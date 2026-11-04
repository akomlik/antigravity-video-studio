---
name: publish-youtube
description: Generates Imperial-first YouTube metadata, clean 00:00 chapters, EN/UA/RU localizations & .srt subtitle tracks, and a 16:9 Composite Thumbnail from Storyboard.md and the .fcproj timeline, then uploads 1 (en_only / option_a) or 3 (option_b) 4K editions to the @akomlik YouTube channel via headless YouTube Data API v3 (1Password direnv-mcp).
---

# Stage 4: YouTube Metadata, Composite Thumbnail & Multi-Language Upload (`/publish-youtube`)

## Purpose
Turns any finished 4K `.mp4` export and `.fcproj` project into a complete YouTube release package (`youtube_metadata.json`, `captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`, and `thumbnail.jpg`) and publishes it to Alexander's `@akomlik` YouTube channel using headless OAuth (`1Password` via `direnv-mcp`).

## Key Studio v2 Rules
1. **Strict ISO Code `ua` for Ukraine Locally:** Always use `ua` (`UA`) in all local filenames (`captions.ua.srt`, `voiceover_ua_part1.wav`, `_UA.mp4`) and `Storyboard.md` / `youtube_metadata.json` keys. `upload_youtube_api.py` automatically translates `"ua" -> "uk"` only on the YouTube Data API v3 wire.
2. **YouTube Chapter Parser Rule:** YouTube uses the **last** `00:00` timestamp block in a video's description to label the scrub-bar chapters. Therefore, inline `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` blocks inside the English description must **never** include `00:00` chapter lists (localized chapters belong strictly inside `localizations["ua"]` and `localizations["ru"]`).
3. **1Password Headless Auth (`direnv-mcp`):** Never store `client_secret.json` on disk. Always invoke `upload_youtube_api.py` via `~/src/ai-workflow/scripts/direnv-mcp` (`GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, `GEMINI_API_KEY`).

## Step 1: Generate Metadata Package, `.srt` Tracks & Composite Thumbnail
Run `generate_youtube_metadata.py`:
```bash
~/src/ai-workflow/scripts/direnv-mcp python3 ./.agents/skills/publish-youtube/scripts/generate_youtube_metadata.py \
  --project-dir "./04_Project_Catalog/YEAR/<project_name>" \
  --mp4 "~/Movies/Exports/YEAR/<project_name>.mp4" \
  --thumb-mode preserve \
  --thumb-text "SAVED AT THE GATE"
```
- **Thumbnail Modes (`--thumb-mode`):**
  - `preserve` (default): Keeps an existing custom/composite `thumbnail.jpg` in the project directory (such as a YouTube Studio "Ask Suggestions" export or co-designed composite).
  - `composite_ai`: Uses Gemini 3 Pro Image (`gemini-3-pro-image-preview`) with `--thumb-hero <hero.jpg>`, `--thumb-prop <prop.jpg>`, and `--thumb-text "<3-4 WORD HOOK>"` to generate a YouTube-Studio-style composite thumbnail (blurred scenic backdrop + left smiling rider + right white-bordered sticker cutout of the key prop + bold yellow/white top headline).
  - `frame`: Extracts a clean 1920×1080 frame at `--thumb-sec`.

## Step 2: Upload to `@akomlik` Channel (`en_only`, `option_a`, or `option_b`)
### Mode 1: Single Video Upload (`en_only` or `option_a` — Everyday Default)
Uploads the 4K English Master (`private`), sets localized `EN`/`UA`/`RU` Titles & Descriptions, uploads `captions.en.srt`, `captions.ua.srt`, and `captions.ru.srt`, and sets `thumbnail.jpg`:
```bash
~/src/ai-workflow/scripts/direnv-mcp python3 ./.agents/skills/publish-youtube/scripts/upload_youtube_api.py \
  --metadata "./04_Project_Catalog/YEAR/<project_name>/youtube_metadata.json" \
  --privacy private
```
*(To update metadata/captions/thumbnail on an already-uploaded video without re-uploading the MP4, add `--update-existing <VIDEO_ID>`).*

### Mode 2: Full 3-Edition Multi-Language Upload (`option_b` — Special Occasions & Family Stories)
Uploads the 4K **🇺🇦 Ukrainian Edition** (`_UA.mp4`, **Unlisted**) and **🇷🇺 Russian Edition** (`_RU.mp4`, **Unlisted**) with their native replicated voice-over tracks and `.srt` captions, then uploads/updates the 4K **🇺🇸 English Master** (**Private**) with prominent clickable `▶️ Дивитися з українською озвучкою` and `▶️ Смотреть с русской озвучкой` links injected into the description, and applies `thumbnail.jpg` to all 3 videos:
```bash
~/src/ai-workflow/scripts/direnv-mcp python3 ./.agents/skills/publish-youtube/scripts/upload_youtube_api.py \
  --metadata "./04_Project_Catalog/YEAR/<project_name>/youtube_metadata.json" \
  --privacy private \
  --option-b
```
