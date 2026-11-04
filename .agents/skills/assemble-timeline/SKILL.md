---
name: assemble-timeline
description: Executes an approved Cut Table (after the user replies OK) in either FilmCraft MCP or DaVinci Resolve Studio MCP, saves the .fcproj/.drp project into Google Drive 04_Project_Catalog/YEAR/, and exports the MP4 into ~/Movies/Exports/YEAR/.
---

# Atomic MCP Timeline Assembly & Verification (`/assemble-timeline`)

## Option A: FilmCraft MCP Execution (`filmcraft` MCP server)
1. Ensure FilmCraft is running in bridge mode with caches routed to `~/Movies/Cache_And_Previews`:
   ```bash
   mkdir -p ~/Movies/Cache_And_Previews && cd ~/Movies/Cache_And_Previews
   open -a FilmCraft --args --control 9876
   ```
2. Call `media_import` with the absolute file paths of all selected clips, stills, archival pulls, and the chosen `~/Music/Cycling_BGM/` music track (`A2`).
3. Call `doc_inspect` once to map filenames to internal FilmCraft `item_id` values.
4. Build and execute the timeline assembly via `assemble_engine.py` or MCP commands adhering strictly to the **Antigravity Production Standards**:
   - **Visuals & Ken Burns:** Place video clips and stills on `V1`. Still photos automatically receive Ken Burns `EaseIn`/`EaseOut` scale keyframing (100% -> 107.5% or 107.5% -> 100%).
   - **Audio Balance & Ducking:** Native camera audio on `A1` (`-6 dB` normal riding, boosted `+4` to `+6 dB` during speech/dialog, `-24 dB` wind gate at $\ge 40\text{ km/h}$). Background music on `A2` (Two-phase or multi-phase, `-16 dB` baseline, ducked to `-20 dB` or silence during speech, `1.5s` intro fade-in, `2.0s–2.5s` outro fade-out). Frame-accurate punchline SFX on `A3` (`-8 dB`).
   - **Captions:** Native `caption_tracks` (C1) in Inter font with semi-transparent dark rounded background pills (`background_color: [0, 0, 0, 195]`, `margin: 0.08`), all emojis sanitized for clean typography.
   - **Ending:** Native `dip_to_black` (1.5s) transition on the closing visual clip.
   - **Burn-In Export:** Always export via `filmcraft-cli` with `--settings '{"burnCaptions": true}'` to `~/Movies/Exports/YEAR/<project_name>.mp4`.
5. Save the reopenable `.fcproj` file to `~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/04_Project_Catalog/YEAR/<project_name>/<project_name>.fcproj` and ALWAYS call `command_run` (`{"id": "file.open", "params": {"path": "<fcproj_path>"}}`) via the `filmcraft` MCP server so the live FilmCraft GUI immediately reflects all timeline changes.
6. **Visual Verification Loop:** Call `render_frame` at three timestamps (Act 1/Scene 00 intro, midpoint, epilogue). Inspect the returned PNGs to confirm zero cropped heads on 4:3 photos and clean title legibility. Export the final `.mp4` to `~/Movies/Exports/YEAR/<project_name>.mp4`.

## Option B: DaVinci Resolve Studio MCP Execution (`davinci-resolve`)
1. Create a new timeline (`1920x1080` or `3840x2160`, `29.97` fps, `DaVinci YRGB Color Managed Rec.709`).
2. Import the selected media into a `Selects` bin via `media_pool`, append clips to `V1`/`V2`/`A1` and music to `A2` via `timeline_edit`, apply `Cross Dissolve` transitions via `transitions`, set Ken Burns zoom keyframes via `keyframes`, and set audio ducking via `audio` / `inspector`.
3. Call `export_still` at three timestamps to visually verify the cut, export a `.drp`/`.drt` backup to `04_Project_Catalog/YEAR/<project_name>/`, and queue the final `.mp4` render to `~/Movies/Exports/YEAR/` via `render`.
