---
name: publish-youtube
description: Generates Imperial-first YouTube metadata, clean 00:00 chapters, EN/UA/RU localizations & .srt subtitle tracks, and localized 16:9 Composite Thumbnails from Storyboard.md and the .fcproj timeline, then uploads 1 (en_only / option_a) or 3 (option_b) 4K editions to YouTube via headless YouTube Data API v3.
---

# Stage 4: YouTube Metadata, Composite Thumbnail & Multi-Language Upload (`/publish-youtube`)

## Purpose
Turns any finished 4K `.mp4` export and `.fcproj` project into a complete YouTube release package (`youtube_metadata.json`, `captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`, and `thumbnail.jpg` / `thumbnail_ua.jpg` / `thumbnail_ru.jpg`) and publishes it to YouTube using the YouTube Data API v3.

## Key Studio v2 Rules
1. **Hook-First Titles (Mobile & Algorithm Optimized):** Default to the high-curiosity narrative hook as the primary title (e.g. `Saved by Nina's Sharp Eyes! Escorting to Zumba & 21.5 mi Pollença Loop`) rather than front-loading date stamps (`YYYY-MM-DD · ...`), which truncate on mobile. Archive date titles are preserved in `title_alternatives` and `recordingDetails.recordingDate`.
2. **Automated Pinned Language Switcher Comment:** When uploading multi-language projects (`--option-b`), `upload_youtube_api.py` automatically posts a top-level language switcher comment on the English master linking directly to the Ukrainian and Russian voiced editions so mobile viewers have 1-click access without expanding the description.
3. **Strict ISO Code `ua` for Ukraine Locally:** Always use `ua` (`UA`) in all local filenames (`captions.ua.srt`, `voiceover_ua_part1.wav`, `thumbnail_ua.jpg`, `_UA.mp4`) and `Storyboard.md` / `youtube_metadata.json` keys. `upload_youtube_api.py` automatically translates `"ua" -> "uk"` only on the YouTube Data API v3 wire.
4. **YouTube Chapter Parser Rule:** YouTube uses the **last** `00:00` timestamp block in a video's description to label the scrub-bar chapters. Therefore, inline `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` blocks inside the English description must **never** include `00:00` chapter lists (localized chapters belong strictly inside `localizations["ua"]` and `localizations["ru"]`).
5. **Mandatory Recording Date (`recordingDetails.recordingDate`):** Every uploaded or updated video (including `EN`, `UA`, and `RU` editions) MUST set `recordingDetails.recordingDate` (`YYYY-MM-DDT00:00:00.000Z`, derived from `recording_date` in `youtube_metadata.json` or the `YYYY-MM-DD` project folder prefix) via `part="snippet,status,localizations,recordingDetails"`.
6. **Environment Inheritance (Zero Wrapper Dependencies):** Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, and `GOOGLE_OAUTH_CLIENT_SECRET` using your preferred environment manager (e.g., `direnv` + 1Password, shell profile, or a local `.env` file) and start Antigravity from that shell session so all child processes inherit them automatically. Once authorized once, `~/.config/antigravity_youtube/token.json` caches the OAuth refresh token for zero-prompt future uploads.
7. **Automated Facebook Promotional Package (`facebook_promo.md`):** Automatically generates three copy-ready Facebook post strategies upon metadata generation and post-upload completion, saving to `04_Project_Catalog/YEAR/<project_name>/facebook_promo.md` and printing the ready-to-copy box directly to the console:
   - **Option 1 (The Curiosity Hook — Algorithm-Optimized):** Zero outbound links in the post text (prevents Facebook's feed reach suppression) + personal backstory and cliffhanger, with the YouTube link and language edition notes formatted for the First Comment.
   - **Option 2 (Direct Story Narrative):** All-in-one post with emoji highlights and embedded video link.
   - **Option 3 (Bilingual / Classmates):** English story hook + UA/RU localized context for European and Ukrainian friends.

## Step 1: Generate Metadata Package, `.srt` Tracks & Composite Thumbnail
Run `generate_youtube_metadata.py`:
```bash
./.venv/bin/python ./.agents/skills/publish-youtube/scripts/generate_youtube_metadata.py \
  --project-dir "./04_Project_Catalog/YEAR/<project_name>" \
  --mp4 "~/Movies/Exports/YEAR/<project_name>.mp4" \
  --thumb-mode preserve \
  --thumb-text "SAVED AT THE GATE" \
  --thumb-text-ua "ВРЯТОВАНИЙ БІЛЯ ВОРІТ" \
  --thumb-text-ru "СПАСЁН У ВОРОТ"
```
- **Thumbnail Modes (`--thumb-mode`):**
  - `preserve` (default): Keeps an existing custom/composite `thumbnail.jpg` in the project directory and automatically generates localized `thumbnail_ua.jpg` and `thumbnail_ru.jpg` if missing.
  - `composite_ai`: Uses Gemini 3 Pro Image (`gemini-3-pro-image-preview`) with `--thumb-hero <hero.jpg>`, `--thumb-prop <prop.jpg>`, and `--thumb-text "<3-4 WORD HOOK>"` to generate a YouTube-Studio-style composite thumbnail (blurred scenic backdrop + left smiling rider + right white-bordered sticker cutout of the key prop + bold yellow/white top headline).
  - `frame`: Extracts a clean 1920×1080 frame at `--thumb-sec`.

## Step 2: Upload to YouTube (`en_only`, `option_a`, or `option_b`)
### Mode 1: Single Video Upload (`en_only` or `option_a` — Everyday Default)
Uploads the 4K English Master (`private`), sets localized `EN`/`UA`/`RU` Titles & Descriptions, uploads `captions.en.srt`, `captions.ua.srt`, and `captions.ru.srt`, and sets `thumbnail.jpg`:
```bash
./.venv/bin/python ./.agents/skills/publish-youtube/scripts/upload_youtube_api.py \
  --metadata "./04_Project_Catalog/YEAR/<project_name>/youtube_metadata.json" \
  --privacy private
```
*(To update metadata/captions/thumbnail on an already-uploaded video without re-uploading the MP4, add `--update-video-id <VIDEO_ID>`).*

### Mode 2: Full 3-Edition Multi-Language Upload (`option_b` — Special Occasions & Family Stories)
Uploads the 4K **🇺🇦 Ukrainian Edition** (`_UA.mp4`, **Unlisted**, with `thumbnail_ua.jpg`) and **🇷🇺 Russian Edition** (`_RU.mp4`, **Unlisted**, with `thumbnail_ru.jpg`) with their native replicated voice-over tracks and `.srt` captions, then uploads/updates the 4K **🇺🇸 English Master** (**Private**, with `thumbnail.jpg`) with clickable links to both localized editions:
```bash
./.venv/bin/python ./.agents/skills/publish-youtube/scripts/upload_youtube_api.py \
  --metadata "./04_Project_Catalog/YEAR/<project_name>/youtube_metadata.json" \
  --privacy private \
  --option-b
```

## Step 3: Social Promotion (Facebook & Beyond)
When `upload_youtube_api.py` finishes, it automatically prints the copy-ready Facebook post box to the console and saves the full formatted package with the live YouTube URL to:
`04_Project_Catalog/YEAR/<project_name>/facebook_promo.md`

To share on Facebook:
1. Open `facebook_promo.md`.
2. Copy the **Option 1 Post Text** and paste into Facebook (attach 1–3 still photos from the project for maximum algorithmic reach).
3. Post the update, then immediately paste the **Option 1 First Comment** (which includes the clean YouTube link and localized language edition notes).
