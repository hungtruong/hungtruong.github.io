
import os
import yaml
import requests
import json
import argparse
import time
import subprocess

# Configuration
LLM_PROXY_URL = "https://llm-proxy.hungt.workers.dev/chat/completions"
FIXED_CATEGORIES = {
    "Tech": ["Coding", "AI", "Hardware", "Apps", "Startups", "Internet"],
    "Life": ["Personal", "Travel", "Health", "Home", "Dreams", "Japanese"],
    "TV": ["Shows"],
    "Movies": ["Reviews", "Cinema"],
    "Music": ["Concerts", "Songs", "Artists", "Found Audio", "Jazz"],
    "Books": ["Reviews", "Reading", "Literature"],
    "Gaming": ["Video Games", "Wii", "Nintendo"],
    "Food": ["Recipes", "Restaurants", "Snacks"],
    "Meta": ["Blogging", "Site News", "Projects"]
}

def parse_frontmatter(content):
    """Parses frontmatter from a markdown string."""
    try:
        if content.startswith('---'):
            end = content.find('---', 3)
            if end != -1:
                fm_str = content[3:end]
                fm = yaml.safe_load(fm_str)
                body = content[end+3:].strip()
                return fm, body, content[3:end] # Return original FM string for diffing if needed
    except Exception as e:
        print(f"Error parsing frontmatter: {e}")
    return {}, content, ""

def dump_frontmatter(fm, body):
    """Reconstructs the post with updated frontmatter."""
    # Custom dump to keep it clean-ish
    fm_str = yaml.dump(fm, default_flow_style=None, sort_keys=False, allow_unicode=True)
    return f"---\n{fm_str}---\n\n{body}\n"

def call_llm(post_content, current_fm):
    """Calls the LLM to analyze the post."""
    
    # Truncate content if too long to save context window/time
    # content_snippet = post_content[:3000] # User requested full content
    
    prompt = f"""
You are an expert Search Optimization Specialist for a personal blog. Your goal is to generate high-quality metadata that improves retrieval in a vector search database.

**Fixed Category List:**
{json.dumps(FIXED_CATEGORIES, indent=2)}

**Task:**
1. **Analyze** the Blog Post Content below.
2. **Assign Category:** Select the Single Best Category from the provided list.
   - **STRICTLY** use one of the top-level keys (e.g. "Tech", "Life") as the 'category'.
   - **DO NOT** output "Tech/Apps" or "Tech > Apps". Use "Tech" as the category and add "Apps" to the tags.
   - If the post discusses multiple topics, choose the DOMINANT one.
   - Only suggest a new category if the content is completely unrelated to existing options.
3. **Generate Tags:** Provide 3-5 relevant, lowercase tags.
   - Prioritize specific technologies (e.g., "Python", "Docker", "Synology", "iOS") over generic terms. Tags should be properly capitalized rather than downcased..
   - Reuse existing tags if relevant: {current_fm.get('tags', [])}
4. **Write Summary (Crucial):** Write a dense, keyword-rich summary (max 3 sentences) optimized for retrieval.
   - **Constraint 1 (Density):** Include specific error codes, software versions, hardware models, or unique terminology (e.g., "LoRA", "MD0", "Error 503") mentioned in the text.
   - **Constraint 2 (Coherence):** Use complete, grammatical sentences to preserve cause-and-effect relationships. Avoid disjointed "word salad."
   - **Constraint 3 (No Meta-Talk):** DO NOT use phrases like "This post discusses", "The author explains", or "A review of". Start directly with the subject (e.g., "Sora 2 onboarding requires..." or "Fix for Synology RAID degradation...").
   - **Constraint 4 (Front-Loading): The FIRST sentence must be a standalone "hook" (under 25 words) that summarizes the main value. Put deeper technical details (error codes, specific limits) in sentences 2 and 3.
   
**Blog Post Content:**
{post_content}

**Output format (JSON only):**
{{
  "category": "String",
  "tags": ["String", "String"],
  "summary": "String"
}}
"""

    payload = {
        "model": "any-free", # Using 'any-free' as discussed
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }
    
    headers = {"Content-Type": "application/json"}
    
    max_retries = 3
    base_delay = 5
    
    for attempt in range(max_retries):
        try:
            print(f"  [Attempt {attempt+1}] Sending request to LLM...", flush=True)
            # Add timeout to prevent hanging forever (10s connect, 60s read)
            response = requests.post(LLM_PROXY_URL, json=payload, headers=headers, timeout=(10, 60))
            
            print(f"  [Attempt {attempt+1}] Response received. Status: {response.status_code}", flush=True)
            
            if response.status_code == 200:
                res_json = response.json()
                
                if 'error' in res_json:
                     print(f"LLM Provider Error: {res_json['error']}. Retrying...", flush=True)
                     time.sleep(base_delay)
                     base_delay *= 2
                     continue
                     
                try:
                    content = res_json['choices'][0]['message']['content']
                except KeyError:
                    print(f"Error: Unexpected JSON format. Response keys: {res_json.keys()}", flush=True)
                    print(f"Full Response: {res_json}", flush=True)
                    return None
                
                # Clean up potential markdown code blocks if the model adds them
                content = content.strip()
                if content.startswith('```json'):
                    content = content[7:]
                elif content.startswith('```'):
                    content = content[3:]
                
                if content.endswith('```'):
                    content = content[:-3]
                
                content = content.strip()
                
                try:
                    result = json.loads(content)
                    result['llm_model'] = res_json.get('model', 'any-free')
                    return result
                except json.JSONDecodeError as e:
                    print(f"  JSON Decode Error: {e}", flush=True)
                    print(f"  Raw Content: {content}", flush=True)
                    # Don't return None immediately, let it retry? 
                    # Yes, raise so the outer loop catches it and retries
                    raise e
            elif response.status_code in [500, 502, 503, 504, 429]:
                 print(f"LLM API Error: {response.status_code}. Retrying in {base_delay}s...", flush=True)
                 time.sleep(base_delay)
                 base_delay *= 2
            else:
                print(f"LLM API Error: {response.status_code} - {response.text}", flush=True)
                return None
        except requests.exceptions.Timeout:
            print(f"  [Attempt {attempt+1}] Request timed out. Retrying...", flush=True)
            time.sleep(base_delay)
            base_delay *= 2
        except Exception as e:
            print(f"LLM Request Failed: {e}. Retrying...", flush=True)
            time.sleep(base_delay)
            base_delay *= 2
            
    print("Max retries exceeded.", flush=True)
    return None

