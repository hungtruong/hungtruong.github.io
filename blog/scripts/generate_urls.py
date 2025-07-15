import os
import re
import yaml

def generate_post_urls(posts_dir, config_file, output_file):
    urls = []

    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)

    base_url = config.get('url', '').rstrip('/')
    base_path = config.get('baseurl', '').rstrip('/')

    for root, _, files in os.walk(posts_dir):
        for file in files:
            if file.endswith(".md"):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Extract YAML front matter
                front_matter_match = re.match(r"^---\s*$(.*?)^---\s*$", content, re.DOTALL | re.MULTILINE)
                
                post_data = {}
                if front_matter_match:
                    front_matter_str = front_matter_match.group(1)
                    try:
                        post_data = yaml.safe_load(front_matter_str)
                    except yaml.YAMLError as e:
                        print(f"Error parsing YAML in {file}: {e}")
                        continue

                # Prioritize permalink from front matter
                if post_data and 'permalink' in post_data:
                    permalink = post_data['permalink'].strip('/')
                    if base_path:
                        full_url = f"{base_url}{base_path}/{permalink}"
                    else:
                        full_url = f"{base_url}/{permalink}"
                else:
                    # Fallback to YYYY/MM/DD/title-slug from filename
                    match = re.match(r"^(\d{4})-(\d{2})-(\d{2})-(.*)\.md$", file)
                    if match:
                        year, month, day, title_slug = match.groups()
                        if base_path:
                            full_url = f"{base_url}{base_path}/{year}/{month}/{day}/{title_slug}"
                        else:
                            full_url = f"{base_url}/{year}/{month}/{day}/{title_slug}"
                    else:
                        print(f"Warning: Could not determine URL for {file}. Skipping.")
                        continue

                urls.append(full_url)
    
    with open(output_file, "w") as f:
        for url in urls:
            f.write(url + "\n")
    
    print(f"Generated {len(urls)} URLs and saved to {output_file}")

if __name__ == "__main__":
    POSTS_DIRECTORY = "/Users/hungtruong/Development/HungTruong/jekyll-blog/_posts"
    CONFIG_FILE = "/Users/hungtruong/Development/HungTruong/jekyll-blog/_config.yml"
    OUTPUT_FILE = "/Users/hungtruong/Development/HungTruong/jekyll-blog/post_urls.txt"

    generate_post_urls(POSTS_DIRECTORY, CONFIG_FILE, OUTPUT_FILE)