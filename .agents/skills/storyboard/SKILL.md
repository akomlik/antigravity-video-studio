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

## Unified Frontier Co-Creation Architecture (Google AI Ultra)

With **Google AI Ultra (`Gemini 4 Carbon / Argon`)**, run the entire Stage 0 co-creation flow end-to-end on the frontier model without manual Flash/Argon toggling:
- **Phase 1: Mechanical Ingest & Scaffold (`agvs_core.ingest_sync` + `ranger_sync` v0.2):**
  Runs all deterministic pre-flight & ingest tools: validates BleeqUP physical/QuickTime-atom continuity, converts `.HEIC` $\rightarrow$ `.jpg`, extracts `.proxies/` 640px thumbnails & contact strips, parses Garmin `.gpx` telemetry (`>= 40m` grade smoothing + ride-date GPX selection), and synchronizes `Storyboard.md` non-destructively.
- **Phase 2: Creative Director Polish & Memory Weaving (`Gemini 4 Carbon / Argon`):**
  Reads `my_digital_brain.md`, examines key thumbnails and `.lrcat` route flashbacks, weaves emotional callbacks, tightens the narrative arc around a single Controlling Idea (`Сверхзадача`), scripts punchy trilingual voice-overs, and designs the composite thumbnail.

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

2. **Phase 2 — Creative Storyboard Polish & Memory Weaving (`Gemini 4 Carbon / Argon`):**
   - **Article XIII Long-Clip Semantic Subclip Rule:** For all video clips $\ge 12\text{s}$, never guess `src_in: 0.0` or `5.0`. Consult the programmatic `subclips` and `landmarks` indexed by `extract_video_subclips.py` (`agvs_core.ai_creative`) in `project_manifest.json` and Section 3 of `Storyboard.md`. When a scene mentions a landmark (e.g. Hotel Pollentia, Restaurante Miramar, Muralles d'Alcúdia, S'Àmfora), select `[src_in, src_in + dur]` to cleanly frame that landmark with at least 3.0–4.0s dwell time so the audience can absorb its history. Inspect key `.proxies/*_thumb.jpg` thumbnails and `.proxies/*_strip.jpg` contact sheets, converted `.jpg` stills, `.gpx` track points (including peak power sprints $\ge 600\text{ W}$), and any referenced YouTube URLs.
   - Cross-reference `./my_digital_brain.md` to identify emotional flashbacks, past trips, recurring people (Nina, cycling companions), or gear lore.
   - **Upfront "Controlling Idea" (`Сверхзадача`) Alignment Gate:** Before writing the full scene map, present 2–3 candidate **Controlling Ideas** via `ask_question` (*"What single emotional takeaway should this film build toward?"*). Once chosen, keep **1 Primary Narrative Spine + at most 1–2 supporting flashbacks**; bank any tangential memories into `my_digital_brain.md` for future rides so the film never feels over-stuffed.
   - **Character Identification Plan ("Who's Who in the Frame"):** List every named person appearing on camera and specify their **First-Appearance Character Callout Badge** (`name`, `role/relationship`, `timestamp_s`, and `position`) so outside viewers immediately know who is who.
   - Polish `<path_to_folder>/Storyboard.md` AND copy it to `04_Project_Catalog/YEAR/<project_name>/Storyboard.md` with **5 structured sections**:
     - **Section 1: Story Overview & Narrative Arc** (Imperial + Metric stats).
     - **Section 2: Multi-Phase Music Plan:** **Article I Music Non-Reuse Law is Absolute!** The agent MUST strictly select candidate tracks from `project_manifest.json`'s `recommended_music_candidates` (which programmatically calls `get_previously_used_tracks()` from `fetch_creatormix_catalog.py` to exclude every track ever used across `04_Project_Catalog/`). NEVER freely browse or guess filenames from `03_Audio_Library/01_Curated_BGM/` without running the non-reuse verification! If fewer than 3 local candidates exist, run `fetch_creatormix_catalog.py` to pull fresh virgin tracks directly from CreatorMix.
     - **Section 3: Scene-by-Scene Visual & Audio Map** (`Scene 00` -> `Scene N`, exact timecodes, `V1` clips/stills, `V2` GPX corner maps/HUD, `A1` live dialog boost, `A4` voiceover cues).
     - **Section 1: Video Overview, Title Ideas & Multi-Phase Music Selection:**
       - **Title Options:** Always put the hook-first title under `* **Primary (Hook-First / YouTube):**` (no date prefix so mobile titles don't truncate), followed by `* **Alt 1 (Route & Highlights):**`, and `* **Archival (Catalog Index):** YYYY-MM-DD · ...`.
     - **Section 2: The Narrative Story** (chronological scene-by-scene breakdown).
     - **Section 3: Archival Memory & Brain Links** (cross-era links to past years or key people from `my_digital_brain.md`).
     - **Section 4: Multi-Language Voice-Over & Subtitle Scripts (`EN`, `UA`, `RU`, etc.)** (always using ISO code `ua` for Ukrainian locally).
       - **Universal Unit Law:** Spoken voiceover and subtitle tracks in **English (`EN`)** strictly use **Imperial units** (`miles`, `feet`, `mph`). **ANY and ALL non-English languages** (`UA`, `RU`, `ES`, `DE`, `FR`, `IT`, etc.) MUST strictly use **Metric units** (`kilometers`, `meters`, `km/h`, `°C`). Virtually every country in Europe and outside the US operates on metric; never use miles or feet in non-English voiceovers or subtitles!
     - **Section 5: Production & YouTube Publishing Spec (Tuning Knobs)** — YAML block capturing:
       - `units`: `imperial_for_en_metric_for_all_others` (`mi/ft/mph` for EN; `km/m/kmh` for all non-English)
       - `burned_in_titles`: `false` (default, so 4K video stays clean and never collides with YouTube CC subtitles)
       - `gpx_corner_map` (`top_right`, `26%` width) & `gpx_telemetry_hud` (`auto` — shown on moving scenes when 3s speed > 2 mph; suppressed on stills & stationary scenes <= 2 mph)
       - `low_res_broll_mode`: `pip_card` (`65%` centered card over blurred `16:9` backdrop for `< 720p` clips)
       - `audio_mix`: `voiceover_persona: "$GEMINI_VOICE_ID"`, `live_dialog_boost: auto`, `bgm_riding_midrange_rms_db: -16.0` (`180 Hz` midrange RMS with `+1.5 dB` mellow offset + `1.8 kHz` presence EQ), `bgm_duck_db: 6.5` (`-21.5..-24.5 dB` under speech), `pip_broll_music_db: -6.5`
       - `agvs_bookends`: Signature AGVS starting postcard and finishing credits bookends (`enabled: true`, `intro_duration_s: 3.5`, `outro_duration_s: 4.5`, `studio_motto`, `location_badge`, `cast_credits`, `steed_credit`, `fuel_sponsors`).
       - `default_privacy`: `"unlisted"` (default for all uploads to allow immediate comments, previews, and language switchers without public feed spam)
       - `youtube_publishing.publishing_mode`:
         - `option_a` (Recommended Default): 1 clean 4K master (`unlisted`) with matching voiceover + localized `EN`/`UA`/`RU` titles, descriptions & `.srt` subtitles (`captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`). Concentrates views on 1 video while serving multi-lingual audiences via YouTube CC.
         - `en_only`: 1 English 4K video (`unlisted`) with `captions.en.srt`.
         - `option_b`: Special Occasions Only — 3 separate 4K video uploads (EN Master `unlisted` + UA/RU unlisted voiced editions). Always requires explicit confirmation before upload!
       - `thumbnail`: `style: composite_ai` (`headline_text`, `hero_image`, `prop_cutout`) modeled after YouTube Studio's "Ask Suggestions" composite layout.
       - `ai_creative_artifacts`: Propose 2–3 **100% Native Studio AI Creative Candidates** (zero BleeqUP app dependency!) generated via `.agents/skills/storyboard/scripts/generate_ai_creative_assets.py` (`agvs_core.ai_creative`: `gemini-3-pro-image` + `gemini-omni-1.2-flash`):
         - **`paint_morph` (Artistic Painting $\leftrightarrow$ Reality Morph):** Synthesizes a `16:9` impasto oil painting, watercolor, or anime twin from any raw photo/video frame and melts it seamlessly into the real shot (ideal for cold opens or poetic endings).
         - **`fpv_drone` (Native 3rd-Person Multi-POV Tracking — Per-Ride Photo Reference + 4 POV Templates):** Uses the photo of Alexander with his bike taken on that day's ride (`--rider-ref <IMG_*.jpg>`, never hardcoded since kit and bike change ride to ride!) + a raw POV road clip (`--source <VIDEO_*.MP4>`), and lets Alexander choose from **4 POV Templates** (`crane_above_to_behind`, `side_tracking`, `low_rear_chase`, `front_lead`) or a **Custom Prompt** (`--viewpoint custom --prompt "..."`).
         - **`living_memory` (Living Archival Photograph):** Animates historical Lightroom photos (`P110*.jpg`, 1977+ B&W film scans) into warm 5.0s living memories (e.g., turning and clinking wine glasses).
3. **Step 3 (Automatic Memory Harvesting into `my_digital_brain.md`):**
   - Append any new people, companions, recurring gear/wardrobe, or cross-year links into `./my_digital_brain.md`.
4. **Step 4 (Interactive Co-Design Prompt & AI Creative Artifact Selection):**
   - Present the updated `Storyboard.md` (highlighting the Scene Map, characters, proposed Thumbnail, and candidate **AI Creative Artifacts**) and use `ask_question` to let Alexander select which AI-generated artifacts (if any) to synthesize and weave into the timeline before running `/build-timeline`.
