---
name: magic-movie
description: One-command iMovie "Magic Movie" replacement (Studio v2). Reads Storyboard.md (including Section 5 Tuning Knobs), downloads linked YouTube flashbacks, renders GPX corner maps & telemetry HUD, generates replicated voice-over (EN/UA/RU), builds the 4-track broadcast audio mix with zero burned-in titles, exports 4K MP4(s), and optionally publishes to YouTube (`en_only`, `option_a`, or `option_b`).
---

# Gear 1: Express "Magic Movie" Auto-Pilot Mode (`/magic-movie`)

## Purpose & Zero-Friction Flow
Use this skill when Alexander wants a complete, broadcast-balanced 4K video built from `Storyboard.md` (and published to YouTube if specified in Section 5) with **zero back-and-forth**.

## Supported Arguments / Overrides
You can invoke `/magic-movie` on a folder and optionally pass inline overrides (which also default to Section 5 of `Storyboard.md`):
- `--publish en_only | option_a | option_b | none` (default: reads `youtube_publishing.publishing_mode` from `Storyboard.md`)
- `--burn-titles true | false` (default: `false` — clean 4K frame, subtitles served via `.srt`)
- `--thumb-text "<HEADLINE>"` (default: reads `thumbnail.headline_text` from `Storyboard.md`)

## Execution Sequence
1. **Step 1 (Enforce FilmCraft >= v0.17.0 & Ensure Ingestion + `Storyboard.md`):**
   - Run `python3 ./.agents/skills/assemble-timeline/scripts/check_filmcraft_env.py` to enforce `MIN_FILMCRAFT_VERSION = "0.17.0"`, auto-sync `filmcraft-cli` if `FilmCraft.app` was updated in ArtCraft Launcher, check for newer upstream releases on `storytold/filmcraft`, and diff any newly added MCP commands against `00_Archive_Indexes/filmcraft_capabilities.json`.
   - If `project_manifest.json` or `Storyboard.md` does not yet exist, run `ingest_and_sync_media.py` to convert `.HEIC` -> `.jpg`, generate `.proxies/`, and draft `Storyboard.md`.
2. **Step 1.5 (Pre-Assembly Creative Checkpoint — 1-Turn Quick Align):**
   - Before launching VO synthesis, GPX rendering, and timeline assembly, present a concise 3-point creative brief to Alexander:
     1. **Primary Voice-Over Language:** Default to the language spoken in raw video clips (e.g. `Russian` or `Ukrainian` for candid conversations with Nina/friends, `English` for English-spoken rides). Note if overridden for a specific target audience (e.g. `English` for US cycling channel / SJBC teammates).
     2. **Selected Music Track:** State the curated #1 track from `03_Audio_Library/01_Curated_BGM/` (Title, Genre, BPM, Mood) and list backup Track #2.
     3. **Publishing Mode:** State target mode (Default: `Option A` — 1 clean 4K master, `unlisted`, with `EN`, `UA`, `RU` `.srt` subtitles).
   - Prompt: **"Ready to assemble timeline with [Language] voiceover, Track #1: [MusicTitle], and Option A publishing? Reply 'OK' to proceed, or specify any swap (e.g. 'swap music to #2', 'use English voiceover')."**
   - Once Alexander replies "OK" or "proceed", execute Steps 2 through 4 seamlessly on auto-pilot!
3. **Step 2 (Fetch Linked YouTube Flashbacks & Render GPX Overlays):**
   - If `Storyboard.md` links an `@akomlik` YouTube URL, pull the slice via `fetch_yt_broll_clip.py`. If the clip is low-resolution (`< 720p`), render it as a `65%` centered **Picture-in-Picture (PiP) card** with a subtle white border over a soft-blurred `16:9` background (`low_res_broll_mode: pip_card`).
   - If a `.gpx` file is present, run `render_gpx_widgets.py` to generate:
     - Top-right **GPX Corner Route Map** (`map_*.png`, `26%` width, `82%` opacity, Imperial `mi`/`ft` header, cyan full track + orange progress trace + glowing current-position dot) placed on `V2`.
     - Bottom-right **Telemetry HUD** (`hud_*.png`, `mph`, `ft`, `%` grade, distance `mi`) placed on `V2` *only* on active riding scenes where GPS speed $\ge 5\text{ mph}$ (`gpx_telemetry_hud: auto`).
