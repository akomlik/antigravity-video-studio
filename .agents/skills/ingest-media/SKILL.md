---
name: ingest-media
description: Universal pre-processor for any video project folder (cycling ride, hike/excursion, party/event, or archival slideshow). Runs ranger-sync if needed, converts HEIC to JPG, extracts .proxies/ video thumbnails, and saves project_manifest.json to Google Drive 04_Project_Catalog/YEAR/.
---

# Ingest & Synchronize Universal Project Media (`/ingest-media`)

## Execution Instructions (`agvs_core.ingest_sync`)
1. Runs seamlessly on **Gemini 4 Carbon / Argon** (Google AI Ultra unified frontier workflow).
2. Execute the thin CLI wrapper `scripts/ingest_and_sync_media.py` (backed by `agvs_core.ingest_sync`) without reading its source code into context.
3. Run `ingest_and_sync_media.py` on the target folder (add `--force-resync` if you want to re-run `ranger-sync` on an already-synced folder, or `--skip-bleequp-sync` to skip):
   ```bash
   python3 ./.agents/skills/ingest-media/scripts/ingest_and_sync_media.py --project-dir "<path_to_folder>" --genre auto
   ```
   *(What this does automatically:*
   - *Converts `.HEIC` $\rightarrow$ `.jpg` and copies all EXIF + GPS + macOS Finder `FileCreateDate`/`FileModifyDate` from `.HEIC` to `.jpg`.*
   - *Runs `ranger-sync apply --auto-shift --rename-shifted --write-filesystem` to auto-detect BleeqUP Camera SoC sleep-oscillator drift (both whole-ride drift and mid-ride Camera Settings sync overlaps), rename shifted BleeqUP 13-digit epoch filenames to their true capture time, inject GPX coordinates, and align macOS Finder creation/modification dates across all BleeqUP and iPhone files so Quick Look scrolls in 100% chronological shot order.*
   - *Extracts `.proxies/*_thumb.jpg` + `*_strip.jpg` and runs `verify_and_refine_bleequp_stop_sync` (`gemini-3.8-flash`) to catch and refine any subtle `10–300s` stop-arrival RTC drift.)*
4. Read the resulting `project_manifest.json` summary block (`detected_genre`, `storyboard_status`, `recommended_music_candidates`, and `project_summary`) and report:
   - Detected Project Genre (`cycling_ride`, `hike_outdoor`, `social_event`, or `archival_slideshow`).
   - Status of `Storyboard.md` (`existing`, `created_skeleton_needs_refinement` — if skeleton, immediately transition into `/storyboard` visual inspection!).
   - Top recommended background music tracks from `03_Audio_Library/01_Curated_BGM/` (or suggest running `/find-music` on open YouTube Audio Library / CreatorMix tabs if the category folder is empty).
