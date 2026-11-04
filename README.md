# Antigravity Video Studio v2 — User Tutorial & Daily Playbook (`@akomlik`)

Welcome to **Antigravity Video Studio v2**! This guide walks you through your complete end-to-end workflow—from writing a 5-line rough draft and dropping raw camera files into `~/Movies/2026/`, to co-developing `Storyboard.md` (with Section 5 YouTube Publishing & Composite Thumbnail specs), rendering GPX route maps & telemetry HUDs, synthesizing warm replicated voice-over (`EN` / `UA` / `RU`), building a broadcast-balanced 4-track timeline in **FilmCraft** (or **DaVinci Resolve**), and publishing 1 or 3 localized 4K editions to YouTube via the YouTube Data API v3.

> **Environment Setup (Bring Your Own Env Manager):**
> Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, and `GOOGLE_OAUTH_CLIENT_SECRET` using whichever method you prefer (`direnv` + 1Password, `.zshrc`, or a local git-ignored `.env` file in the studio root), then launch Google Antigravity from that shell session (e.g., `agy .` or `open -a "Google Antigravity"`) so all skills and scripts inherit your environment variables automatically with zero wrapper dependencies. Once you authorize YouTube once, `~/.config/antigravity_youtube/token.json` caches your OAuth refresh token for all future uploads.

---

## 1. Quick-Start: The 5-Line Draft $\rightarrow$ `/storyboard` $\rightarrow$ `/magic-movie` Flow

For any new ride, hike, excursion, or family event in `~/Movies/YEAR/YYYY-MM-DD_<Name>/`, you only need to write **3 to 5 lines** (either in a starter `Storyboard.md` inside the folder or directly in chat):

```markdown
Ride escorting Nina to Bellevue Zumba, then 21.5 mi coastal loop around Pollença Bay.
At the gate Nina spotted my blue Reynolds front brake pad on the ground!
Added IMG_8777.HEIC (pad on ground) & IMG_8775.HEIC (pad seated in Dura-Ace caliper).
Include 5s of Nina's Zumba video (https://www.youtube.com/watch?v=fGveL-nza0E).
Publish: option_b (all 3 locales: EN Private + UA/RU Unlisted).
Thumbnail: "SAVED AT THE GATE" with selfie + brake caliper cutout.
```

Then run just **two commands**:
1. **Co-Develop the Storyboard & Section 5 Spec:**
   ```text
   /storyboard ~/Movies/2026/2026-11-02_Nina_Pollenca_Loop
   ```
   - Converts `.HEIC` $\rightarrow$ `.jpg`, extracts `.proxies/` video thumbnails, syncs Garmin `.gpx` telemetry (`mi`, `ft`, `mph`), inspects live camera audio levels, drafts the full `Storyboard.md` (including **Section 5: Production & YouTube Publishing Spec** and the **Composite Thumbnail** layout), and harvests new people/places into [`my_digital_brain.md`](./my_digital_brain.md).
2. **Build, Render & Publish End-to-End:**
   ```text
   /magic-movie ~/Movies/2026/2026-11-02_Nina_Pollenca_Loop
   ```
   - Reads Section 5 of `Storyboard.md`, renders GPX corner maps & telemetry HUD overlays (`V2`), synthesizes warm replicated voice-over (`Audio 4`) in `EN` (plus `UA` & `RU` if `option_b`), normalizes live camera dialog (`Audio 1`), balances multi-phase BGM (`Audio 2`) and PiP B-roll audio (`Audio 3`), exports clean 4K MP4(s) with **zero burned-in bottom titles**, generates/applies the `"SAVED AT THE GATE"` composite `thumbnail.jpg`, and uploads to `@akomlik` on YouTube!

---

