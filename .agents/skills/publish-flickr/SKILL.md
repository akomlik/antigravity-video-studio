---
name: publish-flickr
description: Uploads video editions (defaulting to Russian-voiced _RU.mp4 or English master) to Flickr via the Flickr API, sets localized Russian/English titles, descriptions, and geodata, adds to albums, and generates WhatsApp/family sharing links.
---

# Flickr Publishing & Censorship Bypass (`/publish-flickr`)

## Purpose
Because YouTube is heavily throttled or blocked in Russia and occupied Crimea, Alexander's family (Nina's brother in Russia, Alexander's sister in Sevastopol) and Institute classmates on WhatsApp rely on Alexander's **Flickr feed (`apkom`)** and WhatsApp channels to watch new cycling videos, family gatherings, and travel movies.

`/publish-flickr` automates uploading the 4K Russian-voiced video (`_RU.mp4`), sets date-prefixed titles with mile/km summaries, syncs GPS coordinates from `Storyboard.md`, assigns the upload to the target Flickr Album (e.g. `2026 Fall Mallorca Cycling`), and outputs a copy-ready WhatsApp sharing snippet.

---

## Key Studio Rules & Conventions

1. **Default Edition (`_RU.mp4`):** Unless overridden, `/publish-flickr` defaults to uploading `<project>_RU.mp4` (`--edition ru`). Lossless remuxing (`ffmpeg -c:v copy`) produces this file in `0.2s` with zero GPU overhead during `/build-timeline`.
2. **Date-Prefixed Russian Title Standard:** Titles follow Alexander's Lightroom/Flickr naming convention:
   `YYYY-MM-DD · <Russian Title> (<Miles> мили / <Kilometers> км)`
   *(e.g., `2026-10-27 · Вместо группы: выпечка в Буже и «VIP»-кофе (40.1 мили / 64.5 км)`)*.
3. **Clean Description Format:** Uses the Russian storyboard logline, stats, and bike notes without algorithmic hashtags or outbound links that trigger spam filters.
4. **Geolocation Sync:** Automatically reads GPS coordinates from `Storyboard.md` or GPX telemetry and sets photo/video latitude and longitude on Flickr (`flickr.photos.geo.setLocation`).
5. **Zero-Plaintext 1Password & direnv Security:** API keys and OAuth tokens can be injected via environment variables:
   - `FLICKR_API_KEY`
   - `FLICKR_API_SECRET`
   - `FLICKR_OAUTH_TOKEN` (optional once authorized)
   - `FLICKR_OAUTH_TOKEN_SECRET` (optional once authorized)
   Fallback cached tokens are safely kept in `~/.config/antigravity_flickr/oauth_token.json` (outside the git repo).
6. **1 GB Upload Ceiling & Automatic 1080p Transcode Guard:** Flickr strictly enforces a 1,000,000,000-byte (1 GB) upload ceiling and drops the connection (`BrokenPipeError`) if a file exceeds it. If `<project>_RU.mp4` exceeds 980 MB, `upload_flickr_api.py` automatically transcodes a visually lossless high-bitrate 1080p copy (14 Mbps, ~300 MB via `h264_videotoolbox`) with `-c:a copy` before streaming to the Flickr API.

---

## One-Time Setup & Authorization

### Option A: 1Password Integration (Recommended)
Add your Flickr App credentials to your 1Password item (or `.envrc` via `op read`):
```bash
export FLICKR_API_KEY="<your_api_key>"
export FLICKR_API_SECRET="<your_api_secret>"
```

### Option B: Interactive Authorization Flow
Run the auth helper once to generate your OAuth tokens via your browser:
```bash
./.venv/bin/python .agents/skills/publish-flickr/scripts/upload_flickr_api.py \
  --project-dir "./04_Project_Catalog/YEAR/<project_name>" \
  --auth
```
Follow the URL printed in the terminal, approve access on Flickr, and paste the 9-digit verifier code. The script saves tokens to `~/.config/antigravity_flickr/oauth_token.json`.

---

## Usage

### 1. Standard Upload (Russian Edition to Flickr Album)
```bash
./.venv/bin/python .agents/skills/publish-flickr/scripts/upload_flickr_api.py \
  --project-dir "./04_Project_Catalog/2026/2026-10-27_Buger_coffee" \
  --edition ru \
  --album "2026 Fall Mallorca Cycling" \
  --privacy public
```

### 2. English Master Upload
```bash
./.venv/bin/python .agents/skills/publish-flickr/scripts/upload_flickr_api.py \
  --project-dir "./04_Project_Catalog/2026/2026-10-27_Buger_coffee" \
  --edition en \
  --album "2026 Fall Mallorca Cycling" \
  --privacy public
```

### 3. Family-Only Upload
```bash
./.venv/bin/python .agents/skills/publish-flickr/scripts/upload_flickr_api.py \
  --project-dir "./04_Project_Catalog/2026/2026-10-27_Buger_coffee" \
  --edition ru \
  --privacy family
```

---

## Output & WhatsApp Delivery
When the upload finishes, the tool prints the live Flickr video URL and a copy-ready WhatsApp message:

```text
================================================================================
📲 COPY-READY WHATSAPP / CLASSMATES MESSAGE
================================================================================
Привет! Новое видео с осенней Майорки:
2026-10-27 · Вместо группы: выпечка в Буже и «VIP»-кофе (40.1 мили / 64.5 км)

Посмотреть на Flickr (без блокировок YouTube):
https://www.flickr.com/photos/apkom/55635551068/
================================================================================
```
