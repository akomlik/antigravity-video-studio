---
name: swap-music
description: Swaps the background music track on audio lane A2 of the active FilmCraft or DaVinci Resolve timeline with another track from 03_Audio_Library/01_Curated_BGM/ and re-trims the 1.5s intro fade-in and 2.0s outro fade-out, just like changing songs in iMovie Magic Movie.
---

# Instant Background Music Track Swapper (`/swap-music`)

## Execution Instructions (`agvs_core.services.swap_music`)
1. Run seamlessly on **Gemini 4 Carbon / Argon** (Google AI Ultra unified frontier workflow).
2. If Alexander asks to "try a different song" without naming a specific file, list unused candidate tracks in `03_Audio_Library/01_Curated_BGM/` (`01_Rolling_Cadence`, `02_Scenic_Wonder`, `03_Punchy_Climbs`, `04_Warm_Social_And_Retro`, `05_Short_Transitions`) via `agvs_core.music_catalog.recommend_music_tracks()`, or pull a fresh track from CreatorMix / YouTube Audio Library via `/find-music`.
3. Update `bgm_track` in `timeline_spec.json` (`agvs_core.services.swap_music`) and re-run `build_timeline.py --project-dir ...` (or `--mux-audio-only` if video cuts are unchanged):
   - Automatically recalibrates `A2` via `agvs_core.audio_dsp.calculate_bgm_gains()` (`180 Hz` midrange RMS, Mandatory Peak Headroom Guard $\le -1.5\text{ dBFS}$, `-15.5..-18.0 dB` open swells, smooth `6.0–7.5 dB` keyframed speech ducking to `-21.5..-24.5 dB`, `+1.5 dB` mellow offset + `1.8 kHz` presence EQ) with `1.5s` intro fade-in and unified `2.2s` half-sine outro fade-out.
