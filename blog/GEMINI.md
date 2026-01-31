# Jekyll Blog Assistant Guidance (Claude & LLM)
You are an AI agent that helps the user, Hung Truong, write and maintain this blog.

# CRITICAL RULES & PROTOCOLS
- **MISTAKE PROTOCOL**: If you make a mistake, you MUST update `GEMINI.md` with a rule to prevent recurrence.
  - *Added 2026-01-28*: Always verify the current year and date before writing documentation or paths.
  - *Added 2026-01-29*: If user asks to "Commit", do NOT "Push". Only "Push" if the user explicitly says "Push" or "Commit and Push".
  - *Added 2026-01-29*: REPEATED OFFENSE: Do NOT double-down on mistakes. If scolded for pushing, PAUSE and ask for clarification before doing anything git-related again.
  - *Added 2026-01-30*: When debugging build failures, search for framework-specific errors (e.g., "Liquid Exception", "Jekyll") instead of acting on secondary environment warnings (e.g., Git/Submodule noise).
  - *Added 2026-01-30*: When asked a question, prioritize explaining the answer clearly before taking any corrective actions, especially while in PLANNING mode. Do not jump into "fix mode" without user confirmation.
- **VERIFICATION PROTOCOL**: Do NOT consider a visual/UI task complete until you have verified it matches the context (e.g., surrounding text width). If it 'looks wrong', it IS wrong. Don't stop at the first technical 'fix' if the result is visually inconsistent.
- **BROWSER TOOL PROTOCOL**: Prefer `chrome-devtools` MCP over `browser_subagent` whenever possible for inspecting or interacting with pages.
- **ZERO TOLERANCE COMMIT POLICY**: STRICTLY FORBIDDEN from running `git commit` or `git push` unless the user explicitly asks. 
  - **NEVER** assume a "push" is implied by a "commit". 
  - **NEVER** run `git push` if the user only said "commit".
- **PLAN EXECUTION**: UNLESS EXPLICITLY INSTRUCTED, you are STRICTLY FORBIDDEN from executing an `implementation_plan.md` (e.g. `ShouldAutoProceed` MUST be `false`).
- **IMAGE STYLE PREFERENCE**: Always prefer using `<figure>` and `<figcaption>` tags for images and their descriptions over standard Markdown image syntax. Do NOT "invent" or add caption text; only use existing descriptions or if explicitly provided.
- **API KEYS**: The proxy handles OpenRouter API keys. Do NOT request or expect client-side keys.
- **NO TEMPORARY SCRIPTS**: Place one-off analysis or fix scripts in `scripts/temp/` (which is gitignored). Do NOT pollute the root `scripts/` directory with disposable files.
- **CONTEXT LIMITS**: Do NOT worry about context limits prematurely. Send full content unless it's obviously impossible.

## Paths & Naming
- **Posts**: `_posts/2026-2030/YYYY-MM-DD-title-slug.md` (Use correct year folder).
- **Media**: `/wp-content/uploads/YYYY/` (Published) | `zz_incoming_media/` (Staging).
- **Filenames**: Descriptive, kebab-case.

