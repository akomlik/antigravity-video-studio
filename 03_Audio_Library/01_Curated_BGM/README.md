# Curated Royalty-Free Music Pool (`03_Audio_Library/01_Curated_BGM/`)

Welcome to the **Antigravity Video Studio** curated background music repository. All tracks in this directory are 100% copyright-cleared, monetizable, and zero-cost, curated exclusively from **CreatorMix (`creatormix.com`)** and the **YouTube Studio Audio Library**.

---

## 1. Directory Taxonomy & Pacing Matrix

Tracks are categorized by motion profile, tempo (BPM), and narrative pacing:

| Directory | BPM Range | Mood / Instrumentation | Primary Studio Usage |
| :--- | :--- | :--- | :--- |
| **`01_Rolling_Cadence/`** | `110–125 BPM` | Upbeat, steady, rhythmic guitars, light funk, electronic grooves | Flat roads, coastal lanes, paceline cruising (`cycling_ride` default) |
| **`02_Scenic_Wonder/`** | `80–105 BPM` | Melodic, ambient, airy synths, sweeping vistas | Summit panoramas, rainbows, coastal hikes (`hike_outdoor` default) |
| **`03_Punchy_Climbs/`** | `120–140 BPM` | Driving, energetic, punchy drums, aggressive bass/brass | Out-of-the-saddle efforts, crux climbs, fast descents |
| **`04_Warm_Social_And_Retro/`** | `75–115 BPM` | Acoustic guitar, bossa nova, warm piano, chillhop, vintage soul | Market trips, café stops, parties, 1977+ / 1980–1984 slideshows |
| **`05_Short_Transitions/`** | `15–30s` | Quick stingers, comedic riffs, intro hooks | Scene 00 flashbacks, chapter cards, comedic punchlines |

### Standard Filename Convention
```text
[BPM]_[Mood]_[TrackName]_[Artist].mp3
```
*Examples:*
- `118bpm_ChillBeat_CircuitRush_TheMiniVandals.mp3`
- `085bpm_WarmChillhop_Snails_Creatormix.mp3`
- `124bpm_DrivingCadence_Sunseeker_Creatormix.mp3`

---

## 2. Core Audio Engineering Laws

### Article I: Anti-Monotony & Mandatory Music Non-Reuse Law
- **Never reuse the same background music track across video projects.** Every ride, excursion, and family milestone receives its own distinct musical identity.
- Pre-flight checks (`verify_music_non_reuse()`) automatically verify that no track on timeline lane `A2` has appeared in any prior project inside `04_Project_Catalog/`.

### Article V: Mandatory Peak Headroom Guard (Ceiling $\le -1.5\text{ dBFS}$)
Commercial and creator music tracks are already mastered hot (peaks between `-1.6 dBFS` and `-0.2 dBFS`).
- **Never apply blind positive fader gain without peak bounds.**
- `calculate_bgm_gains()` measures both `mean_volume` (RMS) and `max_volume` (true peak).
- Gains are strictly bounded by:
  $$\text{max\_allowed\_gain\_db} = -1.5\text{ dBFS} - \text{raw\_max\_db}$$
  *(or $-2.0\text{ dBFS}$ when presence EQ is enabled).*
- This guarantees the music fader will **NEVER** drive FilmCraft's master audio bus into the red zone (`0 dBFS`) and eliminates digital clipping distortion on bass drum hits.

### Dynamic Calibration & Ducking Standard
- **Riding / Visual Swells (`target_riding_db`):** `-17.5 dB` RMS (punchy, clean, unclipped).
- **Ducked Under Speech/VO (`target_ducked_db`):** `-23.5 dB` RMS (smooth `6.0 dB` duck via sidechain compression or FilmCraft Essential Sound).
- Camera dialogue (`A1`) and Voice-Over (`A4`) sit at `-16.0 dB` mean / `-1.0 dB` peak, allowing spoken words to cut through with `7.5 dB` of clear separation.

---

## 3. Musical Arrangement & Mobile Translation Guide

When selecting tracks for cycling and outdoor motion videos, consider how the track's instrumentation translates to smartphone, tablet, and laptop speakers:

### Recommended: Midrange-Rich Arrangements (Best for Action & Cycling)
- **Instruments:** Acoustic strumming guitars, brass sections, rhythm piano, crisp snares, bright synth leads (prominent energy in **500 Hz – 4 kHz**).
- **Why it works:** Human ears are most sensitive to this frequency range, and smartphone speakers reproduce it cleanly. The music feels loud, driving, and energetic at conservative dB levels without risking clipping.
- **Top Categories:** `01_Rolling_Cadence/` and `03_Punchy_Climbs/`.

### Caution: Sub-Bass Heavy / Chillhop Tracks (Best for Reflection & Relaxed Scenes)
- **Instruments:** Heavy sub-bass 808s and kick drums (60–100 Hz), low-passed mellow keys, filtered muffled snares.
- **Acoustic Reality:** Phone and laptop speakers physically cannot reproduce frequencies below 120 Hz. While the kick drum might peak near `0 dBFS` on the master meter, it sounds subjectively quiet on a phone.
- **AGVS Automatic Handling:** When a chillhop or ambient track is detected (`bpm < 95` or keywords like `chillhop`, `chill`, `ambient`, `lofi`), the engine automatically applies a **1.8 kHz Presence EQ (`equalizer=f=1800:t=q:w=1.2:g=2.0`)** to lift piano and guitar melodies without boosting the sub-bass kick into distortion.
- **Top Categories:** `04_Warm_Social_And_Retro/` (café stops, market wanderings, quiet evening walks).
