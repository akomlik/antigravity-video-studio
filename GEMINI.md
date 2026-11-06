# Antigravity Video Studio — Workspace Instructions (`GEMINI.md`)

Welcome to **Alexander Komlik's (`@akomlik`) Universal AI Video Studio**. Whenever a conversation starts in this workspace, follow these architectural rules and file paths automatically.

> **💡 2-PASS STORYBOARD & MODEL SPLIT WORKFLOW (GOOGLE AI PRO PLAN):**
> - **Pass 1: Ingest & Structural Scaffold (Gemini 3.8 Flash):** Run `/ingest-media` or the initial `/storyboard` pass on **Flash**. Flash handles all shell commands, HEIC $\rightarrow$ JPG conversion, proxy extraction (`.proxies/`), GPX telemetry calculation, and audio dB level analysis at 0% Argon cost.
> - **Pass 2: Creative Polish & Memory Weaving (Gemini 4 Argon):** Once proxies and the draft `Storyboard.md` are on disk, switch the model dropdown to **Gemini 4 Argon** (Thinking: Low or Medium) for the creative pass. Argon acts purely as the Creative Director—weaving emotional flashbacks from `my_digital_brain.md`, sharpening the narrative arc, scripting trilingual voiceover, and designing the composite thumbnail without wasting quota on shell execution!
> - **Assembly & Publishing (Gemini 3.8 Flash):** Switch back to **Flash** for `/build-timeline` and `/publish-youtube`.
> - **Russian Edition (`_RU.mp4`) & Flickr Publishing Standard:** Because YouTube is heavily throttled/blocked in Russia and occupied Crimea, family (Nina's brother, Alexander's sister in Sevastopol) and Institute classmates on WhatsApp rely on Alexander's **Flickr feed (`apkom`)** and WhatsApp channels. Always losslessly remux `<project>_RU.mp4` (`0.2s` `ffmpeg -c:v copy`) by default alongside the primary master, and generate copy-ready Flickr metadata (Date-prefixed Russian title, description, tags, and album).

---

## 1. Core Studio Pillars (Always Read First Before Cutting)

1. **[`editing_constitution.md`](./editing_constitution.md)** — Universal multi-genre editing rules, Stage 0 `Storyboard.md` workflow, EBU R128 audio mixing (`A1` camera audio, `A2` music from `03_Audio_Library/01_Curated_BGM/`, `A3` peak-aligned SFX from `03_Audio_Library/02_SFX/`), Ken Burns rules, and the 100% chat-driven zero-IDE assembly flow.
2. **[`my_digital_brain.md`](./my_digital_brain.md)** — Lifetime biography, key people (**Nina**, Mallorca cycling crew), 1977+ B&W film photography era, 1980–1984 university classmates era, California SJBC cycling, and harvested Mallorca trip lore.
3. **[`03_Audio_Library/02_SFX/catalog.json`](./03_Audio_Library/02_SFX/catalog.json)** & **[`README.md`](./03_Audio_Library/02_SFX/README.md)** — 209 cinematic sound effects across 19 English folders (`01_Whooshes_Soft` through `19_Ambient_Pads`) with exact `duration_ms` and `peak_ms` for frame-accurate peak alignment on track `A3`.

---

## 2. Split Storage Architecture

