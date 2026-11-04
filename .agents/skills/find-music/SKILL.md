---
name: find-music
description: Curates, filters, previews, and auto-saves matching background music (< 3:00 duration) from your two open browser tabs (YouTube Audio Library and creatormix.com) or local 03_Audio_Library/01_Curated_BGM/ pool for a specific project or clip, renaming downloaded tracks to [BPM]_[Mood]_[TrackName]_[Artist].mp3 for future reuse.
---

# Live Browser & Local Pool Music Matcher (`/find-music`)

## Purpose
Implements the **"Music for Video Workflow"** (`1lZCANKqhc2ZQ20LeimogKIXDEOW_gm2gTuVwZTi31YY`). Instead of paying for stock subscriptions, this skill inspects your project's `Storyboard.md` / `project_manifest.json` motion profile and either:
1. Matches an already-saved track in `03_Audio_Library/01_Curated_BGM/`, OR
2. Connects to your **two open browser tabs** (**YouTube Audio Library** in YouTube Studio and **Creator Mix** at `https://creatormix.com/stream`) via the `chrome-devtools` skill / browser automation, applies the exact genre, mood, and `< 3:00` duration filters for your clip, lets you preview or downloads the winning track, and **auto-saves** it into `03_Audio_Library/01_Curated_BGM/<Category>/[BPM]_[Mood]_[TrackName]_[Artist].mp3` for future reuse!

## Directory & Taxonomy Standard
All saved tracks live inside `03_Audio_Library/01_Curated_BGM/`:
- `01_Rolling_Cadence/` — `110–125 BPM`: steady pedaling, flat roads, coastal lanes
- `02_Scenic_Wonder/` — `80–105 BPM` Ambient / Melodic: wide panoramas, summits, rainbows, coastal hikes
- `03_Punchy_Climbs/` — `120–140 BPM` Upbeat / Driving: out-of-the-saddle efforts, fast descents
- `04_Warm_Social_And_Retro/` — `75–115 BPM` Acoustic / Bossa / Café / Retro: market trips (`SaPobla_Market_Trip`), café stops, parties, and 1977+ / 1980–1984 archival slideshows
- `05_Short_Transitions/` — `15–30s` stingers, comedic riffs, quick intros

**Filename Format:** `[BPM]_[Mood]_[TrackName]_[Artist].mp3`  
*(Examples: `118bpm_ChillBeat_CircuitRush_TheMiniVandals.mp3`, `095bpm_AmbientWonder_Pulsar_DensityAndTime.mp3`)*

## Step-by-Step Execution Workflow

### Step 1: Analyze Project / Clip Motion Profile & Duration
1. Read `<project_dir>/Storyboard.md` and `<project_dir>/project_manifest.json` (or inspect the target video clip).
2. Determine:
   - **Target Video Duration** (Rule: always filter for tracks `< 3:00` unless building a long archival slideshow).
   - **Primary & Secondary Phases** (e.g., Phase 1: `01_Rolling_Cadence` 110–125 BPM $\rightarrow$ Phase 2: `02_Scenic_Wonder` reveal, or `04_Warm_Social_And_Retro` acoustic guitar/bossa nova for market & café comedy).
3. Check `03_Audio_Library/01_Curated_BGM/music_catalog.json` and the category subfolders first. If strong local matches already exist, list the top 2 local matches alongside fresh browser filter recommendations.

### Step 2: Filter Your Two Open Browser Tabs (YouTube Audio Library & `creatormix.com`)
Use the `chrome-devtools` skill (`list_pages` $\rightarrow$ `take_snapshot` $\rightarrow$ `click` / `fill`) or `/browser` to interact with Alexander's two music tabs:
1. **Tab 1 — YouTube Audio Library (`studio.youtube.com/channel/.../music`):**
   - Apply **Duration Filter:** `< 3:00` (e.g., `01:30` to `03:00`).
   - Apply **Genre & Mood Filters** based on the scene:
     - *Rolling / Cycling:* Genre = `Dance & Electronic` or `Rock` / `Indie`, Mood = `Inspirational` or `Happy` / `Bright`.
     - *Scenic / Hike / Bay Reveal:* Genre = `Ambient` or `Cinematic`, Mood = `Calm` or `Inspirational`.
     - *Market Excursion / Café / Social:* Genre = `Folk & Acoustic`, `Jazz & Blues`, or `Pop`, Mood = `Bright`, `Happy`, or `Romantic`.
   - Read the visible track table rows (Title, Genre, Mood, Artist, Duration, BPM if shown) and click the Play/Download button on the best match.
2. **Tab 2 — Creator Mix (`https://creatormix.com/stream`):**
   - Filter by Category / Playlist (`Vlog`, `Chill`, `Gaming / Action`, `Synthwave`, `Acoustic / Indie`).
   - Inspect the track list and click Download on the matching track.

### Step 3: Auto-Save & Tag Into `03_Audio_Library/01_Curated_BGM/` for Future Reuse
Once a track is downloaded into `~/Downloads`, immediately run `save_music_track.py` so it is renamed to `[BPM]_[Mood]_[TrackName]_[Artist].mp3`, filed into the right `03_Audio_Library/01_Curated_BGM/<Category>/` folder, backed up to Google Drive, and indexed in `music_catalog.json`:
```bash
python3 ./.agents/skills/find-music/scripts/save_music_track.py \
  --source latest \
  --bpm 118 \
  --mood "ChillBeat" \
  --title "Circuit Rush" \
  --artist "The Mini Vandals" \
  --category "01_Rolling_Cadence" \
  --source-site "YouTube_Audio_Library" \
  --notes "Steady tempo, coastal rolling shots"
```
Confirm the new standardized filename to Alexander and offer to place it on Track `A2` via `/swap-music`, `/magic-movie`, or `/build-cut-table`.