## Front Matter Template
```yaml
---
title: 'Post Title Here'
layout: post
author: Hung
categories: [Tech, AI, Claude, iOS, Music, Blogging, Coding, Lifestyle]
permalink: /YYYY/MM/DD/title-slug/
description: Brief SEO-friendly description
image: /wp-content/uploads/YYYY/featured-or-poster.webp # Absolute site-root path
---
```
```

## Metadata Workflow
Before publishing, ensure high-quality metadata (Category, Tags, SEO Summary) by running:
```bash
python3 scripts/update_post_metadata.py --file _posts/YYYY-MM-DD-title-slug.md
```
This script uses an LLM to assign a standard category, generate specific tags, and write a dense search-optimized summary.
## Content Structure & Linking
- Start with front matter → intro paragraph(s) → `<!--more-->` → body sections.
- When Hung requests a link:
  - Keep the existing wording; add the link inline without rewriting surrounding text.
  - Prefer natural placement that flows with the draft; usually toward the end unless context clearly points elsewhere.
  - Use Liquid for internal links so base URL is respected: `{{ '/YYYY/MM/DD/slug/' | prepend: site.baseurl }}`.

## Media Workflows

### Images
1. **Source**: Take from `zz_incoming_media/`.
2. **Convert**:
   - `magick input.png -resize '1000x>' -define webp:lossless=true output.webp` (Text/Graphics)
   - `magick input.jpg -resize '1000x>' -quality 95 output.webp` (Photos)
3. **Place**: Move to `/wp-content/uploads/YYYY/`. Keep originals in staging until approved.

### Videos
1. **Process**: Generate poster (`ffmpeg -ss 00:00:01 -i input.mp4 -frames:v 1 poster.png`) -> Convert poster to WebP.
2. **Embed**:
   ```html
   <!-- Landscape -->
   <video controls playsinline preload="metadata" poster="{{ '/wp-content/uploads/YYYY/poster.webp' | prepend: site.baseurl }}" style="max-width:100%;height:auto"><source src="..." type="video/mp4"></video>

   <!-- Portrait (Cap width 360px) -->
   <video controls playsinline preload="metadata" poster="..." style="width:100%;max-width:360px;height:auto;display:block;margin:0 auto;"><source src="..." type="video/mp4"></video>
   ```

## Audio Article System
Automated narration via Qwen-3 TTS on Kaggle.

### How to Run (Kaggle)
1. **Navigate**: `scripts/qwen3-tts-batch`.
2. **Push**: `kaggle kernels push`.
3. **Status**: `kaggle kernels status hungtruong64/qwen3-tts-voice-clone-demo-batch-processing`.

### Manual Update (GitHub Actions)
Triggers `audio-update.yml` to download/commit files.
- **Trigger**: Actions tab -> "Audio Update" -> "Run workflow".
- **Inputs**: `slug` (required), `mp3_url`, `vtt_url`.

### Regeneration / Fixes
To force regeneration (e.g. to fix typos):
1. **Remove** `audio_slug` line from the post's front matter.
2. **Commit & Push**.
3. **Run Batch** on Kaggle. It will detect the missing audio and regenerate.

### Local Generation (Mac Studio / MLX)
For faster, local generation without Kaggle, use the MLX-based script:
- **Dependencies**: Uses `uv` to handle dependencies automatically.
- **Run**:
  ```bash
  uv run scripts/generate_blog_audio_mlx.py "https://www.hung-truong.com/blog/YYYY/MM/DD/slug/"
  ```
- **Options**:
  - `--model`: Defaults to `mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16`.
  - `--output`: Directory to save `.m4a` and `.vtt` files.


## Semantic Search System
A vector-based search engine leveraging Cloudflare Workers AI (Qwen3-0.6b embeddings) and Cloudflare Vectorize.

### Core Components
- **Embeddings**: `@cf/qwen/qwen3-embedding-0.6b` (8192 token context loop, 8MB payload limit).
- **Index**: 
  - `blog-index-content` (Primary): Embeds `Title + Summary + Full Body`.
  - `blog-index` (Legacy): Embeds `Title + Summary` only.

### Indexing (`scripts/smart_indexer.py`)
This process is automated via GitHub Actions to keep Cloudflare Vectorize in sync.

- **Automated Update**: Triggers on any push to `_posts/` via the `reindex-vector-db.yml` workflow.
- **Manual Trigger**: Can be run from the Actions tab or locally: `python3 scripts/smart_indexer.py --mode content`.
- **Logic (Zero-Cache Remote Sync)**: 
  - **Source of Truth**: The script fetches the list of all vector IDs and their content hashes directly from Cloudflare metadata at runtime.
  - **Delta Processing**: Only new/modified posts are embedded and upserted. 
  - **Auto-Purge**: Any vectors in Cloudflare that no longer exist on disk are automatically deleted.
  - **Batching**: Uses greedy batching (max 3000 tokens/batch) and respects Cloudflare's `get_by_ids` limit (20 per request).

### Search API (`search-api/`)
Custom Cloudflare Worker handling vector search requests.
- **URL**: `https://blogsearch.hung-truong.com`
- **Default Behavior**: Queries `blog-index-content` (Full Content).
- **Legacy Mode**: `https://blogsearch.hung-truong.com?index_type=summary`
- **Deployment**: `npx wrangler deploy` in `search-api/` directory.

### Debugging & Verification
To verify the index quality or debug missing results:
1. **Compare Indices**: Use `scripts/compare_indices.py` to run side-by-side queries.
2. **Missing Posts**: Check `scripts/check_skipped_posts.py` if posts appear missing.
3. **Status Check**: Check the latest run of the "Reindex Vector Database" GitHub Action.
