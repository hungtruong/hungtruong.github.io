import json
import os
import hashlib
import requests
import html
import re
import glob
import yaml
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv

# Load Environment Variables
load_dotenv()

# CONFIGURATION
# Using Cloudflare Workers AI REST API for embedding generation
CF_ACCOUNT_ID = os.getenv('CF_ACCOUNT_ID')
CF_API_TOKEN = os.getenv('CF_API_TOKEN')
MODEL_ID = '@cf/qwen/qwen3-embedding-0.6b'
import tiktoken

# Max batch size for Qwen3-0.6b API is 32 items
DEFAULT_BATCH_SIZE = 32
# Context window is 8192 tokens. We leave some buffer.
MAX_TOKENS_PER_BATCH = 3000

# Initialize tokenizer once
try:
    TOKENIZER = tiktoken.get_encoding("cl100k_base")
except:
    # Fallback if cl100k_base not found (unlikely), p50k_base is older GPT-3
    TOKENIZER = tiktoken.get_encoding("p50k_base")

def count_tokens(text):
    """
    Count actual tokens using tiktoken (cl100k_base).
    This matches modern BPE tokenizers used by Qwen/GPT-4.
    """
    return len(TOKENIZER.encode(text))

CACHE_FILE = 'scripts/.vector-cache.json'
POSTS_DIR = '_posts'

def parse_frontmatter(content):
    """
    Parses Jekyll frontmatter from a markdown string.
    Returns metadata dict and body content.
    """
    # Check for YAML frontmatter
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', content, re.DOTALL)
    if not match:
        return None, content
    
    fm_text = match.group(1)
    body = match.group(2)
    
    metadata = {}
    # Simple YAML parsing (avoids pyyaml dependency if keeping it light)
    for line in fm_text.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            key = key.strip()
            value = value.strip()
            # Remove quotes
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            metadata[key] = value
            
    return metadata, body.strip()

def generate_embeddings_batch(texts):
    """
    Generates embeddings for a batch of texts using Cloudflare Workers AI REST API.
    """
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/run/{MODEL_ID}"
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Instruction is GLOBAL for the batch
    # Input format: { "text": ["string1", "string2"], "instruction": "..." }
    payload = {
        "text": texts,
        "instruction": "Represent this blog post for retrieval."
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        if not result.get("success"):
            raise Exception(f"Cloudflare AI Error: {result.get('errors')}")
            
        # The API returns shape [batch_size, 1024]
        return result["result"]["data"]
        
    except Exception as e:
        print(f"❌ Embedding Generation Error: {e}")
        # Print response text if available for debugging
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"   Response: {response.text}")
        raise e

def load_config():
    """Load _config.yml to get baseurl."""
    try:
        with open('_config.yml', 'r') as f:
            config = yaml.safe_load(f)
            return config
    except Exception as e:
        print(f"⚠️ Could not load _config.yml: {e}")
        return {}

def get_posts_from_files(mode='summary'):
    """
    Walks the _posts directory and returns a list of post objects.
    mode: 'summary' or 'content'
    """
    config = load_config()
    baseurl = config.get('baseurl', '').rstrip('/')

    posts = []
    files = glob.glob(os.path.join(POSTS_DIR, '**', '*.md'), recursive=True)
    
    print(f"📂 Found {len(files)} markdown files in {POSTS_DIR}...")
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_content = f.read()
            
            metadata, body = parse_frontmatter(raw_content)
            
            if not metadata:
                continue
                
            filename = os.path.basename(filepath)
            slug = filename.replace('.md', '')
            date_match = re.match(r'(\d{4}-\d{2}-\d{2})-(.*)', slug)
            
            permalink = metadata.get('permalink')
            if permalink:
                if not permalink.startswith('/'):
                    permalink = '/' + permalink
                url = f"{baseurl}{permalink}"
            
            elif date_match:
                date_part = date_match.group(1).replace('-', '/')
                title_part = date_match.group(2)
                url = f"{baseurl}/{date_part}/{title_part}/"
            else:
                url = f"{baseurl}/{slug}/"
            
            url = re.sub(r'//+', '/', url)
            
            title = metadata.get('title', slug)
            summary = metadata.get('summary', '')
            
            # Metadata summary always keeps short summary for display
            display_summary = summary if summary else (body[:200] + "...")

            # Determine content source based on mode
            if mode == 'content':
                # FULL CONTENT STRATEGY
                # Verified: Max post size is ~5000 tokens, limit is 8192.
                # So we can safely embed the full content if we use Batch Size = 1.
                content_text = f"{title}\n\n{summary}\n\n{body}"
                embed_source = content_text
            else:
                # SUMMARY ONLY STRATEGY (Legacy/Default)
                if not summary:
                    clean_body = re.sub(r'<[^>]+>', '', body)
                    summary = clean_body[:500] + "..."
                embed_source = summary

            posts.append({
                'id': slug, 
                'title': title,
                'url': url,
                'summary': display_summary,
                'content_source': embed_source 
            })
            
        except Exception as e:
            print(f"⚠️ Failed to parse {filepath}: {e}")
            
    return posts

# ... (process_batch remains mostly same, need to pass index_name to upsert)

