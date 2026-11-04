---
name: swap-music
description: Swaps the background music track on audio lane A2 of the active FilmCraft or DaVinci Resolve timeline with another track from ~/Music/Cycling_BGM/ (03_Audio_Library/01_Curated_BGM/) and re-trims the 1.5s intro fade-in and 2.0s outro fade-out, just like changing songs in iMovie Magic Movie.
---

# Instant Background Music Track Swapper (`/swap-music`)

## Model & Execution Instructions
1. Run this skill on **Gemini 3.8 Flash** (consumes 0% Argon quota).
2. If Alexander asks to "try a different song" without naming a specific file, list the remaining tracks in `~/Music/Cycling_BGM/` (`01_Rolling_Cadence`, `02_Scenic_Wonder`, `03_Punchy_Climbs`, `04_Warm_Social_And_Retro`, `05_Short_Transitions`) matching the project's mood folder, or offer to pull a fresh track from his open YouTube Audio Library / CreatorMix tabs via `/find-music`.
3. In **FilmCraft MCP** (`filmcraft` server) or **DaVinci Resolve MCP**:
   - Import the new music file from `~/Music/Cycling_BGM/` via `media_import` / `media_pool`.
   - Call `sequence_inspect` / `timeline` to read the current sequence end time and existing `A2` clip ID.
   - Replace the audio clip on track `A2` with the new music track, trim its out-point to match the sequence duration, apply `-15.0 dB` baseline gain (`-20.0 dB` speech-ducking keyframes), and apply a `1.5s` linear fade-in at the head and `2.0s` exponential fade-out at the tail.
