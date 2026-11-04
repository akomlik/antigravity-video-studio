---
name: find-music
description: Curates, filters, previews, and auto-saves matching background music (< 3:00 duration) from your two open browser tabs (YouTube Audio Library and creatormix.com) or local 03_Audio_Library/01_Curated_BGM/ pool for a specific project or clip, renaming downloaded tracks to [BPM]_[Mood]_[TrackName]_[Artist].mp3 for future reuse.
---

# Live Browser & Local Pool Music Matcher (`/find-music`)

## Purpose
Implements the **"Music for Video Workflow"** and the **Anti-Monotony & Mandatory Music Non-Reuse Law**:
1. **Zero Music Reuse Across Projects:** Every video must have a unique soundscape. Tracks used in past projects (`04_Project_Catalog/*/Storyboard.md` and `.fcproj`) are automatically excluded.
2. **Online Search Mandatory Until Local Pool $> 100$ Titles:** Because small local pools lead to repetitive soundtrack choices, `/find-music` and `/storyboard` query fresh royalty-free tracks from the **CreatorMix Direct Online Catalog** (`fetch_creatormix_catalog.py`) and **YouTube Studio Audio Library** before reusing any existing local track.
3. **Frictionless Direct CDN Fetching:** Instead of requiring manual browser navigation for every song, `fetch_creatormix_catalog.py` queries 134+ copyright-safe tracks directly across 21 albums, filters by `< 3:00` duration, and downloads directly via CDN stream URLs into `03_Audio_Library/01_Curated_BGM/<Category>/[BPM]_[Mood]_[TrackName]_[Artist].mp3`!

## Directory & Taxonomy Standard
All saved tracks live inside `03_Audio_Library/01_Curated_BGM/`:
- `01_Rolling_Cadence/` — `110–125 BPM`: steady pedaling, flat roads, coastal lanes
- `02_Scenic_Wonder/` — `80–105 BPM` Ambient / Melodic: wide panoramas, summits, rainbows, coastal hikes
- `03_Punchy_Climbs/` — `120–140 BPM` Upbeat / Driving: out-of-the-saddle efforts, fast descents
- `04_Warm_Social_And_Retro/` — `75–115 BPM` Acoustic / Bossa / Café / Retro: market trips (`SaPobla_Market_Trip`), café stops, parties, and 1977+ / 1980–1984 archival slideshows
- `05_Short_Transitions/` — `15–30s` stingers, comedic riffs, quick intros

**Filename Format:** `[BPM]_[Mood]_[TrackName]_[Artist].mp3`  
*(Examples: `118bpm_ChillBeat_CircuitRush_TheMiniVandals.mp3`, `085bpm_WarmChillhop_BubbleGum_Creatormix.mp3`)*

## Step-by-Step Execution Workflow

### Step 1: Analyze Project / Clip Motion Profile & Duration
1. Read `<project_dir>/Storyboard.md` and `<project_dir>/project_manifest.json` (or inspect the target video clip).
2. Determine target video duration (rule: `< 3:00`) and scene phases (e.g. `01_Rolling_Cadence` $\rightarrow$ `04_Warm_Social_And_Retro`).
3. Scan past projects in `04_Project_Catalog/` to compile the list of excluded (already used) tracks.

### Step 2: Source Fresh Music (Direct CreatorMix CLI or YouTube Studio Browser)

#### Option A: Direct CreatorMix Online Search & Auto-Download (Instant, Zero Browser Friction)
Run `fetch_creatormix_catalog.py` with your desired genre or search terms:
```bash
# Search fresh, never-used tracks in a specific genre:
python3 ./.agents/skills/find-music/scripts/fetch_creatormix_catalog.py --genre chillhop --max-duration 180

# Download the winning track (e.g. candidate #2):
python3 ./.agents/skills/find-music/scripts/fetch_creatormix_catalog.py --genre chillhop --download-idx 2
```
*The script downloads the high-quality MP3 directly from CreatorMix CDN, formats it with the standard `[BPM]_[Mood]_[TrackName]_Creatormix.mp3` naming convention, moves it into `03_Audio_Library/01_Curated_BGM/<Category>/`, and updates `music_catalog.json` automatically!*

#### Option B: YouTube Studio Audio Library Browser Tab (`studio.youtube.com`)
If searching for specific ambient or vintage moods in the YouTube Audio Library:
1. Connect via `chrome-devtools` or `/browser` to your open YouTube Studio tab.
2. Apply filters: Duration `< 3:00`, Genre (`Dance & Electronic`, `Ambient`, `Folk & Acoustic`), Mood (`Inspirational`, `Happy`, `Calm`).
3. Download the track to `~/Downloads` and run `save_music_track.py` to auto-tag and move it:
   ```bash
   python3 ./.agents/skills/find-music/scripts/save_music_track.py \
     --source latest \
     --bpm 118 \
     --mood "ChillBeat" \
     --title "Circuit Rush" \
     --artist "The Mini Vandals" \
     --category "01_Rolling_Cadence" \
     --source-site "YouTube_Audio_Library"
   ```

### Step 3: Confirm to Creator & Offer Timeline Placement
Report the new track to Alexander and offer to place it on Track `A2` via `/swap-music`, `/magic-movie`, or `/build-cut-table`.