def upsert_to_cloudflare(vectors, index_name):
    """
    Upserts vectors to Cloudflare Vectorize.
    """
    ndjson = '\n'.join([json.dumps(v) for v in vectors])
    url = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/vectorize/v2/indexes/{index_name}/upsert"
    
    headers = {
        'Authorization': f'Bearer {CF_API_TOKEN}',
        'Content-Type': 'application/x-ndjson'
    }
    
    try:
        response = requests.post(url, headers=headers, data=ndjson)
        res = response.json()
        if not res.get('success'):
            raise Exception(json.dumps(res.get('errors')))
        print(f"✅ Uploaded {len(vectors)} vectors to Cloudflare index '{index_name}'.")
    except Exception as e:
        print(f"❌ Cloudflare Upsert Error: {e}")
        exit(1)

def process_batch(batch, batch_idx, index_name):
    """
    Process a single batch of posts.
    """
    batch_text = [item['text'] for item in batch]
    print(f"🧠 Processing Batch {batch_idx} ({len(batch)} items)...")
    
    try:
        embeddings = generate_embeddings_batch(batch_text)
        
        vectors_batch = []
        local_cache = {}
        
        for j, item in enumerate(batch):
            vectors_batch.append({
                "id": item['id'],
                "values": embeddings[j],
                "metadata": {
                    "title": item['title'],
                    "url": item['url'],
                    "summary": item['summary'] # Use display summary
                }
            })
            local_cache[item['id']] = item['hash']
        
        upsert_to_cloudflare(vectors_batch, index_name)
        return True, local_cache
            
    except Exception as e:
        print(f"❌ Batch {batch_idx} failed: {e}")
        return False, {}

def main():
    parser = argparse.ArgumentParser(description='Index blog posts to Cloudflare Vectorize.')
    parser.add_argument('--index', default=INDEX_NAME, help='Name of the index (default: blog-index)')
    parser.add_argument('--mode', choices=['summary', 'content'], default='content', help='Indexing mode (default: content)')
    args = parser.parse_args()

    if not CF_ACCOUNT_ID or not CF_API_TOKEN:
        print("❌ Error: CF_ACCOUNT_ID and CF_API_TOKEN must be set in .env")
        return

    print(f"🔧 Configured for Index: '{args.index}' | Mode: '{args.mode}'")

    # 1. Load Cache (Namespace by index name)
    cache_file = f'scripts/.vector-cache-{args.index}.json'
    cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except:
            cache = {}

    new_cache = cache.copy()

    # 2. Get Posts
    all_posts = get_posts_from_files(mode=args.mode)
    
    # 3. Identify changes
    posts_to_process = []
    
    print(f"🔍 Scanning {len(all_posts)} posts for changes...")
    
    for post in all_posts:
        post_id = hashlib.md5(post['id'].encode()).hexdigest()
        
        # Hash includes content source, so changing mode will naturally invalidate cache
        content_hash = hashlib.md5((post['title'] + post['url'] + post['content_source'] + MODEL_ID).encode('utf-8')).hexdigest()
        
        if cache.get(post_id) != content_hash:
            posts_to_process.append({
                'id': post_id,
                'title': post['title'],
                'url': post['url'],
                'text': post['content_source'], # This is the full content in content mode
                'summary': post['summary'],     # Display summary
                'hash': content_hash
            })

    if not posts_to_process:
        print("✨ No new/updated posts to index.")
        return

    print(f"🚀 Found {len(posts_to_process)} posts to index.")

    # 4. Process in Batches (Parallel)
    # 4. Process in Batches (Parallel & Greedy)
    # If mode is content, use greedy batching based on tokens.
    # If mode is summary, use fixed batch size (safe because summaries are short).
    
    batches = []
    
    if args.mode == 'content':
        current_batch = []
        current_tokens = 0
        
        for post in posts_to_process:
            # Estimate tokens including instruction overhead (approx)
            # Instruction: "Represent this blog post for retrieval." (~10 tokens)
            tokens = count_tokens(post['text']) + 15
            
            # If adding this post exceeds limit, or batch size hits 32 (API limit)
            if (current_tokens + tokens > MAX_TOKENS_PER_BATCH) or (len(current_batch) >= 32):
                if current_batch:
                    batches.append(current_batch)
                current_batch = [post]
                current_tokens = tokens
            else:
                current_batch.append(post)
                current_tokens += tokens
                
        # Append final batch
        if current_batch:
            batches.append(current_batch)
            
        print(f"⚡ Greedy batching created {len(batches)} batches (Max tokens: {MAX_TOKENS_PER_BATCH}).")
            
    else:
        # Standard logic for summary mode
        total = len(posts_to_process)
        for i in range(0, total, DEFAULT_BATCH_SIZE):
            batches.append(posts_to_process[i:i + DEFAULT_BATCH_SIZE])
            
        print(f"⚡ Standard batching created {len(batches)} batches (Size: {DEFAULT_BATCH_SIZE}).")

    print(f"⚡ Starting parallel processing with 5 workers...")
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Pass args.index to process_batch
        future_to_batch = {
            executor.submit(process_batch, batch, i + 1, args.index): (i + 1) 
            for i, batch in enumerate(batches)
        }
        
        for future in as_completed(future_to_batch):
            batch_id = future_to_batch[future]
            try:
                success, batch_cache = future.result()
                if success:
                    new_cache.update(batch_cache)
                else:
                    print(f"⚠️ Warning: Batch {batch_id} failed completely.")
            except Exception as exc:
                print(f"❌ Exception in batch {batch_id}: {exc}")

    # 5. Save cache
    print("💾 Saving cache...")
    with open(cache_file, 'w') as f:
        json.dump(new_cache, f, indent=2)

    print("\n🎉 Indexing process finished.")

if __name__ == "__main__":
    main()
