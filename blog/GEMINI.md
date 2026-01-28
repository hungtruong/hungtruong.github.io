# Jekyll Blog Assistant Guidance (Claude & Gemini)
The site baseurl is /blog so always navigate to /blog/

## Quick Start (TL;DR)
- Create a new post in `_posts/` using today’s date and kebab-case slug: `YYYY-MM-DD-title-slug.md` in the correct year folder (currently `2021-2025/`).
- Use the front matter template below; set `image` to a site-root path for the featured media: `/wp-content/uploads/YYYY/filename.webp`.
- Add content scaffold and an excerpt break `<!--more-->`.
- For internal links, keep your original wording and link inline using Liquid: `{{ '/path/' | prepend: site.baseurl }}`.
- Media workflow:
  - Images → convert to 1000px WebP, store in `/wp-content/uploads/YYYY/`.
  - Videos → copy from `zz_incoming_media/`, rename descriptively, generate a poster WebP, embed with `playsinline` + `preload="metadata"`. For tall clips, cap width ~360px and center.
- Keep source media in `zz_incoming_media/` until approved.

## Paths & Naming
- Posts: `_posts/<year-or-range>/YYYY-MM-DD-title-slug.md` (use `2021-2025/` for recent years).
- Media (published): `/wp-content/uploads/YYYY/`.
- Media (staging): `zz_incoming_media/` (do not delete originals until confirmed).
- Filenames: descriptive, kebab-case.

## Front Matter Template
```yaml
---
title: 'Post Title Here'
layout: post
author: Hung
categories: [Tech, AI, Claude, iOS, Music, Blogging, Coding, Lifestyle]  # Choose appropriate categories
permalink: /YYYY/MM/DD/title-slug/
description: Brief SEO-friendly description of the post content
# Featured image or video poster (site-root path)
image: /wp-content/uploads/YYYY/featured-or-poster.webp
---
```

## Featured Media Behavior
- Use an absolute site-root path for `image` (e.g., `/wp-content/uploads/2025/name.webp`).
- Prev/next thumbnails at the bottom of posts read `page.image` directly, so absolute paths show correctly.
- Social cards (Open Graph/Twitter) are generated in `_includes/head.html`, which supports absolute `page.image` paths.

## Content Structure & Linking
- Start with front matter → intro paragraph(s) → `<!--more-->` → body sections.
- When Hung requests a link:
  - Keep the existing wording; add the link inline without rewriting surrounding text. 
  - Prefer natural placement that flows with the draft; usually toward the end unless context clearly points elsewhere.
  - Use Liquid for internal links so base URL is respected: `{{ '/YYYY/MM/DD/slug/' | prepend: site.baseurl }}`.

## Image Workflow
1. Locate source in `zz_incoming_media/` (or as specified).
2. Move and rename to proper location if already WebP, or prepare for conversion.
   ```bash
   mv "original-filename.webp" "/path/to/blog/wp-content/uploads/YYYY/descriptive-name.webp"
   ```
3. Convert to WebP at 1000px wide (or smaller if the original is smaller) for performance.
   - Text/graphics: lossless WebP.
   - Photos/gradients: quality ~95.
4. Place in `/wp-content/uploads/YYYY/` with descriptive name.
5. Keep original source in place until approved.

### Image Commands (macOS)
```bash
# Dimensions
sips -g pixelWidth -g pixelHeight "image.png"

# Convert (ImageMagick)
magick input.png -resize 1000x -define webp:lossless=true output.webp
# Or for photos
magick input.jpg -resize 1000x -quality 95 output.webp
```

### Image Embed Snippet
```html
<figure>
  <img src="{{ '/wp-content/uploads/YYYY/image-name.webp' | prepend: site.baseurl }}" alt="Descriptive alt text">
  <figcaption>Concise, helpful caption.</figcaption>
</figure>
```

## Video Workflow
1. Preview the clip in `zz_incoming_media/` and choose a descriptive, kebab-case name reflecting what’s on screen.
2. Copy to `/wp-content/uploads/YYYY/` (leave the original in staging until approved).
3. Generate a poster frame ~1s into the video using `ffmpeg`, then convert to a 1000px-wide lossless WebP; name it with the same base plus `-poster`. After converting, delete the intermediate PNG — keep only the WebP poster.
4. Embed with `controls playsinline preload="metadata" poster="..."`.
5. If the clip is portrait/tall, cap width to ~360px and center it so it doesn’t overwhelm the layout.

### Video Commands
```bash
# Copy from staging (keep original)
cp -p "zz_incoming_media/original-name.MP4" "wp-content/uploads/2025/descriptive-name.mp4"

# Extract poster (PNG)
ffmpeg -y -ss 00:00:01 -i wp-content/uploads/2025/descriptive-name.mp4 \
  -frames:v 1 wp-content/uploads/2025/descriptive-name-poster.png

# Convert poster to 1000px lossless WebP (cwebp or ImageMagick)
cwebp -lossless -resize 1000 0 \
  wp-content/uploads/2025/descriptive-name-poster.png \
  -o wp-content/uploads/2025/descriptive-name-poster.webp

# Remove intermediate PNG (always)
rm wp-content/uploads/2025/descriptive-name-poster.png
```