| Tier | Path | Contents |
| :--- | :--- | :--- |
| **Tier 1: Studio & Catalog Root (Google Drive)** | `./` | `editing_constitution.md`, `my_digital_brain.md`, `00_Archive_Indexes/`, `03_Audio_Library/`, `04_Project_Catalog/YEAR/<project>/` (`Storyboard.md`, `project_manifest.json`, `.fcproj`), and `.agents/skills/`. |
| **Tier 2: Hot Local Media & Renders (`~/Movies/`)** | `~/Movies/2026/<project_folder>/` | Raw `.MOV`/`.MP4`/`.HEIC`/`.jpg`/`.gpx` media, `.proxies/` 640px video thumbnails, `~/Movies/Archival_Pulls/` (YouTube slices & Lightroom 4K exports), `~/Movies/Cache_And_Previews/` (FilmCraft working cache), and `~/Movies/Exports/2026/` (final `.mp4` renders). |
| **Tier 3: Cold External Archive (`Crucial-4T`)** | `/Volumes/Crucial-4T/Movies/YEAR/` & `/Volumes/Crucial-4T/Pictures/` | Historical video projects and 32,815+ Lightroom archival photos (relinked in 10ms via `/relink-archive`). |
| **Curated Free Music Pool (`03_Audio_Library/01_Curated_BGM/`)** | `03_Audio_Library/01_Curated_BGM/` | Zero-cost tracks (< 3:00 duration) curated from **YouTube Audio Library** and **Creator Mix (`creatormix.com`)**, named `[BPM]_[Mood]_[TrackName]_[Artist].mp3` across `01_Rolling_Cadence`, `02_Scenic_Wonder`, `03_Punchy_Climbs`, `04_Warm_Social_And_Retro`, and `05_Short_Transitions`. |

---

## 3. Available Slash-Command Skills (`.agents/skills/`)

- **`/storyboard <folder>`** — **Stage 0 (Co-Design & Harvest):** Runs `ingest_and_sync_media.py`, converts `.HEIC` $\rightarrow$ `.jpg`, extracts `.proxies/` video thumbnails, inspects clips/GPX/YouTube links, co-creates `Storyboard.md`, and automatically harvests new people, places, and memories into `my_digital_brain.md`.
- **`/build-timeline <folder>`** — **Stage 1 (Interactive Assembly & Export):** Presents an in-chat clickable alignment card (`ask_question` for Primary Voice-Over Language, Music Track #1 & #2 with 10s audio preview, and Publishing Mode), updates `Storyboard.md` automatically, builds the 4-track timeline in FilmCraft MCP, saves `.fcproj` to `04_Project_Catalog/YEAR/`, exports `.mp4` to `~/Movies/Exports/YEAR/`, generates metadata & `facebook_promo.md`, and pauses for user review before YouTube upload.
- **`/publish-youtube <folder>`** — **Stage 2 (Headless Release):** Uploads the 4K `.mp4` (default: `unlisted`), sets Imperial-first metadata, clean chapters, localized titles/subtitles (`EN`, `UA`, `RU`), posts language switcher comment, and prints copy-ready Facebook promo directly in chat.
- **`/publish-flickr <folder>`** — **Family & Classmates Release (Censorship Bypass):** Uploads the 4K Russian-voiced video (`_RU.mp4`) or English master to Flickr via API, sets date-prefixed title with miles/km, description, and GPS coordinates, adds to Flickr album, and outputs copy-ready WhatsApp sharing snippet.
- **`/swap-music`** — Instantly swaps the background music track on audio lane `A2` from `03_Audio_Library/01_Curated_BGM/` without rebuilding the whole timeline.
- **`/find-music`** — Connects to Alexander's open **YouTube Audio Library** and **`creatormix.com`** browser tabs (or checks `03_Audio_Library/01_Curated_BGM/`), filters for `< 3:00` duration + matching mood/BPM, and runs `save_music_track.py` to auto-rename downloaded tracks to `[BPM]_[Mood]_[TrackName]_[Artist].mp3`.
- **`/interview-brain`** — Interactive Q&A session (run on Flash) to enrich `my_digital_brain.md` across life eras.
- **`/ingest-media <folder>`** — Runs `ingest_and_sync_media.py` to generate `.proxies/` and `project_manifest.json`.
- **`/relink-archive`** — Runs `relink_project_media.py` when moving folders between `~/Movies/` and `/Volumes/Crucial-4T/Movies/`.

---

## 4. FilmCraft Live Bridge Launch Command

Before calling `filmcraft` MCP tools, ensure FilmCraft is running with its working directory set to `~/Movies/Cache_And_Previews` (so render caches never pollute Google Drive):

```bash
mkdir -p ~/Movies/Cache_And_Previews && cd ~/Movies/Cache_And_Previews
open -a FilmCraft --args --control 9876
```
