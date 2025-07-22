#!/usr/bin/env ruby
require 'yaml'
require 'set'
require 'date'

# Script to fetch all currently used tags from Jekyll posts
# Usage: ruby scripts/fetch_tags.rb

def extract_tags_from_file(file_path)
  begin
    content = File.read(file_path)
    
    # Extract YAML front matter
    if content.match(/^---\s*\n(.*?)\n---\s*\n/m)
      yaml_content = $1
      
      # Simple regex extraction for tags and categories (keep original format)
      tags = []
      
      # Look for tags: [tag1, tag2, tag3] or tags: ["tag1", "tag2"]
      if yaml_content.match(/^tags:\s*\[([^\]]+)\]/m)
        tag_string = $1
        tags.concat(tag_string.split(',').map { |t| t.strip.gsub(/["']/, '') })
      end
      
      # Look for categories: [cat1, cat2, cat3]
      if yaml_content.match(/^categories:\s*\[([^\]]+)\]/m)
        cat_string = $1
        tags.concat(cat_string.split(',').map { |t| t.strip.gsub(/["']/, '') })
      end
      
      # Look for YAML list format tags/categories (with dashes)
      ['tags', 'categories'].each do |field|
        if yaml_content.match(/^#{field}:\s*\n((?:\s+-\s+[^\n]+\n?)+)/m)
          list_content = $1
          list_tags = list_content.scan(/^\s+-\s+(.+)$/).flatten
          tags.concat(list_tags.map { |t| t.strip.gsub(/["']/, '') })
        end
      end
      
      # Look for single line tags/categories
      if yaml_content.match(/^tags:\s*(.+)$/m) && !yaml_content.match(/^tags:\s*\[/) && !yaml_content.match(/^tags:\s*\n/)
        tags << $1.strip.gsub(/["']/, '')
      end
      
      if yaml_content.match(/^categories:\s*(.+)$/m) && !yaml_content.match(/^categories:\s*\[/) && !yaml_content.match(/^categories:\s*\n/)
        tags << $1.strip.gsub(/["']/, '')
      end
      
      return tags.map(&:strip).reject(&:empty?)
    end
  rescue => e
    # Suppress warnings for cleaner output
    # puts "Warning: Could not parse #{file_path}: #{e.message}"
  end
  
  return []
end

def main
  posts_dir = File.join(File.dirname(__FILE__), '..', '_posts')
  all_tags = Set.new
  
  # Find all markdown files in _posts directory recursively
  post_files = Dir.glob(File.join(posts_dir, '**', '*.md'))
  
  post_files.each do |post_file|
    tags = extract_tags_from_file(post_file)
    # Keep original case and merge tags
    all_tags.merge(tags.map(&:strip))
  end
  
  # Sort tags alphabetically
  sorted_tags = all_tags.to_a.sort
  
  puts "Found #{sorted_tags.length} unique tags across all posts:"
  puts
  sorted_tags.each_with_index do |tag, index|
    puts "#{index + 1}. #{tag}"
  end
  
  puts
  puts "Tag list (comma-separated):"
  puts sorted_tags.join(', ')
end

if __FILE__ == $0
  main
end