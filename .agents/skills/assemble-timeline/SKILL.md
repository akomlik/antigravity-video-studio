---
name: assemble-timeline
description: Executes an approved Cut Table (after the user replies OK) in either FilmCraft MCP or DaVinci Resolve Studio MCP, saves the .fcproj/.drp project into Google Drive 04_Project_Catalog/YEAR/, and exports the MP4 into ~/Movies/Exports/YEAR/.
---

# Atomic MCP Timeline Assembly & Verification (`/assemble-timeline`)

## Option A: FilmCraft MCP Execution (`filmcraft` MCP server — Requires FilmCraft `v0.17.0+`)

### 1. Environment & Bridge Verification
1. Run `python3 ./.agents/skills/assemble-timeline/scripts/check_filmcraft_env.py` first to verify FilmCraft $\ge$ `v0.17.0`, auto-sync `filmcraft-cli` with `FilmCraft.app`, and surface any newly added MCP commands in `00_Archive_Indexes/filmcraft_capabilities.json`.
2. Ensure FilmCraft is running in bridge mode with caches routed to `~/Movies/Cache_And_Previews`:
   ```bash
   mkdir -p ~/Movies/Cache_And_Previews && cd ~/Movies/Cache_And_Previews
   open -a FilmCraft --args --control 9876
   ```

### 2. Live Visual Assembly Mode (Default & Recommended)
Watching the timeline assemble live in the open FilmCraft GUI adds less than 1.5 seconds of total socket execution time (calls take $< 20\text{ ms}$ over the local bridge) and provides instant visual verification:
1. **Open Blank Canvas at Second 0:**
   Immediately creates and opens the clean `.fcproj` shell in FilmCraft via `command_run` (`{"id": "file.open", "params": {"path": "<fcproj_path>"}}`) or `sequence.new`. The user sees their empty 4K sequence appear at Second 0.
2. **Streamed Media Ingest:**
   Call `media_import` with the absolute file paths of all selected video cuts, photos, archival pulls, and chosen `03_Audio_Library/01_Curated_BGM/` tracks (`A2`).
3. **Live Scene-by-Scene Stream:**
   As each scene from the approved `Cut Table` is processed, stream `command_batch` calls live over the 9876 bridge:
   - `playhead.set`: Moves playhead to scene start timecode.
   - `source.overwrite` / `timeline.insertClip`: Places visual clip onto `V1` (or `V2` for overlays/PIP) and synchronous audio on `A1`.
   - `motion.apply`: Injects Ken Burns `EaseIn`/`EaseOut` scale & pan keyframes onto stills (100% $\rightarrow$ 108%, or 134% $\rightarrow$ 142% on 4:3 photos to prevent pillarbox cropping).
   - `audio.append`: Drops `A2` background music with 1.5s fade-in and swells.
   - `voiceover.insert`: Drops `A4` voice-over segments onto the live timeline as each audio cue finishes synthesizing.
4. **Broadcast Polish:**
   - **Same-Language Live Dialogue Honor Law:** Never place `A4` Voice-Over in language $L$ over `A1` live camera dialogue spoken in that same language $L$ (`EN` VO honors live `EN` dialogue; `RU` VO honors live `RU` dialogue; `UA` VO honors live `UA` dialogue). When `A4` VO translates a clip containing foreign-language camera dialogue (`edition_lang != clip_dialog_lang`), duck `A1` by `-12 dB` during active VO cues.
   - **Natural `1.00x` Speech Speed, `1:1 V1 == A1` Lip-Sync & Opening Music Intro Law:** Never apply `atempo > 1.0` or internal pause-stripping (`stop_periods=-1`) to live camera speech (`A1`) or synthesized Voice-Over (`A4`). Always size speaking visual cuts (`V1`) to fit the complete `1.00x` spoken sentence (`src_in`, `dur`) so `V1` and `A1` remain locked 1:1 in frame-and-sample sync (sliced via `atrim=start=...:end=...,asetpts=PTS-STARTPTS` with `dynaudnorm=f=150:g=7:p=0.90` applied once post-`amix`) and never overflow into unrelated scenes. Always begin every timeline and rendered `.mp4` with a `1.5s–2.0s` music intro before the first voice-over cue starts.
   - **RMS-Calibrated Music Ducking (`-28.5 dB` Mean Under Speech):** Measure each `A2` music track's `mean_volume` via `ffmpeg volumedetect` (`compute_bgm_ducked_gain_db`) and set `gain_db = -28.5 - raw_mean_db` so ducked BGM sits at **`-28.5 dB` mean** — a full `12.5 dB` quieter than normalized `-16.0 dB` mean Voice-Over and Live Dialogue, even on hot-mastered upbeat tracks.
   - Tag `A4` voiceover and `A1` dialog as `Dialogue` (`clarity.eqPreset: "Balanced Voice"`), and execute `essentialSound.generateDucking` (`reduceDb: -6.0`, `fadeS: 0.45`) on `A2` Music.
   - Apply native 1.5s to 2.0s `dip_to_black` transition on the closing visual clip.
   - **Mandatory Synchronized Outro Audio Fade:** The master audio output (`[fullout]`) and music on `A2` MUST execute a synchronized `2.0s–2.5s` half-sine fade-out (`afade=t=out:st=<TOTAL_DUR - FADE_DUR>:d=<FADE_DUR>:curve=hsin`) so all audio (music, camera noise, SFX tails) reaches complete silence (`-infinity dB`) at or before the final frame. In `.fcproj`, track `A2` MUST carry an `EndAtCut` audio fade transition (`from: Some(clip.id), to: None, align: "EndAtCut"`). Sound must NEVER cut off abruptly.
   - Write multi-language subtitle tracks to `caption_tracks` (C1) with `enabled: false` (`burnCaptions: false` default).

### 3. Headless Batch Fallback (`assemble_engine.py`)
If FilmCraft GUI is not running or bridge mode is offline, automatically assemble the `.fcproj` directly via `assemble_engine.py` in $< 1$ second and render 4K master MP4 via `filmcraft-cli`.
- **Repository Hygiene Rule:** Keep `.agents/skills/assemble-timeline/scripts/` strictly reserved for universal, project-agnostic engines (`assemble_engine.py`, `gpx_widgets.py`, `generate_voiceover.py`, `check_filmcraft_env.py`). If a custom or project-specific assembly script is ever created for a particular project, always save it inside that project's git-ignored catalog folder (`04_Project_Catalog/YEAR/<project_name>/`) and never inside `.agents/skills/`.

### 4. Visual Verification & Master Render
1. Call `render_frame` at three timestamps (Act 1 intro, midpoint, epilogue) to confirm framing.
2. Render master 4K MP4 to `~/Movies/Exports/YEAR/<project_name>.mp4`.
3. If multilingual editions requested (`option_b`), remux with `_UA.mp4` and `_RU.mp4` localized stems.

## Option B: DaVinci Resolve Studio MCP Execution (`davinci-resolve`)
1. Create a new timeline (`1920x1080` or `3840x2160`, `29.97` fps, `DaVinci YRGB Color Managed Rec.709`).
2. Import the selected media into a `Selects` bin via `media_pool`, append clips to `V1`/`V2`/`A1` and music to `A2` via `timeline_edit`, apply `Cross Dissolve` transitions via `transitions`, set Ken Burns zoom keyframes via `keyframes`, and set audio ducking via `audio` / `inspector`.
3. Call `export_still` at three timestamps to visually verify the cut, export a `.drp`/`.drt` backup to `04_Project_Catalog/YEAR/<project_name>/`, and queue the final `.mp4` render to `~/Movies/Exports/YEAR/` via `render`.
