# Antigravity Video Studio — Workspace Instructions (`GEMINI.md`)

Welcome to **Alexander Komlik's (`@akomlik`) Universal AI Video Studio**. Whenever a conversation starts in this workspace, follow these architectural rules and file paths automatically.

> **⚠️ QUOTA PROTECTION RULE (GOOGLE AI PRO PLAN):**
> - If the user is currently on **Gemini 4 Argon** and asks to run multi-step prep tasks (`/ingest-media`, `/storyboard` visual inspection, `/find-music` browser automation, `/interview-brain`, `/swap-music`, or `/relink-archive`), **remind them in 1 line to switch the model dropdown to `Gemini 3.8 Flash`** (or delegate subagent work with `Model: "flash"`) so they don't burn their 5-hour Argon quota!
> - Reserve **Gemini 4 Argon (Medium)** strictly for the single-turn creative **Cut Table generation** (`/build-cut-table`), or run the entire pipeline on **Gemini 3.8 Flash** when Argon is on cooldown.

---

## 1. Core Studio Pillars (Always Read First Before Cutting)

1. **[`editing_constitution.md`](file:///Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/editing_constitution.md)** — Universal multi-genre editing rules, Stage 0 `Storyboard.md` workflow, EBU R128 audio mixing (`A1` camera audio, `A2` music from `~/Music/Cycling_BGM/`, `A3` peak-aligned SFX from `03_Audio_Library/02_SFX/`), Ken Burns rules, and the Cut Table schema.
2. **[`my_digital_brain.md`](file:///Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/my_digital_brain.md)** — Lifetime biography, key people (**Nina**, Mallorca cycling crew), 1977+ B&W film photography era, 1980–1984 university classmates era, California SJBC cycling, and harvested Mallorca trip lore.
3. **[`03_Audio_Library/02_SFX/catalog.json`](file:///Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/03_Audio_Library/02_SFX/catalog.json)** & **[`README.md`](file:///Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/03_Audio_Library/02_SFX/README.md)** — 209 cinematic sound effects across 19 English folders (`01_Whooshes_Soft` through `19_Ambient_Pads`) with exact `duration_ms` and `peak_ms` for frame-accurate peak alignment on track `A3`.

---

## 2. Split Storage Architecture

| Tier | Path | Contents |
| :--- | :--- | :--- |
| **Tier 1: Studio & Catalog Root (Google Drive)** | `~/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/` | `editing_constitution.md`, `my_digital_brain.md`, `00_Archive_Indexes/`, `03_Audio_Library/`, `04_Project_Catalog/YEAR/<project>/` (`Storyboard.md`, `project_manifest.json`, `cut_table.md`, `.fcproj`), and `.agents/skills/`. |
| **Tier 2: Hot Local Media & Renders (`~/Movies/`)** | `~/Movies/2026/<project_folder>/` | Raw `.MOV`/`.MP4`/`.HEIC`/`.jpg`/`.gpx` media, `.proxies/` 640px video thumbnails, `~/Movies/Archival_Pulls/` (YouTube slices & Lightroom 4K exports), `~/Movies/Cache_And_Previews/` (FilmCraft working cache), and `~/Movies/Exports/2026/` (final `.mp4` renders). |
| **Tier 3: Cold External Archive (`Crucial-4T`)** | `/Volumes/Crucial-4T/Movies/YEAR/` & `/Volumes/Crucial-4T/Pictures/` | Historical video projects and 32,815+ Lightroom archival photos (relinked in 10ms via `/relink-archive`). |
| **Curated Free Music Pool (`~/Music/Cycling_BGM/`)** | `~/Music/Cycling_BGM/` $\leftrightarrow$ `03_Audio_Library/01_Curated_BGM/` | Zero-cost tracks (< 3:00 duration) curated from **YouTube Audio Library** and **Creator Mix (`creatormix.com`)**, named `[BPM]_[Mood]_[TrackName]_[Artist].mp3` across `01_Rolling_Cadence`, `02_Scenic_Wonder`, `03_Punchy_Climbs`, `04_Warm_Social_And_Retro`, and `05_Short_Transitions`. |

---

## 3. Available Slash-Command Skills (`.agents/skills/`)

- **`/storyboard <folder>`** — **Stage 0:** Runs `ingest_and_sync_media.py`, converts `.HEIC` $\rightarrow$ `.jpg`, extracts `.proxies/` video thumbnails, inspects clips/GPX/YouTube links, co-creates `Storyboard.md` (migrating `Context.md` if present), and automatically harvests new people, places, and memories into `my_digital_brain.md`.
- **`/find-music`** — Connects to Alexander's open **YouTube Audio Library** and **`creatormix.com`** browser tabs (or checks `~/Music/Cycling_BGM/`), filters for `< 3:00` duration + matching mood/BPM, and runs `save_music_track.py` to auto-rename downloaded tracks to `[BPM]_[Mood]_[TrackName]_[Artist].mp3`.
- **`/magic-movie <folder>`** — **Gear 1 (Express Auto-Pilot):** Reads `Storyboard.md`, fetches any YouTube throwback slices (`fetch_yt_broll_clip.py`), picks the #1 music track on `A2` + contextual SFX from `02_SFX/catalog.json` on `A3`, builds the timeline in FilmCraft MCP without pausing, saves `.fcproj` to `04_Project_Catalog/YEAR/`, and exports `.mp4` to `~/Movies/Exports/YEAR/`.
- **`/build-cut-table <folder>`** — **Gear 2 (Supervised Protocol):** Generates `04_Project_Catalog/YEAR/<project>/cut_table.md` with exact in/out points, `V2` captions, `A1`/`A2` dB levels, and `A3` SFX cues (`peak_ms` aligned), and pauses for human `"OK"`.
- **`/assemble-timeline`** — Executes an approved `cut_table.md` in FilmCraft MCP (`media_import` $\rightarrow$ `doc_inspect` $\rightarrow$ single atomic `command_batch` with `playhead.set` before every `source.overwrite` $\rightarrow$ 3-frame `render_frame` check).
- **`/swap-music`** — Instantly swaps the background music track on audio lane `A2` from `~/Music/Cycling_BGM/`.
- **`/interview-brain`** — Interactive Q&A session (run on Flash) to enrich `my_digital_brain.md` across life eras.
- **`/ingest-media <folder>`** — Runs `ingest_and_sync_media.py` to generate `.proxies/` and `project_manifest.json`.
- **`/relink-archive`** — Runs `relink_project_media.py` when moving folders between `~/Movies/` and `/Volumes/Crucial-4T/Movies/`.
- **`/publish-youtube`** — Generates `youtube_metadata.md`, `youtube_metadata.json` (3 Title options, `00:00` Chapter-indexed Description, Ride/Event stats, Music Credits, Tags), and a 1080p `thumbnail.jpg`, then uploads the `.mp4` and sets all metadata on the `@akomlik` YouTube channel via Chrome DevTools (`studio.youtube.com`) or YouTube Data API v3, and appends the new video to `00_Archive_Indexes/youtube_motion_index.jsonl`.

---

## 4. FilmCraft Live Bridge Launch Command

Before calling `filmcraft` MCP tools, ensure FilmCraft is running with its working directory set to `~/Movies/Cache_And_Previews` (so render caches never pollute Google Drive):

```bash
mkdir -p ~/Movies/Cache_And_Previews && cd ~/Movies/Cache_And_Previews
open -a FilmCraft --args --control 9876
```
