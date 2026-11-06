---
name: storyboard
description: Stage 0 Collaborative Storyboard creator and refiner. Converts HEIC to JPG, generates video proxy thumbnails, inspects all clips/photos/YouTube links, creates or updates Storyboard.md (including Section 5: Production & YouTube Publishing Spec with localization & composite thumbnail settings), asks the user to refine the story, and automatically harvests new people, places, and memories into my_digital_brain.md.
---

# Stage 0: Collaborative Storyboard.md Co-Creator & Memory Harvester (`/storyboard`)

## Purpose
Use this skill as the **first step** on any folder in `~/Movies/YEAR/` (or whenever Alexander drops a 3-to-5-line draft, adds new `.HEIC` photos, YouTube links, or `.gpx` telemetry).

## Quick-Start User Draft Format (What Alexander Can Provide)
Alexander only needs to write a few rough lines in `Storyboard.md` (or in chat), for example:
```markdown
Ride escorting Nina to Bellevue Zumba, then 21.5 mi coastal loop around Pollença Bay.
At the tennis court gate Nina spotted my blue Reynolds front brake pad that fell on the ground!
Added IMG_8777.HEIC (pad on ground) and IMG_8775.HEIC (pad seated in Dura-Ace caliper).
Include 5s of Nina's Zumba video (https://www.youtube.com/watch?v=fGveL-nza0E).
Publish: option_b (all 3 locales: EN Private + UA/RU Unlisted).
Thumbnail: "SAVED AT THE GATE" with selfie + brake caliper cutout.
```

## The 2-Pass Co-Creation Architecture

To maximize creative depth while protecting your 5-hour Argon window:
- **Pass 1: Mechanical Ingest & Scaffold (Run on Gemini 3.8 Flash):**
  Runs all local deterministic tools: converts `.HEIC` $\rightarrow$ `.jpg`, extracts `.proxies/` 640px thumbnails, parses Garmin `.gpx` telemetry, checks camera audio dB levels, and creates the baseline chronological draft of `Storyboard.md`.
- **Pass 2: Creative Director Polish & Memory Weaving (Run on Gemini 4 Argon — Thinking Low/Medium):**
  With all proxies and data already extracted on disk, switch to **Gemini 4 Argon**. Argon acts purely as the Creative Director—reading `my_digital_brain.md`, examining key thumbnails, weaving emotional callbacks and nostalgic flashbacks (like Nina at the fountain in 2018), tightening the 5-act narrative arc, scripting punchy trilingual voice-overs, and designing the composite thumbnail. Zero Argon credits burned on shell execution!

## Execution Sequence
1. **Pass 1 — Automated Prep & Proxy Extraction (Flash):** Run `ingest_and_sync_media.py` on the target folder (passing `--skip-bleequp-sync` if BleeqUP files were already fixed):
   ```bash
   python3 ./.agents/skills/ingest-media/scripts/ingest_and_sync_media.py --project-dir "<path_to_folder>" --genre auto
   ```
   *(Converts `.HEIC` to `.jpg`, extracts 640px proxy thumbnails into `.proxies/`, extracts QuickTime `ISO6709` GPS coordinates and GPX telemetry in Imperial (`mi`, `ft`, `mph`) & Metric, and creates the baseline `Storyboard.md`).*

1b. **Pass 1b — GPX Geospatial Flashback Discovery & Scavenging:**
   If a `.gpx` file is present in the project folder and `lightroom_catalog_dir` is configured in `studio.conf`:
   ```bash
   python3 ./.agents/skills/storyboard/scripts/find_gpx_flashbacks.py --project-dir "<path_to_folder>" --extract-previews
   ```
   *(Scans the active Adobe Lightroom Classic catalog along the ride/hike route in < 3s, checks `LR_Published_4K/` status, stages top candidate preview JPEGs into `<path_to_folder>/.flashback_candidates/`, and surfaces both **4K Published Flashbacks** and **Unrated Hidden Gems** for co-creation selection).*