### Video Embed Snippets
```html
<!-- Standard landscape or square -->
<video controls playsinline preload="metadata"
       poster="{{ '/wp-content/uploads/YYYY/descriptive-name-poster.webp' | prepend: site.baseurl }}"
       style="max-width:100%;height:auto">
  <source src="{{ '/wp-content/uploads/YYYY/descriptive-name.mp4' | prepend: site.baseurl }}" type="video/mp4">
</video>

<!-- Portrait/tall clip: narrower centered layout -->
<video controls playsinline preload="metadata"
       poster="{{ '/wp-content/uploads/YYYY/descriptive-name-poster.webp' | prepend: site.baseurl }}"
       style="width:100%;max-width:360px;height:auto;display:block;margin:0 auto;">
  <source src="{{ '/wp-content/uploads/YYYY/descriptive-name.mp4' | prepend: site.baseurl }}" type="video/mp4">
</video>
```

## Final Checklist
- File in correct `_posts/` year folder with `YYYY-MM-DD-slug.md`.
- Front matter complete; `image` is an absolute path under `/wp-content/uploads/YYYY/`.
- Excerpt break `<!--more-->` present; content follows house tone.
- Internal links use Liquid with `site.baseurl`; wording unchanged.
- Images converted to 1000px WebP; videos have poster WebP and sensible width.
- No intermediate poster PNGs left behind (delete after WebP is created).
- Originals remain in `zz_incoming_media/` until approved.

## Audio Article System

The blog uses an automated pipeline to generate audio narrations for posts using Qwen-3 TTS Voice Cloning on Kaggle.

### How It Works
1.  **Trigger**: The system checks for posts *missing* the `audio_slug` in Front Matter.
2.  **Scraping**: The notebook scrapes the post content.
    -   **Inclusions**: `p`, `h1-h6`, `li`, `blockquote`.
    -   **Exclusions**: `pre` (code), `figcaption` (captions), and "Comments" sections.
    -   **Normalization**: Whitespace is normalized; "Hung" is pronounced "Hang" (case-sensitive) for audio but preserved in text.
3.  **Generation**: Qwen-3 TTS generates MP3 audio and VTT transcripts.
4.  **Delivery**: Files are uploaded to R2. A GitHub Dispatch event triggers a workflow to update the post's `audio_slug` in the repository provided `GITHUB_TOKEN` is set.

### Kaggle Workflow
To run the generation pipeline (requires `KAGGLE_API_TOKEN`):

1.  **Navigate**: Go to `scripts/qwen3-tts-batch` (for multiple posts) or `scripts/qwen3-tts-single` (testing).
2.  **Push**: Run `kaggle kernels push` to start the notebook.
3.  **Status**: Monitor with `kaggle kernels status hungtruong64/qwen3-tts-voice-clone-demo-batch-processing`.

### Frontend Integration
The Jekyll layout (`_layouts/post.html`) and JavaScript (`assets/js/vtt-inject.js`) handle the playback and transcript synchronization:

1.  **Player Injection**: If `page.audio_slug` exists, `_layouts/post.html` injects an `<audio>` tag pointing to `/assets/audio/[audio_slug].mp3`.
2.  **Transcript Fetching**: The same slug is used to fetch the VTT file at `/assets/audio/[audio_slug].vtt`.
3.  **DOM Synchronization**: `vtt-inject.js` parses the VTT cues and traverses the DOM of the post content (`#hypertranscript`). It wraps matching text nodes in `<span>` tags with `data-m` (milliseconds) attributes.
4.  **Interactive Playback**: `HyperaudioLite` uses these spans to highlight words in sync with audio and allows clicking text to jump to that timestamp.

### Regenerating Audio
To force regeneration (e.g., after fixing typos or scraper logic):
1.  **Remove `audio_slug`**: Delete the line from the post's front matter.
2.  **Push**: Commit and push the removal to GitHub.
3.  **Run Batch**: Execute the Kaggle batch notebook. It will detect the missing audio (since the slug is gone) and regenerate it.
    - Note: The scraper logic handles `<li>` tags, so missing bullet points should be resolved by this process.

### Auditing
If you suspect missing content:
- Use a script (like `audit_missing_bullets.py`, though keep it local/ignored) to check for list items in markdown that are absent from VTT.
- If inconsistencies are found, use the regeneration steps above.

# CRITICAL RULES
- DO NOT push to Kaggle (`kaggle kernels push`) unless EXPLICITLY requested by the user. Always ask for confirmation first.