## 2. End-to-End Studio v2 Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ STEP 0: Drop Raw Media + 5-Line Draft into ~/Movies/2026/YYYY-MM-DD_<Name>/  │
│ (iPhone .MOV/.HEIC, BleeqUP Ranger .MP4/.JPG, Garmin .gpx, 5-line rough note)│
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0: Run  /storyboard ~/Movies/2026/YYYY-MM-DD_<Name>                    │
│ • Converts .HEIC -> .jpg, extracts .proxies/, syncs .gpx (Imperial mi/ft/mph)│
│ • Co-develops Storyboard.md (Scenes + Section 5 Publishing & Thumbnail Spec) │
│ • Harvests new people, landmarks & gear lore into my_digital_brain.md        │
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ GEAR 1: Run  /magic-movie ~/Movies/2026/YYYY-MM-DD_<Name>                    │
│ • V1: 4K video cuts, Ken Burns stills, 62% PiP card for low-res B-roll       │
│ • V2: Translucent GPX Corner Route Maps + conditional Telemetry HUD          │
│ • A1: Speech-boosted live camera dialog (-22 dB mean, 120 Hz HPF + dynaudnorm)│
│ • A2: Multi-phase BGM (-7.5 dB under VO, swelling +3.5 dB during pure riding)│
│ • A3: Tamed PiP B-roll audio (-6.5 dB) / subtle SFX (never over speech)      │
│ • A4: Replicated warm Voice-Over (voice_jntybwupjc1s, -16 LUFS, EN / UA / RU)│
│ • Exports clean 4K MP4 (burnCaptions: false) + 0.2s remuxed _UA.mp4 & _RU.mp4│
└──────────────────────────────────────┬───────────────────────────────────────┘
                                       ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: YouTube Publishing (/publish-youtube or auto via /magic-movie)      │
│ • Generates Imperial titles, clean 00:00 chapters, .srt tracks (en, ua, ru)  │
│ • Generates or applies YouTube-Studio-style Composite Thumbnail (1920x1080)  │
│ • Uploads via YouTube Data API v3 (inherited env vars + cached OAuth token): │
│   - en_only : 1 English 4K video (Private) + captions.en.srt                 │
│   - option_a: 1 English 4K video (Private) + EN/UA/RU titles, descs & .srts  │
│   - option_b: All 3 4K editions (EN Private + UA & RU Unlisted cross-linked) │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Master Reference: Section 5 Tuning Knobs (`Storyboard.md`)

Every `Storyboard.md` ends with **Section 5: Production & YouTube Publishing Spec (Tuning Knobs)** so you can customize any video by editing a single YAML block (or telling me in plain text):

```yaml
# Visual & Telemetry Knobs
sequence_resolution: "3840x2160@30"
units: "imperial"                     # "imperial" (default: mi, ft, mph + metric in parens) | "metric"
burned_in_titles: false               # false (default: clean 4K frames; rely on .srt CC + voiceover) | true
gpx_corner_map: true                  # true (default: 3.5s top-right GPX progress map at scene transitions) | false
gpx_telemetry_hud: "auto"             # "auto" (shown only on active riding scenes; hidden at stops/gates) | "always" | "off"
low_res_broll_mode: "pip_card"        # "pip_card" (62% framed inset over blurred 4K backdrop for <1080p clips) | "full"

# Audio & Voice-Over Knobs (4-Track Broadcast Mix)
voiceover_persona: "voice_jntybwupjc1s" # Replicated from Alexander's Zero-T Performance Self-Talk.m4a
voiceover_gain_db: -0.5               # Matches normalized live speech (-19 dB mean)
live_dialog_boost: "auto"             # Boosts quiet BleeqUP camera speech (<-35 dB) to -22 dB mean & strips overlapping SFX
bgm_gain_under_vo_db: -7.5            # Warmly audible underneath voiceover (-26 dB mean)
bgm_swell_riding_db: +3.5             # Swells to -4.0 dB (-22.9 dB mean) during riding-only sections
pip_broll_music_gain_db: -6.5         # Tames smartphone B-roll music (-30 dB mean) so it never overpowers

# YouTube Localization & Publishing Knobs
publishing_mode: "option_b"           # "en_only" | "option_a" (Everyday default: 1 video + en/ua/ru .srt) | "option_b" (Special occasions: EN Private + UA/RU Unlisted voiceover editions)
toponym_phonetics: "mallorca_yeismo"  # Phonetic ll before vowel -> й/є (Майорка, Пойенса/Поєнса, Сойер/Соєр, Йук); pre-consonantal ll in Valldemossa -> Валдемоса
default_privacy: "private"            # Primary video uploaded as "private" for review; UA/RU editions as "unlisted"
playlists:
  - "Mallorca"
  - "2026 Mallorca Cycling"

# Custom Thumbnail Spec (YouTube Studio "Ask Suggestions" Composite Style — Localized per Edition)
thumbnail:
  mode: "composite_ai"                        # "composite_ai" (Hero portrait + Prop sticker cutout + 3-4 word hook) | "preserve" | "frame"
  headline_text: "SAVED AT THE GATE"          # English top banner (thumbnail.jpg)
  headline_text_ua: "ВРЯТОВАНИЙ БІЛЯ ВОРІТ"   # Ukrainian top banner (thumbnail_ua.jpg)
  headline_text_ru: "СПАСЁН У ВОРОТ"          # Russian top banner (thumbnail_ru.jpg)
  hero_image: "IMG_8744.jpg"                  # Left: Smiling rider portrait over blurred scenic backdrop
  prop_cutout: "IMG_8775.jpg"                 # Right: White-outlined sticker cutout of the story's key prop
  fallback_timestamp_sec: 56.5
```