def is_file_dirty(filepath):
    """Checks if a file is modified/dirty in git."""
    try:
        # git status --porcelain returns output if file is changed
        result = subprocess.run(
            ["git", "status", "--porcelain", filepath],
            capture_output=True,
            text=True,
            check=True
        )
        return bool(result.stdout.strip())
    except subprocess.CalledProcessError:
        # If git fails, assume dirty to be safe? Or log warning?
        # Assuming not dirty if git fails might overwrite work.
        print(f"Warning: git status check failed for {filepath}")
        return False

def process_file(filepath, dry_run=False, incremental=False):
    if incremental and is_file_dirty(filepath):
        print(f"Skipping {filepath} (Dirty in git)...", flush=True)
        return

    print(f"Processing {filepath}...", flush=True)
    try:
        with open(filepath, 'r') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"File not found: {filepath}", flush=True)
        return

    fm, body, _ = parse_frontmatter(content)
    # ... rest of function ...
    if not fm:
        print("Skill issue: No frontmatter found.", flush=True)
        return

    result = call_llm(body, fm)
    if not result:
        print("Skipping: LLM failed to return valid JSON.", flush=True)
        return

    # Update Frontmatter
    original_category = fm.get('category') or fm.get('categories')
    original_tags = fm.get('tags')
    
    # Remove old plural 'categories' to avoid confusion/duplicates
    if 'categories' in fm:
        del fm['categories']
        
    # Validate/Normalize Category
    llm_cat = result['category']
    
    # Pre-process for slash/arrow creativity
    if '/' in llm_cat:
        parts = llm_cat.split('/')
        if parts[0].strip() in FIXED_CATEGORIES:
            llm_cat = parts[0].strip()
            if 'tags' not in result: result['tags'] = []
            result['tags'].append(parts[1].strip())
    elif '>' in llm_cat:
        parts = llm_cat.split('>')
        if parts[0].strip() in FIXED_CATEGORIES:
            llm_cat = parts[0].strip()
            if 'tags' not in result: result['tags'] = []
            result['tags'].append(parts[1].strip())
            
    final_cat = llm_cat
    
    # Check if it's a known key
    if llm_cat not in FIXED_CATEGORIES:
        # Check if it's a sub-category value
        for key, values in FIXED_CATEGORIES.items():
            if llm_cat in values:
                final_cat = key
                # Add the specific term to tags if not there
                if 'tags' not in result: result['tags'] = []
                if llm_cat not in result['tags']:
                    result['tags'].append(llm_cat)
                break
    
    fm['category'] = final_cat
    # Merge existing tags if desired, or just overwrite? 
    # Plan says: "Generate 3-5 additional specific tags... Preferring existing".
    # Let's trust the LLM's output for tags but maybe ensure we don't lose data if we want strict accumulation? 
    # User said: "Each post can either keep the existing tags and categories or have them altered."
    # So overwriting based on LLM's judgement is fine.
    fm['tags'] = result['tags']
    
    # Add summary
    fm['summary'] = result['summary']
    
    # log the model used
    fm['llm_model'] = result.get('llm_model', 'any-free')

    # Normalize tags to list if they aren't
    if isinstance(fm.get('tags'), str):
        fm['tags'] = [fm['tags']]
        
    print(f"  Old/New Category: {original_category} -> {fm['category']}", flush=True)
    print(f"  Old/New Tags: {original_tags} -> {fm['tags']}", flush=True)
    print(f"  Summary: {fm['summary']}", flush=True)

    if not dry_run:
        new_content = dump_frontmatter(fm, body)
        with open(filepath, 'w') as f:
            f.write(new_content)
        print("  Updated file.", flush=True)
    else:
        print("  Dry Run: No changes written.", flush=True)

def main():
    parser = argparse.ArgumentParser(description="Update blog post metadata using LLM.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write changes to files.")
    parser.add_argument("--file", type=str, nargs='+', help="Process specific file(s).")
    parser.add_argument("--limit", type=int, help="Limit the number of files to process.")
    parser.add_argument("--incremental", action="store_true", help="Skip files that are already modified in git.")
    
    args = parser.parse_args()

    if args.file:
        for f in args.file:
            process_file(f, args.dry_run, args.incremental)
            time.sleep(2) # Enforce a pause between files
    else:
        all_files = []
        for root, dirs, files in os.walk("_posts"):
            for file in files:
                if file.endswith(".md"):
                    all_files.append(os.path.join(root, file))
        
        # Sort ALL files globally in reverse order (Newest first)
        all_files.sort(reverse=True)
        
        count = 0
        for filepath in all_files:
            if args.limit and count >= args.limit:
                break
                
            process_file(filepath, args.dry_run, args.incremental)
            
            count += 1
            time.sleep(1) 

if __name__ == "__main__":
    main()
