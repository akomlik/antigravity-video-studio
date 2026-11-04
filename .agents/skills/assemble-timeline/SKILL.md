---
name: assemble-timeline
description: Executes an approved Cut Table (after the user replies OK) in either FilmCraft MCP or DaVinci Resolve Studio MCP, saves the .fcproj/.drp project into Google Drive 04_Project_Catalog/YEAR/, and exports the MP4 into ~/Movies/Exports/YEAR/.
---

# Atomic MCP Timeline Assembly & Verification (`/assemble-timeline`)

## Option A: FilmCraft MCP Execution (`filmcraft` MCP server — Requires FilmCraft `v0.17.0+`)
1. Run `python3 ./.agents/skills/assemble-timeline/scripts/check_filmcraft_env.py` first to verify FilmCraft $\ge$ `v0.17.0`, auto-sync `filmcraft-cli` with `FilmCraft.app`, and surface any newly added MCP commands in `00_Archive_Indexes/filmcraft_capabilities.json`.
2. Ensure FilmCraft is running in bridge mode with caches routed to `~/Movies/Cache_And_Previews`:
   ```bash
   mkdir -p ~/Movies/Cache_And_Previews && cd ~/Movies/Cache_And_Previews
   open -a FilmCraft --args --control 9876
   ```
3. Call `media_import` with the absolute file paths of all selected clips, stills, archival pulls, and the chosen `03_Audio_Library/01_Curated_BGM/` music track (`A2`).
4. Call `doc_inspect` once to map filenames to internal FilmCraft `item_id` values.
5. Build and execute the timeline assembly via `assemble_engine.py` or MCP commands adhering strictly to the **Antigravity Studio v2 Production Standards**:
   - **Visuals & Ken Burns:** Place video clips and stills on `V1`. Still photos automatically receive Ken Burns `EaseIn`/`EaseOut` scale keyframing (100% -> 108% or 134% -> 142% on 4:3 stills).
   - **FilmCraft v0.17.0+ `Essential Sound` & 4-Track Broadcast Mix:**
     - Tag `A4` Voice-Over and `A1` speech clips as `Dialogue` (`essentialSound.setType`, `clarity.eqPreset: "Balanced Voice"`, `repair.rumble.on: true`).
     - Tag `A1` riding clips as `Ambience`, `A2` tracks as `Music`, and `A3` clips as `SFX`.
     - Enable native `essentialSound.generateDucking` (`reduceDb: -3.5`, `fadeS: 0.45`) on `A2` Music so BGM automatically ducks `-3.5 dB` under voice-over/dialogue and swells back up during pure riding!
   - **Captions & Zero Burned-In Titles Default:** Store captions in `caption_tracks` (C1) for `.srt` export, keeping `enabled: false` and `--settings '{"burnCaptions": false}'` by default unless `burned_in_titles: true` is requested.
   - **Ending:** Native `dip_to_black` (1.5s) transition on the closing visual clip.
6. Save the reopenable `.fcproj` file to `./04_Project_Catalog/YEAR/<project_name>/<project_name>.fcproj` and ALWAYS call `command_run` (`{"id": "file.open", "params": {"path": "<fcproj_path>"}}`) via the `filmcraft` MCP server so the live FilmCraft GUI immediately reflects all timeline changes.
7. **Visual Verification Loop:** Call `render_frame` at three timestamps (Act 1/Scene 00 intro, midpoint, epilogue). Inspect the returned PNGs to confirm zero cropped heads on 4:3 photos. Export the final `.mp4` to `~/Movies/Exports/YEAR/<project_name>.mp4`.

## Option B: DaVinci Resolve Studio MCP Execution (`davinci-resolve`)
1. Create a new timeline (`1920x1080` or `3840x2160`, `29.97` fps, `DaVinci YRGB Color Managed Rec.709`).
2. Import the selected media into a `Selects` bin via `media_pool`, append clips to `V1`/`V2`/`A1` and music to `A2` via `timeline_edit`, apply `Cross Dissolve` transitions via `transitions`, set Ken Burns zoom keyframes via `keyframes`, and set audio ducking via `audio` / `inspector`.
3. Call `export_still` at three timestamps to visually verify the cut, export a `.drp`/`.drt` backup to `04_Project_Catalog/YEAR/<project_name>/`, and queue the final `.mp4` render to `~/Movies/Exports/YEAR/` via `render`.