### Key Linguistic & Technical Standards Built Into Studio v2
1. **Strict ISO Code `ua` for Ukraine Locally:** All local files (`captions.ua.srt`, `voiceover_ua_part1.wav`, `_UA.mp4`) and JSON keys use `ua` (`UA`), mapping `"ua" -> "uk"` strictly inside `upload_youtube_api.py` when calling the YouTube Data API v3 wire format.
2. **Mallorca Phonetic Toponym Rule:**
   - Intervocalic or word-initial `ll` before a vowel (`V + ll + V` or `# + ll + V`) is always written and voiced phonetically as `[j]` without soft `"ль"`: **Майорка** (never Мальорка), **Пойенса / Порт-де-Пойенса / Бадия-де-Пойенса** (`RU`), **Поєнса / Порт-де-Поєнса / Бадія-де-Поєнса** (`UA`), **Сойер / Соєр**, **Йук** (*Lluc*).
   - Pre-consonantal `ll` in **Valldemossa** (*Vall* + *de Mossa*) uses a clean hard `"л"`: **Валдемоса** (or **Вальдемоса**, never *«Вайдемосса»*).
3. **Why `option_b` Works on Non-YPP Channels:** YouTube Studio gates the multi-language `Audio` track uploader (`Add` button) to YouTube Partner Program channels (`1,000+` subscribers). Because our 4K video has zero burned-in English titles, `option_b` losslessly remuxes `_UA.mp4` and `_RU.mp4` in **`0.2 seconds`** (`ffmpeg -c:v copy`), uploads them as **Unlisted**, and cross-links them at the top of the `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` sections of your **Private** English master.

---

## 4. Google AI Pro Quota Guide (Which Model to Select)

| Workflow Step / Slash Command | **Recommended Model** | **Why** |
| :--- | :--- | :--- |
| **1. Pre-Processing (`/ingest-media`)** | 🟢 **Gemini 3.8 Flash** | Runs local Python (`ranger-sync`, `sips`, `ffmpeg`, GPX math) at 0% Argon cost. |
| **2. Drafting & Co-Developing `/storyboard`** | 🟢 **Gemini 3.8 Flash** *(or Argon Medium)* | Inspects `.proxies/*_thumb.jpg` thumbnails, drafts `Storyboard.md` + Section 5, and updates `my_digital_brain.md`. |
| **3. Curating Browser Music (`/find-music`)** | 🟢 **Gemini 3.8 Flash** | Filters open YouTube Audio Library & `creatormix.com` tabs (`< 3:00`). |
| **4. Building & Publishing (`/magic-movie`, `/publish-youtube`)** | 🟢 **Gemini 3.8 Flash** or 🟡 **Argon Medium** | All audio mixing, GPX widget rendering, voiceover synthesis, and YouTube API uploads run via deterministic Python scripts in `.venv`. |

