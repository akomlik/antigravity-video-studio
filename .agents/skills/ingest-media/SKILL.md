---
name: ingest-media
description: Universal pre-processor for any video project folder (cycling ride, hike/excursion, party/event, or archival slideshow). Runs ranger-sync if needed, converts HEIC to JPG, extracts .proxies/ video thumbnails, migrates Context.md to Storyboard.md, and saves project_manifest.json to Google Drive 04_Project_Catalog/YEAR/.
---

# Ingest & Synchronize Universal Project Media (`/ingest-media`)

## Model & Execution Instructions
1. Execute this skill using **Gemini 3.8 Flash** to preserve Gemini 4 Argon quota.
2. Treat `scripts/ingest_and_sync_media.py` as a black box—do not read its source code into context.
3. If the target folder was already fixed by `ranger-sync` (`bleequp-ranger-sync`), pass `--skip-bleequp-sync`:
   ```bash
   python3 ~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/.agents/skills/ingest-media/scripts/ingest_and_sync_media.py --project-dir "<path_to_folder>" --genre auto --skip-bleequp-sync
   ```
4. Read the resulting `project_manifest.json` summary block (`detected_genre`, `storyboard_status`, `recommended_music_candidates`, and `project_summary`) and report:
   - Detected Project Genre (`cycling_ride`, `hike_outdoor`, `social_event`, or `archival_slideshow`).
   - Status of `Storyboard.md` (`existing`, `migrated_from_Context_md`, or `created_skeleton_needs_refinement` — if skeleton, immediately transition into `/storyboard` visual inspection!).
   - Top recommended background music tracks from `~/Music/Cycling_BGM/` (or suggest running `/find-music` on open YouTube Audio Library / CreatorMix tabs if the category folder is empty).
