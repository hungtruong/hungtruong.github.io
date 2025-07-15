#!/usr/bin/env python3
"""
Fix comments with bad 2025 timestamps by deleting them and refetching from archive.org
"""

import os
import yaml
import shutil
import sys
from datetime import datetime
from comment_recovery import CommentRecovery

def get_post_url_from_slug(slug):
    """Convert post slug back to URL by finding the actual post file"""
    # Search for the post in the _posts directory structure
    post_dirs = ['_posts', '_posts/2015-2020']
    
    # Add year directories dynamically
    for year in range(2002, 2025):
        year_dir = f'_posts/{year}'
        if os.path.exists(year_dir):
            post_dirs.append(year_dir)
    
    for post_dir in post_dirs:
        if not os.path.exists(post_dir):
            continue
            
        for filename in os.listdir(post_dir):
            if filename.endswith('.md') and slug in filename:
                # Extract date from filename: YYYY-MM-DD-slug.md
                date_part = filename[:10]  # YYYY-MM-DD
                if len(date_part) == 10 and date_part.count('-') == 2:
                    try:
                        year, month, day = date_part.split('-')
                        return f"http://www.hung-truong.com/blog/{year}/{month}/{day}/{slug}/"
                    except:
                        continue
    
    # Fallback to old method if not found
    return f"http://www.hung-truong.com/blog/{slug}/"

def find_bad_comments(comments_dir="_data/comments"):
    """Find all comments with 2025 timestamps"""
    bad_posts = {}
    
    if not os.path.exists(comments_dir):
        print(f"Comments directory {comments_dir} does not exist")
        return bad_posts
    
    for post_dir in os.listdir(comments_dir):
        post_path = os.path.join(comments_dir, post_dir)
        if not os.path.isdir(post_path):
            continue
            
        bad_files = []
        for comment_file in os.listdir(post_path):
            if not comment_file.endswith('.yml'):
                continue
                
            comment_path = os.path.join(post_path, comment_file)
            try:
                with open(comment_path, 'r') as f:
                    comment_data = yaml.safe_load(f)
                
                if comment_data and 'date' in comment_data:
                    date_str = comment_data['date']
                    if '2025' in date_str:
                        bad_files.append(comment_path)
                        
            except Exception as e:
                print(f"ERROR reading {comment_file}: {e}")
        
        if bad_files:
            bad_posts[post_dir] = bad_files
    
    return bad_posts

def backup_post_comments(post_dir, backup_dir="_data/comments_backup"):
    """Backup all comments for a post before deleting"""
    os.makedirs(backup_dir, exist_ok=True)
    
    source_path = os.path.join("_data/comments", post_dir)
    backup_path = os.path.join(backup_dir, post_dir)
    
    if os.path.exists(source_path):
        if os.path.exists(backup_path):
            shutil.rmtree(backup_path)
        shutil.copytree(source_path, backup_path)
        print(f"  Backed up {post_dir} to {backup_path}")
        return True
    return False

def delete_bad_comments(bad_files):
    """Delete the bad comment files"""
    for file_path in bad_files:
        try:
            os.remove(file_path)
            print(f"  Deleted: {file_path}")
        except Exception as e:
            print(f"  ERROR deleting {file_path}: {e}")

def refetch_comments(post_slug, recovery_instance):
    """Refetch comments for a post"""
    post_url = get_post_url_from_slug(post_slug)
    print(f"  Refetching comments for: {post_url}")
    
    try:
        recovery_instance.process_post(post_url)
        return True
    except Exception as e:
        print(f"  ERROR refetching comments: {e}")
        return False

def main():
    print("=== Finding comments with bad 2025 timestamps ===")
    bad_posts = find_bad_comments()
    
    if not bad_posts:
        print("No bad comments found!")
        return
    
    total_bad_comments = sum(len(files) for files in bad_posts.values())
    print(f"Found {len(bad_posts)} posts with {total_bad_comments} bad comments")
    
    # Show posts to fix
    print(f"\\nPosts to fix:")
    for post_dir, bad_files in bad_posts.items():
        print(f"  - {post_dir} ({len(bad_files)} bad comments)")
    
    # Auto-proceed (remove interactive prompt)
    print(f"\\nProceeding with fixing {len(bad_posts)} posts...")
    
    # For testing, limit to first N posts
    if len(sys.argv) > 1 and sys.argv[1].startswith("--test"):
        if "=" in sys.argv[1]:
            num_posts = int(sys.argv[1].split("=")[1])
        else:
            num_posts = 3
        print(f"TEST MODE: Only processing first {num_posts} posts")
        limited_posts = dict(list(bad_posts.items())[:num_posts])
        bad_posts = limited_posts
    
    # Initialize recovery instance
    recovery = CommentRecovery(delay=2.0)  # Be extra respectful with delays
    
    # Process each post
    successful_fixes = 0
    failed_fixes = []
    
    for post_dir, bad_files in bad_posts.items():
        print(f"\\n=== Processing {post_dir} ({len(bad_files)} bad comments) ===")
        
        # Backup first
        if not backup_post_comments(post_dir):
            print(f"  FAILED to backup {post_dir}, skipping...")
            failed_fixes.append(post_dir)
            continue
        
        # Delete bad comments
        delete_bad_comments(bad_files)
        
        # Refetch comments
        if refetch_comments(post_dir, recovery):
            successful_fixes += 1
            print(f"  SUCCESS: Fixed {post_dir}")
        else:
            failed_fixes.append(post_dir)
            print(f"  FAILED: Could not refetch comments for {post_dir}")
    
    # Summary
    print(f"\\n=== SUMMARY ===")
    print(f"Successfully fixed: {successful_fixes}/{len(bad_posts)} posts")
    print(f"Failed to fix: {len(failed_fixes)} posts")
    
    if failed_fixes:
        print(f"\\nFailed posts:")
        for post_dir in failed_fixes:
            print(f"  - {post_dir}")
        
        # Create a retry file for failed posts
        with open("failed_posts.txt", "w") as f:
            for post_dir in failed_fixes:
                f.write(f"{get_post_url_from_slug(post_dir)}\\n")
        print(f"\\nFailed post URLs saved to failed_posts.txt for manual retry")
    
    print(f"\\nBackups saved in _data/comments_backup/")

if __name__ == "__main__":
    main()