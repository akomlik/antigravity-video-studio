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
2. **Step 2 (Fetch Linked YouTube Flashbacks & Render GPX Overlays):**
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
     - `A1 (Native / Live Dialog)`: Boosted live dialog (`0 dB`, `-22 dB` mean) during speech; muted or `-6 dB` during pure riding.
     - `A2 (BGM)`: Multi-phase music at `-7.5 dB` under VO, swelling `+3.5 dB` (`-4.0 dB`, `-22.9 dB` mean) during riding-only intervals, muted during live camera dialog, with mandatory `2.0s–2.5s` half-sine outro fade (`curve=hsin`) matching the visual dip-to-black.
     - `A3 (SFX / B-Roll Audio)`: PiP B-roll music trimmed to `-6.5 dB` (`-30.3 dB` mean) with `0.8s` fades; zero SFX overlapping live speech.
     - `A4 (Voice-Over)`: Warm replicated voice-over (`+2.0 dB`, `-16 LUFS`).
     - `Master Outro Audio Fade`: All master audio outputs (`[fullout]`) MUST apply `afade=t=out:st=<TOTAL_DUR - FADE_DUR>:d=<FADE_DUR>:curve=hsin` reaching complete silence (`-infinity dB`) as the video dips to black (never cutting abruptly).
     - `C1 (Captions)`: Stored in `.fcproj` for `.srt` extraction, with `enabled: False` and `--settings '{"burnCaptions": false}'` so the exported 4K video has **zero burned-in bottom titles**.
   - Export `~/Movies/Exports/YEAR/<project_name>.mp4` (`3840x2160`, `H.264`, `AAC 192k`) and refresh the live FilmCraft GUI via `file.open`.
   - If `publishing_mode` is `option_b`, build the localized `UA` and `RU` master audio stems (`full_audio_ua.m4a`, `full_audio_ru.m4a`) and losslessly remux them with the 4K video stream (`ffmpeg -c:v copy`, `0.2s` each) into `<project_name>_UA.mp4` and `<project_name>_RU.mp4`.
5. **Step 5 (Generate Metadata, Composite Thumbnail & Publish to YouTube):**
   - Run `generate_youtube_metadata.py` and `upload_youtube_api.py` (inheriting `GEMINI_API_KEY` / OAuth credentials from the shell environment or cached `~/.config/antigravity_youtube/token.json`) according to `Section 5` (`en_only`, `option_a`, or `option_b` via `--option-b`), applying `thumbnail.jpg` (`thumbnail_ua.jpg`, `thumbnail_ru.jpg`) to all uploaded editions.