2. **Pass 2 — Creative Storyboard Polish & Memory Weaving (Argon):**
   - Inspect key `.proxies/*_thumb.jpg` thumbnails, converted `.jpg` stills, `.gpx` track points, and any referenced YouTube URLs.
   - Cross-reference `./my_digital_brain.md` to identify emotional flashbacks, past trips, recurring people (Nina, cycling companions), or gear lore.
   - Polish `<path_to_folder>/Storyboard.md` AND copy it to `04_Project_Catalog/YEAR/<project_name>/Storyboard.md` with **5 structured sections**:
     - **Section 1: Story Overview & Narrative Arc** (Imperial + Metric stats).
     - **Section 2: Multi-Phase Music Plan** (`03_Audio_Library/01_Curated_BGM/` tracks, ducking under VO/dialog, `+3.5 dB` swell during pure riding).
     - **Section 3: Scene-by-Scene Visual & Audio Map** (`Scene 00` -> `Scene N`, exact timecodes, `V1` clips/stills, `V2` GPX corner maps/HUD, `A1` live dialog boost, `A4` voiceover cues).
     - **Section 1: Video Overview, Title Ideas & Multi-Phase Music Selection:**
       - **Title Options:** Always put the hook-first title under `* **Primary (Hook-First / YouTube):**` (no date prefix so mobile titles don't truncate), followed by `* **Alt 1 (Route & Highlights):**`, and `* **Archival (Catalog Index):** YYYY-MM-DD · ...`.
     - **Section 2: The Narrative Story** (chronological scene-by-scene breakdown).
     - **Section 3: Archival Memory & Brain Links** (cross-era links to past years or key people from `my_digital_brain.md`).
     - **Section 4: Multi-Language Voice-Over & Subtitle Scripts (`EN`, `UA`, `RU`)** (always using ISO code `ua` for Ukrainian locally).
     - **Section 5: Production & YouTube Publishing Spec (Tuning Knobs)** — YAML block capturing:
       - `units`: `imperial_default` (`mi`, `ft`, `mph`)
       - `burned_in_titles`: `false` (default, so 4K video stays clean and never collides with YouTube CC subtitles)
       - `gpx_corner_map` (`top_right`, `26%` width) & `gpx_telemetry_hud` (`auto` — shown on moving scenes when 3s speed > 2 mph; suppressed on stills & stationary scenes <= 2 mph)
       - `low_res_broll_mode`: `pip_card` (`65%` centered card over blurred `16:9` backdrop for `< 720p` clips)
       - `audio_mix`: `voiceover_persona: voice_jntybwupjc1s`, `live_dialog_boost: auto`, `bgm_under_vo_db: -7.5`, `bgm_riding_swell_db: +3.5`, `pip_broll_music_db: -6.5`
       - `default_privacy`: `"unlisted"` (default for all uploads to allow immediate comments, previews, and language switchers without public feed spam)
       - `youtube_publishing.publishing_mode`:
         - `option_a` (Recommended Default): 1 clean 4K master (`unlisted`) with matching voiceover + localized `EN`/`UA`/`RU` titles, descriptions & `.srt` subtitles (`captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`). Concentrates views on 1 video while serving multi-lingual audiences via YouTube CC.
         - `en_only`: 1 English 4K video (`unlisted`) with `captions.en.srt`.
         - `option_b`: Special Occasions Only — 3 separate 4K video uploads (EN Master `unlisted` + UA/RU unlisted voiced editions). Always requires explicit confirmation before upload!
       - `thumbnail`: `style: composite_ai` (`headline_text`, `hero_image`, `prop_cutout`) modeled after YouTube Studio's "Ask Suggestions" composite layout.
3. **Step 3 (Automatic Memory Harvesting into `my_digital_brain.md`):**
   - Append any new people, companions, recurring gear/wardrobe, or cross-year links into `./my_digital_brain.md`.
4. **Step 4 (Interactive Co-Design Prompt):**
   - Present the updated `Storyboard.md` (highlighting the Scene Map, characters, and proposed Thumbnail Headline + Hero/Prop pairing) and ask:
     **"Storyboard.md is ready! Would you like to tweak any story details, or run `/build-timeline` to select your music/language in chat and assemble the 4K video?"**
