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

## Execution Sequence
1. **Step 1 (Automated Prep & Proxy Extraction):** Run `ingest_and_sync_media.py` on the target folder (passing `--skip-bleequp-sync` if BleeqUP files were already fixed):
   ```bash
   python3 ~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/.agents/skills/ingest-media/scripts/ingest_and_sync_media.py --project-dir "<path_to_folder>" --genre auto
   ```
   *(Converts `.HEIC` to `.jpg`, extracts 640px proxy thumbnails into `.proxies/`, extracts QuickTime `ISO6709` GPS coordinates and GPX telemetry in Imperial (`mi`, `ft`, `mph`) & Metric, and creates/migrates `Storyboard.md`).*
2. **Step 2 (Multimodal Visual Inspection & Storyboard Co-Development):**
   - Inspect all `.proxies/*_thumb.jpg` thumbnails, converted `.jpg` stills, `.gpx` track points, and any referenced YouTube URLs.
   - Measure live camera audio in clips where the rider or companions speak so `live_dialog_boost` can be planned.
   - Write or update `<path_to_folder>/Storyboard.md` AND copy it to `04_Project_Catalog/YEAR/<project_name>/Storyboard.md` with **5 structured sections**:
     - **Section 1: Story Overview & Narrative Arc** (Imperial + Metric stats).
     - **Section 2: Multi-Phase Music Plan** (`~/Music/Cycling_BGM/` tracks, ducking under VO/dialog, `+3.5 dB` swell during pure riding).
     - **Section 3: Scene-by-Scene Visual & Audio Map** (`Scene 00` -> `Scene N`, exact timecodes, `V1` clips/stills, `V2` GPX corner maps/HUD, `A1` live dialog boost, `A4` voiceover cues).
     - **Section 4: Multi-Language Voice-Over & Subtitle Scripts (`EN`, `UA`, `RU`)** (always using ISO code `ua` for Ukrainian locally).
     - **Section 5: Production & YouTube Publishing Spec (Tuning Knobs)** — YAML block capturing:
       - `units`: `imperial_default` (`mi`, `ft`, `mph`)
       - `burned_in_titles`: `false` (default, so 4K video stays clean and never collides with YouTube CC subtitles)
       - `gpx_corner_map` (`top_right`, `26%` width) & `gpx_telemetry_hud` (`auto` — suppressed when speed `< 5 mph`)
       - `low_res_broll_mode`: `pip_card` (`65%` centered card over blurred `16:9` backdrop for `< 720p` clips)
       - `audio_mix`: `voiceover_persona: voice_jntybwupjc1s`, `live_dialog_boost: auto`, `bgm_under_vo_db: -7.5`, `bgm_riding_swell_db: +3.5`, `pip_broll_music_db: -6.5`
       - `youtube_publishing.publishing_mode`:
         - `en_only`: 1 English 4K video (`private`) with `captions.en.srt`
         - `option_a`: 1 English 4K video (`private`) with localized `EN`/`UA`/`RU` titles, descriptions & `.srt` subtitles (`captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`)
         - `option_b`: **Full 3-Edition Multi-Language Upload** — 1 English 4K Master (`private`) + `0.2s` lossless remuxed `🇺🇦 UA` (`_UA.mp4`, `unlisted`) & `🇷🇺 RU` (`_RU.mp4`, `unlisted`) editions with native `UA`/`RU` replicated voice-over, cross-linked at the top of the `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` sections of the English description
       - `thumbnail`: `style: composite_ai` (`headline_text`, `hero_image`, `prop_cutout`) modeled after YouTube Studio's "Ask Suggestions" composite layout.
3. **Step 3 (Automatic Memory Harvesting into `my_digital_brain.md`):**
   - Append any new people, companions, recurring gear/wardrobe, or cross-year links into `~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/my_digital_brain.md`.
4. **Step 4 (Interactive Co-Design Prompt):**
   - Present the updated `Storyboard.md` (highlighting the Scene Map, Section 5 `publishing_mode`, and the proposed 3–4 word Thumbnail Headline + Hero/Prop pairing) and ask:
     **"Storyboard.md (including Section 5 YouTube Publishing & Thumbnail Spec) is ready. Would you like to tweak any scene or thumbnail/localization setting, or run `/magic-movie` to build and publish?"**