---

## 5. Where Everything Lives on Your Mac

| Folder / File | Location | Purpose |
| :--- | :--- | :--- |
| **Workspace Root** | `./` | Contains `README.md`, `editing_constitution.md`, `my_digital_brain.md`, and `.venv` (`google-genai`, `google-api-python-client`, `pillow`). |
| **Agent Skills** | `.agents/skills/` | All 10 slash-command skills (`storyboard`, `magic-movie`, `publish-youtube`, `assemble-timeline`, `build-cut-table`, `find-music`, `swap-music`, `ingest-media`, `interview-brain`, `relink-archive`). |
| **Voice Profile** | `03_Audio_Library/03_Voice_Profile/` | Reference voice audio (`alexander_komlik_reference_24k.wav`) & persistent Gemini TTS persona ID (`voice_id.json` $\rightarrow$ `voice_jntybwupjc1s`). |
| **Curated Music Pool** | `03_Audio_Library/01_Curated_BGM/` | Reusable copyright-safe music (`[BPM]_[Mood]_[TrackName]_[Artist].mp3`). |
| **Hot Raw Media** | `~/Movies/2026/YYYY-MM-DD_<Name>/` | Raw `.MP4`/`.MOV`/`.HEIC`/`.gpx` files, `.proxies/`, and synced `Storyboard.md`. |
| **Cloud Project Catalog** | `04_Project_Catalog/2026/YYYY-MM-DD_<Name>/` | `Storyboard.md`, `.fcproj`, `youtube_metadata.json`, `captions.{en,ua,ru}.srt`, `thumbnail.jpg`, and voiceover WAVs. |
| **Final 4K Exports** | `~/Movies/Exports/2026/` | Finished `<project>.mp4`, `<project>_UA.mp4`, and `<project>_RU.mp4` masters. |

---

## 6. Summary of All 10 Slash Commands

| Slash Command | Purpose |
| :--- | :--- |
| **`/storyboard <path>`** | Stage 0: Converts `.HEIC` $\rightarrow$ `.jpg`, generates `.proxies/`, co-develops `Storyboard.md` (with Section 5 Publishing & Thumbnail Spec), and updates `my_digital_brain.md`. |
| **`/magic-movie <path>`** | Gear 1: One-command build from `Storyboard.md` $\rightarrow$ GPX overlays + replicated VO + 4-track broadcast audio mix $\rightarrow$ clean 4K MP4(s) + optional YouTube upload. |
| **`/publish-youtube <path>`** | Stage 4: Generates Imperial metadata, `00:00` chapters, `.srt` subtitles (`en`, `ua`, `ru`), and Composite Thumbnail, then uploads (`en_only`, `option_a`, or `option_b`) to `@akomlik`. |
| **`/find-music <path>`** | Curates & auto-saves matching `< 3:00` tracks from YouTube Audio Library / `creatormix.com` into `03_Audio_Library/01_Curated_BGM/`. |
| **`/swap-music [track]`** | Swaps the background music track on `A2` while preserving all video cuts and audio ducking. |
| **`/build-cut-table <path>`** | Gear 2: Generates the scene-by-scene Markdown Cut Table (`cut_table.md`) and waits for your `"OK"`. |
| **`/assemble-timeline`** | Executes an approved `cut_table.md` in FilmCraft or DaVinci Resolve. |
| **`/ingest-media <path>`** | Standalone media pre-processor (`ranger-sync`, `.HEIC` $\rightarrow$ `.jpg`, `.proxies/`, GPX sync). |
| **`/interview-brain [topic]`** | Interactive Q&A session to enrich `my_digital_brain.md` (`1977+ B&W`, `1980–1984 University`, Mallorca/California cycling). |
| **`/relink-archive <path>`** | Rewrites media paths in `.fcproj` & `project_manifest.json` when moving folders between `~/Movies/` and `/Volumes/Crucial-4T/Movies/`. |
