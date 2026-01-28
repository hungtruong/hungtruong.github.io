import os
import re

POSTS_DIR = '_posts'
AUDIO_DIR = 'assets/audio'

def normalize_text(text):
    """Normalize text for comparison: remove non-alphanumeric, lower case."""
    return re.sub(r'[^a-z0-9]', '', text.lower())

def get_post_data(post_path):
    """Extract audio_slug and content manually."""
    try:
        with open(post_path, 'r', encoding='utf-8') as f:
            full_text = f.read()
    except Exception:
        return None, None

    # Split by frontmatter delimiters
    parts = re.split(r'^---\s*$', full_text, flags=re.MULTILINE)
    if len(parts) < 3:
        return None, None
    
    front_matter = parts[1]
    content = "".join(parts[2:])
    
    # Extract audio_slug
    slug_match = re.search(r'^audio_slug:\s*(.+)$', front_matter, re.MULTILINE)
    if not slug_match:
        return None, None
        
    return slug_match.group(1).strip(), content

def get_list_items(content):
    """Extract list items from markdown content."""
    list_items = []
    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()
        # Bullet points: * or - (must be followed by space)
        # Numbered lists: 1. 2. etc
        match = re.match(r'^(\*|-|\d+\.)\s+(.+)', stripped)
        if match:
            list_items.append(match.group(2))
    return list_items

def check_vtt_coverage(post_path, audio_slug):
    vtt_path = os.path.join(AUDIO_DIR, f"{audio_slug}.vtt")
    if not os.path.exists(vtt_path):
        return None

    slug, content = get_post_data(post_path)
    if not content:
        return None

    items = get_list_items(content)
    if not items:
        return None 

    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            vtt_content = f.read()
    except Exception:
        return None

    # Extract text from VTT
    vtt_text_blob = ""
    for line in vtt_content.split('\n'):
        if '-->' in line:
            continue
        if line.strip() == 'WEBVTT':
            continue
        if not line.strip():
            continue
        if re.match(r'^\d+$', line.strip()):
            continue
        vtt_text_blob += line + " "
    
    normalized_vtt = normalize_text(vtt_text_blob)
    
    missing_items = []
    for item in items:
        # Markdown link cleaning: [text](url) -> text
        clean_item = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', item)
        # Bold/Italic cleaning: **text** -> text, *text* -> text
        clean_item = re.sub(r'[*_]{1,2}([^*_]+)[*_]{1,2}', r'\1', clean_item)
        
        normalized_item = normalize_text(clean_item)
        
        if len(normalized_item) < 10: 
            continue # Skip short items

        if normalized_item not in normalized_vtt:
             missing_items.append(clean_item)

    if missing_items:
        return missing_items
    return None

def main():
    print("Auditing posts for missing list items in VTT...")
    for root, dirs, files in os.walk(POSTS_DIR):
        for file in files:
            if file.endswith('.md'):
                post_path = os.path.join(root, file)
                slug, _ = get_post_data(post_path)
                if slug:
                    missing = check_vtt_coverage(post_path, slug)
                    if missing:
                        print(f"\nPost: {file} (slug: {slug})")
                        print(f"Found {len(missing)} potentially missing items:")
                        for item in missing[:5]: 
                            print(f" - {item[:100]}...")
                        if len(missing) > 5:
                            print(f" - ... and {len(missing)-5} more")

if __name__ == "__main__":
    main()