3. **Step 3 (Generate Warm Replicated Voice-Over & Boost Live Camera Dialog):**
   - Run `generate_voiceover.py` using Alexander's custom replicated voice persona (`voice_jntybwupjc1s` in `03_Audio_Library/03_Voice_Profile/voice_id.json`) to synthesize scene-synced `48 kHz` stereo narration (`-16 LUFS`) for the requested locales (`en`, plus `ua` and `ru` when `option_b` is selected).
   - For scenes with live BleeqUP camera conversation (`-45 dB` to `-53 dB` raw mic level), extract and normalize the dialog with a `120 Hz` high-pass filter + `+16..22 dB` boost + `dynaudnorm` (`-22 dB` mean) and remove any overlapping `A3` SFX.
4. **Step 4 (Assemble 4-Track Timeline & Export Clean 4K Master):**
   - Assemble the `.fcproj` timeline with:
     - `V1`: Video clips and Ken Burns (`EaseInOut` `1.0 -> 1.075`) still photos (including prop/repair detail photos synchronized to the dialog/VO).
     - `V2`: GPX Corner Maps & Telemetry HUD overlays.
     - `A1 (Native / Live Dialog)`: Normalized live dialog (`-16.0 dB` mean) when `edition_lang == clip_dialog_lang` (never covered by same-language VO!); ducked by `-12 dB` under cross-language VO when `edition_lang != clip_dialog_lang`.
     - `A2 (BGM)`: RMS-calibrated (`gain_db = -28.5 - raw_mean_db`) so music sits at `-28.5 dB` mean under VO/live dialogue (`12.5 dB` below speech), swelling `+5.0 dB` (`-23.5 dB` mean) only during non-speech intervals, with mandatory `2.0s–2.5s` half-sine outro fade (`curve=hsin`) matching the visual dip-to-black.
     - `A3 (SFX / B-Roll Audio)`: PiP B-roll music trimmed to `-6.5 dB` (`-30.3 dB` mean) with `0.8s` fades; zero SFX overlapping live speech.
     - `A4 (Voice-Over)`: Warm replicated voice-over normalized to `-16.0 dB` mean (`-1.0 dB` peak), automatically suppressed over same-language live dialogue sections (`filter_vo_cues_for_same_language_dialog`).
     - `Master Outro Audio Fade`: All master audio outputs (`[fullout]`) MUST apply `afade=t=out:st=<TOTAL_DUR - FADE_DUR>:d=<FADE_DUR>:curve=hsin` reaching complete silence (`-infinity dB`) as the video dips to black (never cutting abruptly).
     - `C1 (Captions)`: Stored in `.fcproj` for `.srt` extraction, with `enabled: False` and `--settings '{"burnCaptions": false}'` so the exported 4K video has **zero burned-in bottom titles**.
   - Export `~/Movies/Exports/YEAR/<project_name>.mp4` (`3840x2160`, `H.264`, `AAC 192k`) and refresh the live FilmCraft GUI via `file.open`.
   - If `publishing_mode` is `option_b`, build the localized `UA` and `RU` master audio stems (`full_audio_ua.m4a`, `full_audio_ru.m4a`) and losslessly remux them with the 4K video stream (`ffmpeg -c:v copy`, `0.2s` each) into `<project_name>_UA.mp4` and `<project_name>_RU.mp4`.
5. **Step 5 (Generate Metadata, Composite Thumbnail & Social Copy — Pause for Upload Approval):**
   - Run `generate_youtube_metadata.py` to produce:
     - `youtube_metadata.json` (Imperial stats, hook-first title, chapters, and localized descriptions)
     - `thumbnail.jpg`, `thumbnail_ua.jpg`, `thumbnail_ru.jpg`
     - `facebook_promo.md` (Copy-ready Facebook promotional packages: Option 1 Curiosity Hook, Direct Story, and Bilingual)
   - Present the release summary, hook-first title, thumbnail, and Facebook promotional copy in the chat response.
   - **MANDATORY USER CONFIRMATION (NEVER AUTO-UPLOAD):** Never call `upload_youtube_api.py` automatically without asking Alexander first! Always pause and ask:
     *"4K MP4 export complete and metadata generated. Would you like to upload to YouTube now (`--option-b` / `--privacy unlisted`)?"*
   - Only run `upload_youtube_api.py` when Alexander explicitly confirms.
