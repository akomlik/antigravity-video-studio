---
name: publish-youtube
description: Generates Imperial-first YouTube metadata, clean 00:00 chapters, EN/UA/RU localizations & .srt subtitle tracks, and localized 16:9 Composite Thumbnails from Storyboard.md and the .fcproj timeline, then uploads 1 (en_only / option_a) or 3 (option_b) 4K editions to YouTube via headless YouTube Data API v3.
---

# Stage 4: YouTube Metadata, Composite Thumbnail & Multi-Language Upload (`/publish-youtube`)

## Purpose
Turns any finished 4K `.mp4` export and `.fcproj` project into a complete YouTube release package (`youtube_metadata.json`, `captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`, and `thumbnail.jpg` / `thumbnail_ua.jpg` / `thumbnail_ru.jpg`) and publishes it to YouTube using the YouTube Data API v3.

## Key AGVS v3 Rules (`agvs_core.youtube_pub` & `publish_service`)
1. **Mandatory Human Approval Gate & Default `unlisted` Visibility:** Never upload without explicit human sign-off (`HumanApprovalRequiredError`). Default all uploads to `privacy_status: "unlisted"` so pinned language-switcher comments and link previews never fail with HTTP 403.
2. **Hook + Landmark Titles (Cold-Viewer CTR & Search Optimized):** Combine a concrete cycling/tactical curiosity hook with high-intent Mallorca landmarks (e.g. `568W Harley Draft, Hidden Mallorca History & 72°F Crocodile Beach Swim (32.6 mi)` or `Trapped into the Climb: Passing Bruce on Coll de Sa Batalla (57.1 mi)`) rather than vague lifestyle phrases or front-loaded date stamps (`YYYY-MM-DD · ...`). Archive date titles are preserved in `title_alternatives` and `recordingDetails.recordingDate`. Always flip the reviewed `unlisted` upload directly to `public` rather than re-uploading so 100% of watch-time velocity stays on a single `video_id`.
3. **Automated Pinned Language Switcher Comment:** When uploading multi-language projects (`--option-b`), `upload_youtube_api.py` automatically posts a top-level language switcher comment on the English master linking directly to the Ukrainian and Russian voiced editions so mobile viewers have 1-click access without expanding the description.
4. **Strict ISO Code `ua` for Ukraine Locally:** Always use `ua` (`UA`) in all local filenames (`captions.ua.srt`, `voiceover_ua_part1.wav`, `thumbnail_ua.jpg`, `_UA.mp4`) and `Storyboard.md` / `youtube_metadata.json` keys. `agvs_core.youtube_pub` automatically translates `"ua" -> "uk"` exclusively at the YouTube Data API v3 wire boundary, with SHA-256 `.srt` hash caching to save 1,200 API quota units on updates.
4. **YouTube Chapter Parser Rule:** YouTube uses the **last** `00:00` timestamp block in a video's description to label the scrub-bar chapters. Therefore, inline `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` blocks inside the English description must **never** include `00:00` chapter lists (localized chapters belong strictly inside `localizations["ua"]` and `localizations["ru"]`).
5. **Mandatory Recording Date (`recordingDetails.recordingDate`):** Every uploaded or updated video (including `EN`, `UA`, and `RU` editions) MUST set `recordingDetails.recordingDate` (`YYYY-MM-DDT00:00:00.000Z`, derived from `recording_date` in `youtube_metadata.json` or the `YYYY-MM-DD` project folder prefix) via `part="snippet,status,localizations,recordingDetails"`.
6. **Environment Inheritance & Zero-File 1Password Integration:** Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and optionally `GOOGLE_OAUTH_REFRESH_TOKEN` via your preferred environment manager (`direnv` + 1Password `envvar:*` protocol). When `GOOGLE_OAUTH_REFRESH_TOKEN` is present in the environment, credentials refresh completely in-memory with zero tokens or json files stored on disk. If absent, it safely falls back to caching in `~/.config/antigravity_youtube/token.json`.
7. **Automated Facebook Promotional Package (`facebook_promo.md`):** Automatically generates copy-ready Facebook post strategies upon metadata generation and post-upload completion, saving to `04_Project_Catalog/YEAR/<project_name>/facebook_promo.md` and printing the ready-to-copy box directly to the console:
   - **Option 1 (Direct YouTube Link Card — Default & Proven 265+ Views Standard):** Story hook + direct YouTube URL in the post body (without attaching separate photo files, so Facebook renders the full-width clickable 16:9 `YOUTUBE.COM` preview card from `thumbnail.jpg`), plus optional Flickr RU link.
   - **Option 2 (Story + Highlights + Direct Link):** All-in-one post with emoji highlights and embedded video link.
   - **Option 3 (Bilingual / Classmates):** English story hook + UA/RU localized context for European and Ukrainian friends.
   - **Option 4 (Mallorca Cycling Facebook Group — Authentic Route Story, Zero Hashtags):** Multi-paragraph peer rider story sharing local road/café intel + community question + `first_comment` YouTube link (never `#procyclehire` or repetitive 1-line link drops, max 1–2x/week to respect group anti-spam rules).

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

