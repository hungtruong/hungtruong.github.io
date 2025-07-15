#!/usr/bin/env python3
"""
WordPress Comment Recovery Script for Jekyll Blog
Recovers comments from Archive.org for posts published before April 2018
"""

import requests
import time
import re
import yaml
import os
import hashlib
from datetime import datetime, timezone
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
import argparse
import json

class CommentRecovery:
    def __init__(self, blog_url="https://www.hung-truong.com/blog", 
                 output_dir="_data/comments", 
                 delay=1.0, 
                 cutoff_date="2018-04-01"):
        self.blog_url = blog_url.rstrip('/')
        self.output_dir = output_dir
        self.delay = delay  # Delay between requests to be respectful
        self.cutoff_date = cutoff_date
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        
    def get_cdx_snapshots(self, post_url, limit=50):
        """
        Get archived snapshots of a post from Archive.org CDX API
        """
        cdx_url = "http://web.archive.org/cdx/search/cdx"
        params = {
            'url': post_url,
            'matchType': 'exact',
            'output': 'json',
            'limit': limit,
            'filter': 'statuscode:200'  # Only successful captures
        }
        
        try:
            print(f"Querying CDX API for: {post_url}")
            response = self.session.get(cdx_url, params=params)
            response.raise_for_status()
            time.sleep(self.delay)
            
            data = response.json()
            if not data or len(data) < 2:  # No results or only header
                return []
                
            # Skip header row
            snapshots = []
            for row in data[1:]:
                timestamp, original_url, mime_type, status_code = row[1], row[2], row[3], row[4]
                
                # Only include HTML pages from before our cutoff
                if mime_type.startswith('text/html') and timestamp < self.cutoff_date.replace('-', ''):
                    snapshots.append({
                        'timestamp': timestamp,
                        'url': original_url,
                        'archive_url': f"http://web.archive.org/web/{timestamp}id_/{original_url}"
                    })
            
            print(f"Found {len(snapshots)} archived snapshots")
            return sorted(snapshots, key=lambda x: x['timestamp'], reverse=True)
            
        except Exception as e:
            print(f"Error querying CDX API: {e}")
            return []
    
    def extract_wordpress_comments(self, archive_url):
        """
        Extract comments from an archived WordPress page
        """
        try:
            print(f"Fetching archived page: {archive_url}")
            response = self.session.get(archive_url)
            response.raise_for_status()
            time.sleep(self.delay)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for WordPress comment structure
            comment_selectors = [
                'li.comment', 
                'div.comment',
                'article.comment',
                'div[id^="comment-"]',
                'li[id^="comment-"]'
            ]
            
            comment_elements = []
            for selector in comment_selectors:
                elements = soup.select(selector)
                if elements:
                    comment_elements = elements
                    print(f"Found {len(elements)} comments using selector: {selector}")
                    break
            
            if not comment_elements:
                print("No comments found on this page")
                return []

            comment_map = {} # Map element to parsed comment data

            # First pass: Parse all comments and map them
            for comment_el in comment_elements:
                comment_data = self.parse_comment_element(comment_el)
                if comment_data:
                    comment_map[comment_el] = comment_data

            # Second pass: Associate replies with parents
            for comment_el, comment_data in comment_map.items():
                parent_el = comment_el.find_parent(class_=re.compile(r'\bcomment\b'))
                
                if parent_el and parent_el in comment_map:
                    parent_id = comment_map[parent_el]['_id']
                    comment_data['replying_to'] = parent_id

            return list(comment_map.values())
            
        except Exception as e:
            print(f"Error fetching archived page: {e}")
            return []
    
    def parse_comment_element(self, comment_el, parent_id=None):
        """
        Parse individual comment element from WordPress HTML
        """
        comment_data = {}
        
        # Try to find comment ID
        comment_id = None
        if comment_el.get('id'):
            id_match = re.search(r'comment-(\d+)', comment_el.get('id'))
            if id_match:
                comment_id = id_match.group(1)
        
        # Find author name and URL
        author_name = None
        author_url = None
        
        # Look for author link first (which contains both name and URL)
        author_link = comment_el.select_one('.comment-author a, .fn a, cite a')
        if author_link and author_link.get('href'):
            author_name = author_link.get_text().strip()
            href = author_link.get('href')
            # Extract original URL from archive.org format
            if href and href.startswith(('http://', 'https://')) and not href.startswith('mailto:'):
                # Check if it's an archive.org URL and extract the original
                if 'web.archive.org/web/' in href:
                    # Pattern: https://web.archive.org/web/timestamp/original_url
                    parts = href.split('/')
                    if len(parts) >= 6:
                        # Find the timestamp part and get everything after it
                        for i, part in enumerate(parts):
                            if part.startswith(('19', '20')) and len(part) >= 8:  # timestamp
                                original_url = '/'.join(parts[i+1:])
                                if original_url.startswith(('http://', 'https://')):
                                    author_url = original_url
                                break
                else:
                    # Not an archive URL, use as-is
                    author_url = href
        
        # If no linked author name found, look for plain text name
        if not author_name:
            author_selectors = [
                '.comment-author .fn',
                '.comment-meta .fn', 
                '.fn',
                '.comment-author cite',
                '.comment-author',
                '.vcard .fn'
            ]
            
            for selector in author_selectors:
                author_el = comment_el.select_one(selector)
                if author_el:
                    author_name = author_el.get_text().strip()
                    break
        
        if not author_name:
            # Fallback: look for any name-like text
            cite_el = comment_el.select_one('cite')
            if cite_el:
                author_name = cite_el.get_text().strip()
        
        # Find comment date
        date_selectors = [
            '.comment-date',
            '.comment-meta time',
            '.comment-meta .published',
            'time[datetime]',
            '.date',
            '.comment-meta',
            '.commentmetadata',
            'small',
            'cite + *',  # Element after cite (often contains date)
            '.fn + *',   # Element after author name
        ]
        
        comment_date = None
        for selector in date_selectors:
            date_el = comment_el.select_one(selector)
            if date_el:
                # Try datetime attribute first
                if date_el.get('datetime'):
                    comment_date = date_el.get('datetime')
                else:
                    comment_date = date_el.get_text().strip()
                break
        
        # If no date found with selectors, try to find any text that looks like a date
        if not comment_date:
            comment_text = comment_el.get_text()
            # Look for common date patterns in the text
            date_patterns = [
                r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b',
                r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}\b',
                r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, comment_text, re.IGNORECASE)
                if match:
                    comment_date = match.group(0)
                    break
        
        # Find comment content
        content_selectors = [
            '.comment-content',
            '.comment-text',
            '.comment-body p',
            'p'
        ]
        
        comment_content = None
        for selector in content_selectors:
            content_el = comment_el.select_one(selector)
            if content_el:
                # Get text content, preserving some basic formatting
                comment_content = content_el.get_text().strip()
                break
        
        # Only return comment if we have essential data
        if author_name and comment_content:
            # Generate email hash (we don't have actual emails)
            fake_email = f"{author_name.lower().replace(' ', '')}@recovered.comment"
            email_hash = hashlib.md5(fake_email.encode()).hexdigest()
            
            # Parse and standardize date
            try:
                if comment_date:
                    # Try to parse various date formats
                    parsed_date = self.parse_comment_date(comment_date)
                else:
                    # Fallback to epoch time
                    parsed_date = datetime.now(timezone.utc).isoformat()
            except Exception as e:
                parsed_date = datetime.now(timezone.utc).isoformat()
            
            comment_data = {
                '_id': comment_id or hashlib.md5(f"{author_name}{comment_content}".encode()).hexdigest()[:16],
                'name': author_name,
                'email': email_hash,
                'message': comment_content,
                'date': parsed_date,
                'recovered': True  # Flag to indicate this was recovered
            }
            
            # Add parent ID for threaded comments
            if parent_id:
                comment_data['replying_to'] = parent_id
            
            # Only include URL if we actually found one
            if author_url:
                comment_data['url'] = author_url
            
            return comment_data
        
        return None
    
    def parse_comment_date(self, date_str):
        """
        Parse various date formats from WordPress comments
        """
        # Clean up common date string issues
        date_str = date_str.strip()
        
        # Remove ordinal indicators (st, nd, rd, th) from dates
        date_str = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', date_str)
        
        # Remove day names (Monday, Tuesday, etc.)
        date_str = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s*', '', date_str, flags=re.IGNORECASE)
        
        # WordPress and common date formats, ordered by specificity
        formats = [
            '%Y-%m-%dT%H:%M:%S%z',       # ISO format with timezone
            '%Y-%m-%dT%H:%M:%S',         # ISO format without timezone
            '%Y-%m-%d %H:%M:%S',         # Standard format
            '%B %d, %Y at %I:%M %p',     # "January 1, 2015 at 3:30 PM"
            '%B %d, %Y at %I:%M %p',     # "January 1, 2015 at 3:30 pm"
            '%b %d, %Y at %I:%M %p',     # "Jan 1, 2015 at 3:30 PM"
            '%b %d, %Y at %I:%M %p',     # "Jan 1, 2015 at 3:30 pm"
            '%B %d, %Y',                 # "January 1, 2015"
            '%b %d, %Y',                 # "Jan 1, 2015"
            '%d %B %Y',                  # "1 January 2015"
            '%d %b %Y',                  # "1 Jan 2015"
            '%m/%d/%Y',                  # "1/1/2015" (US format)
            '%m/%d/%y',                  # "1/1/15" (US format, 2-digit year)
            '%Y/%m/%d',                  # "2015/1/1" (ISO-like)
            '%Y-%m-%d',                  # "2015-01-01"
            '%d-%m-%Y',                  # "01-01-2015" (European)
            '%d.%m.%Y',                  # "01.01.2015" (European)
            '%d/%m/%Y',                  # "1/1/2015" (European - try after US format)
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                # Handle 2-digit years (assume 20xx for years 00-30, 19xx for 31-99)
                if dt.year < 100:
                    if dt.year <= 30:
                        dt = dt.replace(year=dt.year + 2000)
                    else:
                        dt = dt.replace(year=dt.year + 1900)
                
                # Ensure timezone info
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                continue
        
        # Try regex patterns for more flexible parsing
        # Match patterns like "August 10, 2002" with various separators
        month_year_pattern = r'(?P<month>January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\s,]*(?P<day>\d{1,2})[\s,]*(?P<year>\d{4})'
        match = re.search(month_year_pattern, date_str, re.IGNORECASE)
        if match:
            month_name = match.group('month')
            day = int(match.group('day'))
            year = int(match.group('year'))
            
            # Convert month name to number
            month_map = {
                'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
                'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
                'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
                'nov': 11, 'november': 11, 'dec': 12, 'december': 12
            }
            
            month = month_map.get(month_name.lower())
            if month:
                try:
                    dt = datetime(year, month, day, tzinfo=timezone.utc)
                    return dt.isoformat()
                except ValueError:
                    pass
        
        # If all parsing fails, try to extract at least the year
        year_match = re.search(r'(?P<year>19\d{2}|20\d{2})', date_str)
        if year_match:
            year = int(year_match.group('year'))
            # Use January 1st as fallback
            dt = datetime(year, 1, 1, tzinfo=timezone.utc)
            return dt.isoformat()
        
        # Last resort: return a very old date to indicate parsing failure
        # This is better than current time since it won't be confused with modern dates
        return datetime(1970, 1, 1, tzinfo=timezone.utc).isoformat()
    
    def save_comments_to_yaml(self, post_slug, comments):
        """
        Save comments in Jekyll/Staticman YAML format
        """
        if not comments:
            print("No comments to save")
            return
        
        post_dir = os.path.join(self.output_dir, post_slug)
        os.makedirs(post_dir, exist_ok=True)
        
        for comment in comments:
            # Generate timestamp-based filename like Staticman
            timestamp = int(time.time() * 1000)
            filename = f"comment-{timestamp}.yml"
            filepath = os.path.join(post_dir, filename)
            
            # Ensure we don't overwrite existing files
            counter = 1
            while os.path.exists(filepath):
                filename = f"comment-{timestamp}-{counter}.yml"
                filepath = os.path.join(post_dir, filename)
                counter += 1
            
            with open(filepath, 'w') as f:
                yaml.dump(comment, f, default_flow_style=False, allow_unicode=True)
                
            print(f"Saved comment to: {filepath}")
            time.sleep(0.1)  # Small delay between file writes
    
    def extract_post_slug_from_url(self, post_url):
        """
        Extract Jekyll-compatible post slug from URL
        """
        # Remove blog URL prefix and extract last part
        path = urlparse(post_url).path
        slug = path.rstrip('/').split('/')[-1]
        
        # Clean up slug to match Jekyll conventions
        slug = re.sub(r'[^a-zA-Z0-9\-]', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        
        return slug
    
    def process_post(self, post_url, max_snapshots=10):
        """
        Process a single post: find snapshots and extract comments
        """
        print(f"\n=== Processing post: {post_url} ===")
        
        snapshots = self.get_cdx_snapshots(post_url, limit=max_snapshots)
        if not snapshots:
            print("No archived snapshots found")
            return
        
        post_slug = self.extract_post_slug_from_url(post_url)
        print(f"Post slug: {post_slug}")
        
        all_comments = []
        
        # Try snapshots from newest to oldest, up to a maximum of 2 attempts
        attempts = 0
        for snapshot in snapshots:
            if attempts >= 2:
                print("Reached maximum attempts (2) without finding comments.")
                break

            print(f"\nTrying snapshot from {snapshot['timestamp']}")
            comments = self.extract_wordpress_comments(snapshot['archive_url'])
            
            if comments:
                print(f"Found {len(comments)} comments in this snapshot")
                all_comments.extend(comments)
                # Usually the most recent snapshot with comments is best
                break
            else:
                print("No comments found in this snapshot")
                attempts += 1
        
        if all_comments:
            print(f"\nTotal comments found: {len(all_comments)}")
            self.save_comments_to_yaml(post_slug, all_comments)
        else:
            print("No comments found in any snapshot")


def main():
    parser = argparse.ArgumentParser(description='Recover WordPress comments from Archive.org')
    parser.add_argument('--url', help='Single post URL to process')
    parser.add_argument('--posts-file', help='File containing list of post URLs')
    parser.add_argument('--delay', type=float, default=1.0, help='Delay between requests (seconds)')
    parser.add_argument('--test', action='store_true', help='Test mode with sample posts')
    
    args = parser.parse_args()
    
    recovery = CommentRecovery(delay=args.delay)
    
    if args.test:
        # Test with known posts that likely had comments
        test_posts = [
            "https://www.hung-truong.com/blog/2014/10/10/graphing-my-cycling-progress-on-strava-and-automating-with-zapier/",
            "https://www.hung-truong.com/blog/2010/01/27/why-the-apple-ipad-will-fail/",
            "https://www.hung-truong.com/blog/2011/07/14/banana-republic-and-gap-etc-stores-passwords-in-plain-text/"
        ]
        
        for post_url in test_posts:
            recovery.process_post(post_url)
    
    elif args.url:
        recovery.process_post(args.url)
    
    elif args.posts_file:
        # Read all URLs initially
        with open(args.posts_file, 'r') as f:
            all_urls = [line.strip() for line in f if line.strip() and not line.strip().startswith('#')]
        
        remaining_urls = list(all_urls) # Create a mutable copy
        
        while remaining_urls:
            current_url = remaining_urls[0] # Get the first URL
            print(f"Attempting to process: {current_url}")
            try:
                recovery.process_post(current_url)
                # If successful, remove the URL and rewrite the file
                remaining_urls.pop(0) # Remove the first element
                with open(args.posts_file, 'w') as f:
                    for url in remaining_urls:
                        f.write(url + '\n')
                print(f"Successfully processed and removed: {current_url}")
            except Exception as e:
                print(f"Error processing {current_url}: {e}")
                print("Keeping this URL in the list for retry.")
                # If an error occurs, break the loop to allow manual intervention or retry
                break # Stop processing on error
    
    else:
        print("Please specify --url, --posts-file, or --test")


if __name__ == "__main__":
    main()