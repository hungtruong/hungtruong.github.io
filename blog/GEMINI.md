# Jekyll Blog Post Creation Process

## File Structure
- Posts go in `_posts/` directory in appropriate year folder
- Check existing structure: currently using `2021-2025/` for recent posts
- Follow naming convention: `YYYY-MM-DD-title-slug.md`
- Use today's date for new posts

## Front Matter Template
```yaml
---
title: 'Post Title Here'
layout: post
author: Hung
categories: [Tech, AI, Claude]  # Choose appropriate categories
permalink: /YYYY/MM/DD/title-slug/
description: Brief SEO-friendly description of the post content
---
```

## Common Categories
Based on recent posts:
- Tech
- AI
- Claude
- iOS
- Music
- Blogging
- Coding
- Lifestyle

## Content Structure
- Start with front matter
- Add `<!-- Your blog content goes here -->`
- Include `<!--more-->` tag for excerpt break
- Follow existing post style and tone

## Process
1. Check `_posts/` directory structure to find correct year folder
2. Create file with proper naming convention
3. Add front matter with all required fields
4. Include basic content structure
5. File is ready for user to write actual content

## Example
For a post in 2025, check if there's a `2025/` folder or `2021-2025/` folder and use the appropriate one.

## Image Processing for Blog Posts

### Image Location Structure
- Images are stored in `/wp-content/uploads/YYYY/`
- Use the current year for new images (e.g., `/wp-content/uploads/2025/`)

### Image Processing Steps
1. **Move and rename** image to proper location:
   ```bash
   mv "original-filename.webp" "/path/to/blog/wp-content/uploads/YYYY/descriptive-name.webp"
   ```

2. **Check image dimensions**:
   ```bash
   sips -g pixelWidth -g pixelHeight "image-path"
   ```

3. **Convert and resize** (using ImageMagick for optimal quality/size):
   ```bash
   # For text/graphics with sharp edges (screenshots, tables, diagrams)
   magick "input.png" -resize 800x -define webp:lossless=true "output.webp"
   
   # For photos or images with gradients
   magick "input.png" -resize 800x -quality 95 "output.webp"
   ```
   - WebP lossless: Perfect quality, 60% smaller than PNG
   - WebP lossy (95%): Good for photos, even smaller files
   - Resizes to 800px width (maintains aspect ratio)
   - Best web performance and compatibility

4. **Clean up** original file if needed:
   ```bash
   rm "original-file.webp"
   ```

### Adding Images to Blog Posts

#### Front Matter
Add to YAML front matter for featured image:
```yaml
image: /wp-content/uploads/YYYY/image-name.webp
```

#### Inline Figure with Caption
Add to post content:
```html
<figure>
	<img src="{{ '/wp-content/uploads/YYYY/image-name.webp' | prepend: site.baseurl }}">
	<figcaption>Caption text here</figcaption>
</figure>
```

### Image Guidelines
- **Max width**: 800px for good loading performance
- **Format**: WebP (lossless for text/graphics, lossy for photos)
- **Naming**: Use descriptive, kebab-case names
- **Captions**: Keep concise and descriptive