## Step 2: Upload to YouTube (`en_only`, `option_a`, or `option_b` — Default `unlisted`)
### Mode 1: Single Video Upload (`en_only` or `option_a` — Everyday Default)
Uploads the 4K English Master (`unlisted` default), sets localized `EN`/`UA`/`RU` Titles & Descriptions, uploads SHA-256 hash-cached `captions.en.srt`, `captions.ua.srt`, and `captions.ru.srt`, and sets `thumbnail.jpg`:
```bash
./.venv/bin/python ./.agents/skills/publish-youtube/scripts/upload_youtube_api.py \
  --metadata "./04_Project_Catalog/YEAR/<project_name>/youtube_metadata.json" \
  --privacy unlisted
```
*(Idempotent on partial resume; to update metadata/captions/thumbnail on an already-uploaded video without re-uploading the MP4, add `--update-video-id <VIDEO_ID>`).*

### Mode 2: Full 3-Edition Multi-Language Upload (`option_b` — Special Occasions & Family Stories)
Uploads the 4K **🇺🇦 Ukrainian Edition** (`_UA.mp4`, **Unlisted**, with `thumbnail_ua.jpg`) and **🇷🇺 Russian Edition** (`_RU.mp4`, **Unlisted**, with `thumbnail_ru.jpg`) with their native Google Gemini TTS voice-over tracks and `.srt` captions, then uploads/updates the 4K **🇺🇸 English Master** (**Unlisted**, with `thumbnail.jpg`) with clickable links and a pinned language-switcher comment:
```bash
./.venv/bin/python ./.agents/skills/publish-youtube/scripts/upload_youtube_api.py \
  --metadata "./04_Project_Catalog/YEAR/<project_name>/youtube_metadata.json" \
  --privacy unlisted \
  --option-b
```

## Step 3: Social Promotion (Facebook & Beyond)
When `upload_youtube_api.py` finishes, it automatically prints the copy-ready Facebook post box to the console and saves the full formatted package with the live YouTube URL to:
`04_Project_Catalog/YEAR/<project_name>/facebook_promo.md`

To share on Facebook & Strava:
1. Open `facebook_promo.md`.
2. Copy the **Option 1 Post Text** (or **Option 4** for the *Mallorca Cycling* group) and paste directly into Facebook **without attaching separate photo files** so Facebook renders the full-width clickable 16:9 `YOUTUBE.COM` preview card from your composite thumbnail.
3. **Strava Sharing Convention (No Links in Comments!):** Strava strips/blocks URLs inside comments. Always put the live YouTube URL inside the **Strava Activity Description**, and if replying to a friend's comment (e.g. `@Joe`), post a link-free comment pointing them up to the activity description ("Added the 4K video link to the ride description above!").
