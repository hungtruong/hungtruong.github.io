#!/usr/bin/env ruby
require 'yaml'
require 'set'
require 'date'

# Script to normalize tags in Jekyll posts
# Usage: ruby scripts/normalize_tags.rb

# Common acronyms that should be ALL CAPS
ACRONYMS = %w[AI API APIs DOM DS DDR PSP PS3 SEO TMBG TV UNM OJ iOS XML CSS HTML HTTP HTTPS JS JSON SQL REST UI UX PHP AJAX CRUD MVC ORM CDN DNS SSH FTP SMTP POP IMAP PDF GIF JPEG JPG PNG SVG RSS URL USB DVD CD RPG FPS RTS MMO MMORPG NPC DLC HR IM IE KVM MP3 DVI SXSW SAX MMS D&D GDK]

# Words that should keep their original case
PRESERVE_CASE = %w[iPhone iPad iPod MacBook iMac Mac Pro .NET C# F# eBay WordPress JavaScript AdWords Android Craigslist Django Facebook Final Firefox Flickr Foursquare Google HTML5 IT iTunes JQuery Jekyll MySQL Nintendo Nokia Orbitz Photoshop PostgreSQL PowerPoint Rails Twilio Twitter Ubuntu Windows Yahoo YouTube Zapier Lifehacker NetNewsWire TechCrunch ThinkGeek Web WebOS DSi iAd macOS]

# Special case words that should be lowercase except first letter
SPECIAL_CASES = {
  'site news' => 'Site News',
  't-shirts' => 'T-Shirts',
  't-shirt' => 'T-Shirt',
  'mac os x' => 'Mac OS X',
  'plug-ins' => 'Plug-ins',
  'sci-fi' => 'Sci-Fi',
  'wi-fi' => 'Wi-Fi',
  'sci fi' => 'Sci-Fi',
  'how-to' => 'How-To',
  'how to' => 'How-To',
  'web 2.0' => 'Web 2.0',
  'web2.0' => 'Web 2.0',
  'iphone x' => 'iPhone X'
}

def normalize_tag(tag)
  return '' if tag.nil? || tag.empty?
  
  # Remove quotes and strip whitespace
  clean_tag = tag.to_s.strip.gsub(/["']/, '')
  return '' if clean_tag.empty?
  
  # Check for case preservation first (case insensitive match, but return original)
  PRESERVE_CASE.each do |word|
    if clean_tag.downcase == word.downcase
      return word
    end
  end
  
  # Check special cases first (exact match, case insensitive)
  SPECIAL_CASES.each do |key, value|
    if clean_tag.downcase == key.downcase
      return value
    end
  end
  
  # Check if it's a known acronym (case insensitive check)
  if ACRONYMS.any? { |acronym| clean_tag.downcase == acronym.downcase }
    return ACRONYMS.find { |acronym| clean_tag.downcase == acronym.downcase }
  end
  
  # Handle multi-word phrases (capitalize each word)
  if clean_tag.include?(' ')
    return clean_tag.downcase.split(' ').map(&:capitalize).join(' ')
  end
  
  # Otherwise capitalize first letter
  clean_tag.downcase.capitalize
end

def extract_field_tags(yaml_content, field_name)
  field_tags = []
  
  # Look for field: [tag1, tag2, tag3] or field: ["tag1", "tag2"]
  if yaml_content.match(/^#{field_name}:\s*\[([^\]]+)\]/m)
    tag_string = $1
    field_tags.concat(tag_string.split(',').map { |t| t.strip.gsub(/["']/, '') })
  end
  
  # Look for YAML list format field (with dashes)
  if yaml_content.match(/^#{field_name}:\s*\n((?:\s+-\s+[^\n]+\n?)+)/m)
    list_content = $1
    list_tags = list_content.scan(/^\s+-\s+(.+)$/).flatten
    field_tags.concat(list_tags.map { |t| t.strip.gsub(/["']/, '') })
  end
  
  # Look for single line field
  if yaml_content.match(/^#{field_name}:\s*(.+)$/m) && !yaml_content.match(/^#{field_name}:\s*\[/) && !yaml_content.match(/^#{field_name}:\s*\n/)
    field_tags << $1.strip.gsub(/["']/, '')
  end
  
  return field_tags
end

def extract_and_normalize_tags_from_file(file_path)
  begin
    content = File.read(file_path)
    
    # Extract YAML front matter
    if content.match(/^---\s*\n(.*?)\n---\s*\n/m)
      yaml_content = $1
      
      # Extract tags and categories separately
      original_tags = extract_field_tags(yaml_content, 'tags')
      original_categories = extract_field_tags(yaml_content, 'categories')
      
      # Normalize each field separately
      normalized_tags = original_tags.map { |tag| normalize_tag(tag) }.uniq.reject(&:empty?)
      normalized_categories = original_categories.map { |tag| normalize_tag(tag) }.uniq.reject(&:empty?)
      
      return {
        original_tags: original_tags,
        original_categories: original_categories,
        normalized_tags: normalized_tags,
        normalized_categories: normalized_categories
      }
    end
  rescue => e
    # Suppress warnings for cleaner output
    # puts "Warning: Could not parse #{file_path}: #{e.message}"
  end
  
  return { original_tags: [], original_categories: [], normalized_tags: [], normalized_categories: [] }
end

def update_tags_in_file(file_path, normalized_tags, normalized_categories)
  return if normalized_tags.empty? && normalized_categories.empty?
  
  begin
    content = File.read(file_path)
    
    # Replace tags field in YAML front matter (bracket format)
    if !normalized_tags.empty?
      content.gsub!(/^tags:\s*\[([^\]]+)\]/m) do |match|
        "tags: [#{normalized_tags.join(', ')}]"
      end
      
      # Replace YAML list format tags (with dashes)
      content.gsub!(/^tags:\s*\n((?:\s+-\s+[^\n]+\n)*\s+-\s+[^\n]+)(?=\n(?:\S|\Z))/m) do |match|
        "tags: [#{normalized_tags.join(', ')}]"
      end
      
      # Replace single line tags
      content.gsub!(/^tags:\s*(.+)$/m) do |match|
        next match if $1.strip.start_with?('[') # Skip if it's already an array
        next match if $1.strip.empty? # Skip empty fields
        "tags: [#{normalized_tags.join(', ')}]"
      end
    end
    
    # Replace categories field in YAML front matter (bracket format)
    if !normalized_categories.empty?
      content.gsub!(/^categories:\s*\[([^\]]+)\]/m) do |match|
        "categories: [#{normalized_categories.join(', ')}]"
      end
      
      # Replace YAML list format categories (with dashes)
      content.gsub!(/^categories:\s*\n((?:\s+-\s+[^\n]+\n)*\s+-\s+[^\n]+)(?=\n(?:\S|\Z))/m) do |match|
        "categories: [#{normalized_categories.join(', ')}]"
      end
      
      # Replace single line categories
      content.gsub!(/^categories:\s*(.+)$/m) do |match|
        next match if $1.strip.start_with?('[') # Skip if it's already an array
        next match if $1.strip.empty? # Skip empty fields
        "categories: [#{normalized_categories.join(', ')}]"
      end
    end
    
    File.write(file_path, content)
    return true
  rescue => e
    puts "Warning: Could not update #{file_path}: #{e.message}"
    return false
  end
end

def main
  posts_dir = File.join(File.dirname(__FILE__), '..', '_posts')
  
  # Find all markdown files in _posts directory recursively
  post_files = Dir.glob(File.join(posts_dir, '**', '*.md'))
  
  puts "Normalizing tags in #{post_files.length} post files..."
  puts
  
  updated_count = 0
  all_normalized_tags = Set.new
  all_normalized_categories = Set.new
  
  post_files.each do |post_file|
    result = extract_and_normalize_tags_from_file(post_file)
    
    # Check if tags or categories need updating
    tags_changed = result[:original_tags] != result[:normalized_tags]
    categories_changed = result[:original_categories] != result[:normalized_categories]
    
    if (result[:normalized_tags].any? || result[:normalized_categories].any?) && (tags_changed || categories_changed)
      if update_tags_in_file(post_file, result[:normalized_tags], result[:normalized_categories])
        changes = []
        if tags_changed && result[:normalized_tags].any?
          changes << "tags: #{result[:original_tags].join(', ')} → #{result[:normalized_tags].join(', ')}"
        end
        if categories_changed && result[:normalized_categories].any?
          changes << "categories: #{result[:original_categories].join(', ')} → #{result[:normalized_categories].join(', ')}"
        end
        
        puts "✓ Updated #{File.basename(post_file)}: #{changes.join('; ')}"
        updated_count += 1
      else
        puts "✗ Failed to update #{File.basename(post_file)}"
      end
    elsif result[:normalized_tags].any? || result[:normalized_categories].any?
      normalized_items = []
      normalized_items << "tags: #{result[:normalized_tags].join(', ')}" if result[:normalized_tags].any?
      normalized_items << "categories: #{result[:normalized_categories].join(', ')}" if result[:normalized_categories].any?
      puts "  Already normalized: #{File.basename(post_file)} - #{normalized_items.join('; ')}"
    end
    
    all_normalized_tags.merge(result[:normalized_tags])
    all_normalized_categories.merge(result[:normalized_categories])
  end
  
  puts
  puts "Summary:"
  puts "- Processed #{post_files.length} files"
  puts "- Updated #{updated_count} files"
  puts "- Found #{all_normalized_tags.size} unique normalized tags:"
  puts all_normalized_tags.to_a.sort.map { |tag| "  • #{tag}" }.join("\n")
  puts "- Found #{all_normalized_categories.size} unique normalized categories:"
  puts all_normalized_categories.to_a.sort.map { |tag| "  • #{tag}" }.join("\n")
end

if __FILE__ == $0
  main
end