# AGVS — Antigravity Video Studio v3 (`@akomlik`)

Welcome to **AGVS v3 (Antigravity Video Studio)** — powered by the unified **`agvs_core/`** modular Python engine and **Google AI Ultra (`Gemini 4 Carbon / Argon`)**! Open-source repository: [**`akomlik/antigravity-video-studio`**](https://github.com/akomlik/antigravity-video-studio). This guide walks you through your complete end-to-end autonomous video production workflow—from writing a 5-line rough draft and dropping raw camera files into `~/Movies/2026/`, to co-developing `Storyboard.md` (with signature AGVS bookends, YouTube Publishing & Composite Thumbnail specs), rendering GPX route maps & telemetry HUDs, synthesizing warm replicated voice-over (`EN` / `UA` / `RU`), building a broadcast-balanced 4-track timeline in **FilmCraft** (or **DaVinci Resolve**), and publishing 1 or 3 localized 4K editions to YouTube and Flickr via their native APIs.

> **Environment Setup (Bring Your Own Env Manager):**
> Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `FLICKR_*` credentials using whichever method you prefer (see [Section 9](#9-optional-zero-plaintext-secret-management-with-1password--direnv-alexanders-protocol) for Alexander's 1Password `envvar:*` protocol, or use `.zshrc` / local `.env`), then launch **Gemini** or **Antigravity** from that shell session so all skills and scripts inherit your environment variables automatically with zero wrapper dependencies:
> ```bash
> open -a Gemini
> # or
> open -a Antigravity
> # or launch the CLI directly:
> agy .
> ```
> Once you authorize YouTube once, `~/.config/antigravity_youtube/token.json` caches your OAuth refresh token for all future uploads.

---

## 1. Quick-Start: The 5-Line Draft $\rightarrow$ `/storyboard` $\rightarrow$ `/build-timeline` Flow

For any new ride, hike, excursion, or family event in `~/Movies/YEAR/YYYY-MM-DD_<Name>/`, you only need to write **3 to 5 lines** (either in a starter `Storyboard.md` inside the folder or directly in chat):

```markdown
Ride escorting Nina to Bellevue Zumba, then 21.5 mi coastal loop around Pollença Bay.
At the gate Nina spotted my blue Reynolds front brake pad on the ground!
Added IMG_8777.HEIC (pad on ground) & IMG_8775.HEIC (pad seated in Dura-Ace caliper).
Include 5s of Nina's Zumba video (https://www.youtube.com/watch?v=fGveL-nza0E).
Publish: option_a (Single 4K master, Unlisted, with EN/UA/RU subtitles).
Thumbnail: "SAVED AT THE GATE" with selfie + brake caliper cutout.
```

Then run the streamlined workflow:
1. **Stage 0: Unified Frontier Storyboard Co-Creation (`/storyboard` — Gemini 4 Carbon / Argon):**
   ```text
   /storyboard ~/Movies/2026/2026-11-02_Nina_Pollenca_Loop
   ```
   - **Automated Ingest & Telemetry (`agvs_core.ingest_sync` + `ranger_sync`):** Converts `.HEIC` $\rightarrow$ `.jpg`, extracts `.proxies/` video thumbnails & contact strips, syncs Garmin `.gpx` telemetry (`mi`, `ft`, `mph` with `>= 40m` grade smoothing), and scans Lightroom `.lrcat` route flashbacks.
   - **Creative Director & Lore Weaving:** Weaves emotional flashbacks from [`my_digital_brain.md`](./my_digital_brain.md), polishes the narrative arc around a single Controlling Idea (`Сверхзадача`), writes trilingual voiceover scripts, and designs the composite thumbnail.
2. **Stage 1: Interactive Assembly & 4K Export (`/build-timeline`):**
   ```text
   /build-timeline ~/Movies/2026/2026-11-02_Nina_Pollenca_Loop
   ```
   - Presents an interactive in-chat alignment card (`ask_question`, 1 question per turn) to confirm primary language (defaulting to live spoken language), background music (with 10s audio previews via Mac speaker), telemetry HUD visibility, and publishing mode.
   - Enforces post-bookend V1 visual continuity (`0` tick gaps), builds the ear-tested 4-track broadcast mix (`A1` camera speech normalized via `120 Hz` HPF + `dynaudnorm` to `-16 dB` mean, `A2` `180 Hz` midrange-calibrated BGM at `-15.5..-18.0 dB` riding swells with smooth `6.0–7.5 dB` keyframed ducking to `-21.5..-24.5 dB` under speech, `A3` `peak_ms`-aligned SFX, `A4` single-pass Studio-Dry VO at `-16 LUFS`), applies 2-axis Ken Burns motion to photos, pauses at the FilmCraft pre-render review gate, and exports clean 4K MP4 (`3840x2160`) with a unified `2.2s` half-sine outro fade.
   - **4K Multi-Language Edition Export (`edition_visual_mode`):** Defaults to `"universal_4k_remux"` (`0.2s` lossless `ffmpeg -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy` into `~/Movies/Exports/YEAR/<project>_RU.mp4` & `_UA.mp4`), or `"localized_4k_render"` (full `3840x2160` 4K `filmcraft-cli` render when `live_hud_ru/` or `_4K_RU.mp4` localized bookends are active—never downscaling to `1080p`).
3. **Stage 2: Headless YouTube & Flickr Publishing:**
   ```text
   /publish-youtube ~/Movies/2026/2026-11-02_Nina_Pollenca_Loop
   ```
   - Mandatory human review gate before upload.
   - Uploads 4K MP4 as `unlisted` by default, sets Imperial-first metadata, clean chapters, and multilingual `.srt` subtitles (`en`, `ua` $\rightarrow$ `uk`, `ru`) with SHA-256 hash caching to save up to 1,200 API quota units.
   - Prints ready-to-paste Facebook promotional copy and **📸 Flickr Publishing Metadata** (date-prefixed Russian title, description, tags, and album recommendation) directly in chat.

---

## 2. End-to-End AGVS v3 Architecture Diagram (`agvs_core/`)

> Architectural reference & v3 modular blueprint: [`docs/ARCHITECTURE_AUDIT_v3.md`](./docs/ARCHITECTURE_AUDIT_v3.md)

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 0: Drop Raw Media + 5-Line Draft into ~/Movies/2026/YYYY-MM-DD_<Name>/                   │
│ (iPhone .MOV/.HEIC, BleeqUP Ranger .MP4/.JPG, Garmin .gpx, 5-line rough note)                 │
└───────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0: Co-Design & Lore Harvest (/storyboard -> agvs_core.ingest_sync & flashback_lrcat)    │
│ • Enforces FilmCraft >= v0.17.0 & runs ranger_sync v0.2 (RTC brownout + <250ms batch guard)   │
│ • Converts .HEIC -> .jpg, extracts .proxies/, syncs .gpx (Imperial mi/ft/mph + 40m grade)     │
│ • Co-develops Storyboard.md (Scenes 00..N + Section 5 Publishing & Composite Thumbnail Spec)  │
│ • Harvests new people, landmarks & gear lore into my_digital_brain.md                         │
└───────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Declarative Assembly & Render (/build-timeline -> agvs_core.timeline_builder)        │
│ • Pydantic v2 Validation: ProjectManifest + TimelineSpec + StoryboardTuningSpec pre-flight    │
│ • V1: Post-bookend continuity repair (0 tick gaps), 4K cuts, Ken Burns stills, 62% PiP cards  │
│ • V2/V3/V4: Warm Vintage Parchment cards, paginated primary-translation cards, 1Hz GPX HUD    │
│ • A1: Speech-boosted live camera dialog (-16 dB mean / -1 dB peak, 120 Hz HPF + dynaudnorm)   │
│ • A2: 180 Hz midrange BGM (-15.5..-18.0 dB riding, 6.0-7.5 dB duck to -21.5..-24.5 dB)        │
│ • A3: Tamed PiP B-roll audio (-6.5 dB) / peak_ms-aligned Brehov SFX (never over speech)       │
│ • A4: Single-pass Studio-Dry Voice-Over ($GEMINI_VOICE_ID, -16 LUFS, 1.00x natural speed)     │
│ • Exports clean 4K MP4 (burnCaptions: false) + universal_4k_remux (0.2s) or localized_4k      │
└───────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Headless YouTube & Flickr Release (/publish-youtube -> agvs_core.youtube_pub)        │
│ • MANDATORY APPROVAL GATE: HumanApprovalRequiredError blocks any unapproved automated upload  │
│ • Generates Imperial titles, clean 00:00 chapters, .srt tracks (en, ua -> uk, ru)             │
│ • SHA-256 caption hash caching: Skips captions.insert if unchanged (saves 1,200 quota units)  │
│ • Generates localized 1920x1080 Composite Thumbnails (thumbnail.jpg, _ua.jpg, _ru.jpg)        │
│ • Uploads via YouTube Data API v3 (default privacy: "unlisted"):                              │
│   - option_a (Default): 1 English 4K video (Unlisted) + EN/UA/RU titles, descs & .srts        │
│   - option_b (Milestones): 3 4K editions (EN + UA/RU Unlisted) + pinned switcher comment      │
│ • Cross-links Flickr _RU.mp4 release & prints copy-ready Facebook + Strava + WhatsApp boxes   │
└───────────────────────────────────────────────────────────────────────────────────────────────┘
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
gpx_telemetry_hud: "auto"             # "auto" (activity-aware: > 2.0 mph ride / > 0.8 mph hike; off at stops & stills) | "always" | "off"
low_res_broll_mode: "pip_card"        # "pip_card" (62% framed inset over blurred 4K backdrop for <1080p clips) | "full"

# Audio & Voice-Over Knobs (4-Track Ear-Tested Broadcast Mix)
voiceover_persona: "$GEMINI_VOICE_ID" # Inherited from environment variable GEMINI_VOICE_ID
voiceover_target_lufs: -16.0          # Single-pass Studio-Dry EBU R128 integrated loudness (1.00x natural speed)
live_dialog_boost: "auto"             # 120 Hz HPF + sample-accurate atrim + post-mix dynaudnorm (-16 dB mean / -1 dB peak)
bgm_riding_midrange_rms_db: -16.0     # 180 Hz HPF midrange RMS (-16.0 dB mellow/+1.5 dB offset, -17.5 dB standard; <= -1.5 dBFS peak)
bgm_duck_db: 6.5                      # Smooth 6.0-7.5 dB keyframed duck under VO/speech (-21.5..-24.5 dB midrange RMS)
pip_broll_music_gain_db: -6.5         # Tames smartphone B-roll music (-30 dB mean) so it never overpowers

# YouTube Localization & Publishing Knobs
edition_visual_mode: "universal_4k_remux" # "universal_4k_remux" (default 0.2s 4K copy) | "localized_4k_render" (full 3840x2160 RU render)
publishing_mode: "option_a"           # "en_only" | "option_a" (Everyday default: 1 Unlisted 4K master + en/ua/ru .srt) | "option_b" (3 Unlisted 4K voiced editions)
toponym_phonetics: "mallorca_yeismo"  # Phonetic ll before vowel -> й/є (Майорка, Пойенса/Поєнса, Сойер/Соєр, Йук); pre-consonantal ll in Valldemossa -> Валдемоса
default_privacy: "unlisted"           # Default "unlisted" so pinned language-switcher comments & previews work immediately
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

# Signature AGVS Bookends Spec (agvs_bookends.py)
agvs_bookends:
  enabled: true                               # true (3.5s Pre-Flight Postcard + 4.5s Post-Ride Bar Tab) | false
  intro_duration_s: 3.5                       # Opening tilted (-2.0°) postcard over GPX route map canvas
  outro_duration_s: 4.5                       # Closing tilted (+1.5°) postcard over right-hand credits card
  studio_motto: "Gravity Reduction Module: FAILED (Climbing Anyway)"
  location_badge: "MALLORCA // BONAIRE ➔ COLL DE FEMENIA & MORTITX"
  cast_credits:
    - "Mark — Mecánico Campeón & 60th Birthday Honoree"
    - "Bruce & Lisa — Thursday Ride Ghosts (Plan B Instigators)"
    - "Uphill Trail Runners — The 146 bpm Sprint Catalysts"
    - "Nina — Bodega del Sol First-Night Dinner Partner"
  steed_credit: 'Mint Trek Madone 7 (Personal build on 2016 Craigslist frame · Stationed on island as "Mallorca Bike" since June 2022)'
  main_hero: "Antigravity Video Studio (AGVS v2.0)"
  github_repo: "github.com/akomlik/antigravity-video-studio"
  fuel_sponsors: "Pro Cycle Cafe VIP Card • Antonio's Bodega del Sol • 0x Alcohol"
```

### Signature AGVS Bookends: Pre-Flight Postcard & Post-Ride Bar Tab

AGVS v2 introduces a signature, data-driven bookend identity generated deterministically by [`agvs_bookends.py`](./.agents/skills/build-timeline/scripts/agvs_bookends.py):

1. **Opening Pre-Flight Postcard (00:00 – 00:03.5):**
   - Live video plays inside a **$-2.0^\circ$ tilted white postcard frame** (70% scale with embossed border and soft drop shadow).
   - Rendered over a 4K dark-slate GPX topographic route map canvas with cyan start and red summit pins.
   - Features the aerospace rubber stamp **🚀 AGVS // ANTIGRAVITY VIDEO STUDIO**, dynamic ride motto, and bottom ticket-stub flight manifest bar (`📅 Date | 🎬 Title | 🚴 mi • ⛰️ ft`).
   - Smoothly transitions to 100% full-screen video at $t = 3.5\text{s}$ right as primary voice-over begins.
2. **Closing Post-Ride Bar Tab & Production Credits (Final 4.5s):**
   - Keeps final live video playing inside a **$+1.5^\circ$ tilted postcard** with handwritten `"Wish you were here! — AGVS"` script on the bottom chin.
   - Right-side itemized **AGVS Production Receipt / Bar Tab** auto-populated from `Storyboard.md` and `my_digital_brain.md`:
     - **THE CREW / PELOTON:** Cast with humorous roles.
     - **LEAD STEED:** Bike with authentic personal history (e.g. personal build on 2016 Craigslist frame, stationed in Mallorca since June 2022).
     - **CAMERA & GIMBAL:** BleeqUP Ranger AI Glasses & iPhone 15 Pro.
     - **TELEMETRY & MEMORY BANK:** Garmin Edge 1040 (Edge 840 backup) & `my_digital_brain.md`.
     - **STUDIO ENGINE & MAIN HERO:** Antigravity Video Studio (AGVS v2.0) with open-source GitHub link ([`akomlik/antigravity-video-studio`](https://github.com/akomlik/antigravity-video-studio)).
     - **FUEL & SPONSORS:** Local cafes, bodegas, and nutrition.
     - **FOOTER STAMP:** Witty disclaimers (*"⚠️ 0% Gravity Guaranteed on Descents Only • No Argon Quotas Were Harmed in This Render"*).
3. **Continuous Timeline Continuity & 0.2s Lossless Remuxing:**
   - 100% contiguous V1 video track (0 black frames).
   - Universal bookend text allows `_RU.mp4` and `_UA.mp4` to continue using **0.2-second lossless `ffmpeg -c:v copy` remuxing** for Flickr and WhatsApp sharing.

### Key Linguistic & Technical Standards Built Into Studio v2
1. **Strict ISO Code `ua` for Ukraine Locally:** All local files (`captions.ua.srt`, `voiceover_ua_part1.wav`, `_UA.mp4`) and JSON keys use `ua` (`UA`), mapping `"ua" -> "uk"` strictly inside `upload_youtube_api.py` when calling the YouTube Data API v3 wire format.
2. **Mallorca Phonetic Toponym Rule:**
   - Intervocalic or word-initial `ll` before a vowel (`V + ll + V` or `# + ll + V`) is always written and voiced phonetically as `[j]` without soft `"ль"`: **Майорка** (never Мальорка), **Пойенса / Порт-де-Пойенса / Бадия-де-Пойенса** (`RU`), **Поєнса / Порт-де-Поєнса / Бадія-де-Поєнса** (`UA`), **Сойер / Соєр**, **Йук** (*Lluc*).
   - Pre-consonantal `ll` in **Valldemossa** (*Vall* + *de Mossa*) uses a clean hard `"л"`: **Валдемоса** (or **Вальдемоса**, never *«Вайдемосса»*).
3. **Why `option_b` Works on Non-YPP Channels:** YouTube Studio gates the multi-language `Audio` track uploader (`Add` button) to YouTube Partner Program channels (`1,000+` subscribers). Because our 4K video has zero burned-in English titles, `option_b` losslessly remuxes `_UA.mp4` and `_RU.mp4` in **`0.2 seconds`** (`ffmpeg -c:v copy`), uploads them as **Unlisted**, and cross-links them at the top of the `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` sections of your **Private** English master.

---

## 4. Unified Frontier Model Workflow (Google AI Ultra Plan)

With **Google AI Ultra (`20x` continuous headroom)**, AGVS v3 runs **Gemini 4 Carbon / Argon** end-to-end across every stage without manual model toggling or Pro-tier quota workarounds:

| Workflow Step / Slash Command | **Active Engine** | **Role** |
| :--- | :--- | :--- |
| **1. Pre-Processing (`/ingest-media`)** | **Gemini 4 Carbon / Argon** + `agvs_core.ingest_sync` | Runs `ranger_sync` v0.2, `sips`, `ffmpeg`, 40m GPX telemetry, and contact-strip landmark/stop-sync vision analysis. |
| **2. Co-Developing `/storyboard`** | **Gemini 4 Carbon / Argon** | Inspects `.proxies/*_thumb.jpg` & contact sheets, weaves `my_digital_brain.md` flashbacks, and drafts `Storyboard.md`. |
| **3. Curating Music (`/find-music`, `/swap-music`)** | **Gemini 4 Carbon / Argon** + `agvs_core.music_catalog` | Enforces Anti-Monotony Non-Reuse across `04_Project_Catalog/` and fetches `< 3:00` tracks from CreatorMix / YouTube Audio Library. |
| **4. Building & Publishing (`/build-timeline`, `/publish-youtube`, `/publish-flickr`)** | **Gemini 4 Carbon / Argon** + `agvs_core.services` | Validates Pydantic v2 schemas, renders Warm Vintage cards & 4K timelines, pauses at human gates, and publishes via YouTube/Flickr APIs. |

---

## 5. Where Everything Lives on Your Mac

| Folder / File | Location | Purpose |
| :--- | :--- | :--- |
| **Workspace Root & Core Package** | `./` & `./agvs_core/` | `pyproject.toml`, `studio.conf`, `agvs_core/` (schemas, ingest, GPX, audio DSP, vintage cards, bookends, timeline builder, YouTube/Flickr pub, Cockpit `services/`), and `tests/` (`< 15s` golden regression suite). |
| **Agent Skills (Thin CLI Shims)** | `.agents/skills/` | All 9 slash-command skills (`storyboard`, `build-timeline`, `publish-youtube`, `publish-flickr`, `find-music`, `swap-music`, `ingest-media`, `interview-brain`, `relink-archive`) backed by `< 40`-line CLI shims over `agvs_core`. |
| **Voice Cloning & Consent** | `03_Audio_Library/00_Voice_Cloning/` | Reference speech & mandatory spoken consent staging ([`README.md`](./03_Audio_Library/00_Voice_Cloning/README.md) guide for 1Password `$GEMINI_VOICE_ID` setup). |
| **Voice Profile** | `03_Audio_Library/03_Voice_Profile/` | Reference voice audio & local cache (resolving `$GEMINI_VOICE_ID` from inherited environment). |
| **Curated Music Pool** | `03_Audio_Library/01_Curated_BGM/` | Reusable copyright-safe music (`[BPM]_[Mood]_[TrackName]_[Artist].mp3`). |
| **Hot Raw Media** | `~/Movies/2026/YYYY-MM-DD_<Name>/` | Raw `.MP4`/`.MOV`/`.HEIC`/`.gpx` files, `.proxies/`, and synced `Storyboard.md`. |
| **Cloud Project Catalog** | `04_Project_Catalog/2026/YYYY-MM-DD_<Name>/` | `Storyboard.md`, `.fcproj`, `youtube_metadata.json`, `captions.{en,ua,ru}.srt`, `thumbnail.jpg`, and voiceover WAVs. |
| **Final 4K Exports** | `~/Movies/Exports/2026/` | Finished `<project>.mp4`, `<project>_UA.mp4`, and `<project>_RU.mp4` masters. |

---

## 6. Summary of Active Slash Commands

| Slash Command | Stage | Purpose |
| :--- | :--- | :--- |
| **`/storyboard <path>`** | Stage 0 | Converts `.HEIC` $\rightarrow$ `.jpg`, generates `.proxies/`, co-develops `Storyboard.md` (with Section 5 Publishing & Thumbnail Spec), and updates `my_digital_brain.md`. |
| **`/build-timeline <path>`** | Stage 1 | Interactive in-chat alignment card (`ask_question`), enforces V1 visual continuity (auto-repairs black gaps), builds 4-track broadcast mix (`A1` speech, `A2` music auto-ducking, `A3` SFX, `A4` VO), applies Ken Burns motion, and exports 4K MP4. |
| **`/publish-youtube <path>`** | Stage 2 | Mandatory human review gate, generates Imperial metadata, `00:00` chapters, hash-cached `.srt` tracks (`en`, `ua` $\rightarrow$ `uk`, `ru` saving 1,200 quota units), and Composite Thumbnail, then uploads to `@akomlik` and prints Facebook promo. |
| **`/find-music [query]`** | Tool | Curates, non-reuse checks, & auto-downloads matching `< 3:00` tracks from the 134-track CreatorMix direct CDN catalog or YouTube Audio Library into `03_Audio_Library/01_Curated_BGM/`. |
| **`/swap-music [track]`** | Tool | Swaps the background music track on `A2` while preserving all video cuts and audio ducking. |
| **`/ingest-media <path>`** | Pre-Proc | Standalone media pre-processor (`ranger-sync`, `.HEIC` $\rightarrow$ `.jpg`, `.proxies/`, GPX sync). |
| **`/interview-brain [topic]`** | Harvest | Interactive Q&A session to enrich `my_digital_brain.md` (`1977+ B&W`, `1980–1984 University`, Mallorca/California cycling). |
| **`/relink-archive <path>`** | Archive | Rewrites media paths in `.fcproj` & `project_manifest.json` when moving folders between `~/Movies/` and `/Volumes/Crucial-4T/Movies/`. |

---

## 6b. FilmCraft Version Gate (`>= v0.17.0`), CLI Auto-Sync & MCP Capability Diffing

Because [`storytold/filmcraft`](https://github.com/storytold/filmcraft/releases) ships new releases every 48–72 hours via the **ArtCraft Launcher**, Studio v2 includes an automatic version gate and capability tracker ([`check_filmcraft_env.py`](./.agents/skills/build-timeline/scripts/check_filmcraft_env.py) + [`00_Archive_Indexes/filmcraft_capabilities.json`](./00_Archive_Indexes/filmcraft_capabilities.json)) wired directly into `ingest_and_sync_media.py` and `assemble_engine.py`:

1. **Enforces `MIN_FILMCRAFT_VERSION = "0.17.0"`:** Prevents older FilmCraft versions from running without `essentialSound.*` auto-ducking, 5x faster GPU Bokeh Blur, and serialized bridge frame rendering.
2. **Auto-Syncs `filmcraft-cli` with `FilmCraft.app`:** Updating `FilmCraft.app` inside the ArtCraft Launcher does *not* automatically update `/opt/homebrew/bin/filmcraft-cli`. Whenever `check_filmcraft_env.py` detects that `filmcraft-cli` lags behind `FilmCraft.app`, it automatically downloads the matching `filmcraft-cli-<ver>-macos-universal.zip` from GitHub, clears macOS quarantine attributes, and ad-hoc signs the binary.
3. **Leverages Native FilmCraft `v0.17.0+` `essentialSound.*` Auto-Ducking:** [`assemble_engine.py`](./.agents/skills/build-timeline/scripts/assemble_engine.py) automatically tags `A4`/`A1` voice clips as `Dialogue` (with rumble repair + `Balanced Voice` clarity EQ), `A2` tracks as `Music`, `A1` riding clips as `Ambience`, and `A3` clips as `SFX`, and runs `essentialSound.generateDucking` so background music automatically ducks `-3.5 dB` under voiceover and swells back up during pure riding!
4. **Diffs New MCP Commands on Every Upgrade:** Whenever you update FilmCraft in the ArtCraft Launcher, run:
   ```bash
   ./.venv/bin/python .agents/skills/build-timeline/scripts/check_filmcraft_env.py --sync-cli
   ```
   to align `filmcraft-cli` and print a diff of all newly added MCP commands against `00_Archive_Indexes/filmcraft_capabilities.json` (716 commands in `v0.17.0`).

---

## 6c. IntelliJ IDEA: MCP Servers

This project's [`.ai/mcp/mcp.json`](./.ai/mcp/mcp.json) carries over the three servers configured in Antigravity's `~/.gemini/config/mcp_config.json`:

| Server | Launch configuration |
| :--- | :--- |
| `github` | `direnv-mcp npx -y @modelcontextprotocol/server-github` |
| `google-workspace` | `direnv-mcp uvx workspace-mcp --tool-tier complete` |
| `filmcraft` | `filmcraft-mcp-bridge` connecting to the visible app |

GitHub and Google Workspace use the existing `~/src/ai-workflow/scripts/direnv-mcp` launcher. It reuses the inherited environment when `WORKFLOW_CONTEXT` is set; otherwise, it loads the environment through `direnv exec ~/src`. The project JSON contains no credentials. Fully quit IDEA before launching it from your configured shell with `open -a "IntelliJ IDEA"` when refreshing inherited environment variables.

Enable the project entries in **Settings → Tools → AI Assistant → Model Context Protocol (MCP)** and click **Apply**. If global entries with the same names already exist, use the project configuration for this workspace. Start a new agent chat after enabling changed servers. Chrome DevTools and DaVinci Resolve are mentioned elsewhere in this guide but are not configured in the Antigravity MCP file above.

### FilmCraft desktop connection

IDEA's AI Assistant reads this project's [`.ai/mcp/mcp.json`](./.ai/mcp/mcp.json), which registers **`filmcraft`** over STDIO. It uses the existing `~/.local/bin/filmcraft-mcp-bridge` launcher to control the visible FilmCraft app on `127.0.0.1:9876`. The launcher reads the private token from `~/.config/filmcraft/control_token` and runs `~/src/filmcraft/target/release/filmcraft-cli mcp --bridge 127.0.0.1:9876`. These are local installation paths; adjust the configuration if setting up another Mac.

1. Start FilmCraft with its control channel enabled. With FilmCraft closed, run this in a terminal (the existing token file is required):
   ```bash
   (
     mkdir -p "$HOME/Movies/Cache_And_Previews" || exit 1
     cd "$HOME/Movies/Cache_And_Previews" || exit 1
     export FILMCRAFT_CONTROL_TOKEN="$(tr -d '[:space:]' < "$HOME/.config/filmcraft/control_token")"
     test -n "$FILMCRAFT_CONTROL_TOKEN" || exit 1
     /Applications/FilmCraft.app/Contents/MacOS/FilmCraft --control 9876
   )
   ```
   Keep that terminal running. If FilmCraft is already open without the control channel, save your work and quit it before relaunching with this command. Keep the token out of the MCP JSON and version control.
2. In **Settings → Tools → AI Assistant → Model Context Protocol (MCP)**, enable the project-level **filmcraft** entry and click **Apply**. IDEA may first show an external-configuration-change notification because automatic enabling is disabled. See [JetBrains' MCP setup instructions](https://www.jetbrains.com/help/ai-assistant/configure-an-mcp-server.html).
3. Check that the server connects and lists tools such as `doc_inspect`, `command_list`, and `command_run`. Start a new agent chat if the current chat does not pick up the added tools. A read-only check is: “Use FilmCraft MCP to inspect the current project.”

The FilmCraft app must remain open with the control channel enabled for editing tools to work. A successful MCP connection alone does not establish that the desktop app is reachable. The bridge CLI and installed app were both verified at **0.17.1** during setup; keep the bridge's CLI aligned when upgrading FilmCraft.

---

## 7. For BleeqUP Ranger AI Glasses Users (`bleequp-ranger-sync`)

If you shoot POV cycling or outdoor footage with [**BleeqUP Ranger AI Sports Camera Glasses**](https://www.bleequp.com/products/bleequp-ranger-ai-sports-camera-glasses) alongside an iPhone and a Garmin `.gpx` computer, [`ingest_and_sync_media.py`](./.agents/skills/ingest-media/scripts/ingest_and_sync_media.py) (used by `/storyboard`, `/ingest-media`, and `/build-timeline`) automatically integrates with the companion open-source utility:

- **Repository:** [**`akomlik/bleequp-ranger-sync`**](https://github.com/akomlik/bleequp-ranger-sync) (`ranger-sync` CLI)
- **What It Solves:**
  1. **Restores True Capture Timestamps & EXIF/QuickTime Metadata:** BleeqUP `.MP4` exports overwrite `CreationDate` with the iOS transfer time while storing the true millisecond UTC epoch in the filename (`VIDEO_1793434415483.MP4`, `IMG_1793437400537.JPG`), and `.JPG` stills lack `DateTimeOriginal`, camera/lens EXIF tags, and GPS coordinates.
  2. **Recovers Pre-Sync RTC Clock Drift (~11.3 min/day):** When the glasses sit in standby without opening Camera Settings in the mobile app, the internal sleep oscillator drifts ~11.3 minutes/day. `ranger-sync` detects timeline skew against your iPhone reference shots and `.gpx` track, shifts timestamps & filenames (`--shift-files ... --rename-shifted`), and injects exact GPX coordinates into every clip and photo.
- **How Studio v2 Uses It:**
  - If `ranger-sync` is installed on your `PATH`, Step 0a of `ingest_and_sync_media.py` runs `ranger-sync <project_dir>` automatically whenever `VIDEO_*` or `IMG_17*` files are present (and writes a `.bleequp_synced` marker so it only runs once).
  - If you already ran `ranger-sync apply` manually on a ride folder before starting, pass `--skip-bleequp-sync` (or touch `.bleequp_synced`).

---

## 8. Credits, Inspiration & Populating the SFX Audio Library

This workflow was inspired by the AI-driven video editing architecture and *Digital Brain* + *Editing Constitution* methodology shared by:

1. **Igor Brehov (`@igor_brehov`) — [«Как смонтировать с ИИ даже сложное видео. Полный гайд по AI Claude Code»](https://www.youtube.com/watch?v=l30VMUhaff0)**
   - **Original *Конституция монтажа* & Free 209-Sound SFX Package (Google Drive):** [`https://drive.google.com/drive/folders/1QJ5PFyerFwdyHY_K9luzCn26-TsH4lly`](https://drive.google.com/drive/folders/1QJ5PFyerFwdyHY_K9luzCn26-TsH4lly)
   - **How to Populate `03_Audio_Library/02_SFX/` (Optional):**
     To keep this Git repository lightweight, `.wav` audio files are excluded via `.gitignore`, while the translated English catalog with exact `duration_ms` and `peak_ms` peak-alignment metadata is tracked in [`03_Audio_Library/02_SFX/catalog.json`](./03_Audio_Library/02_SFX/catalog.json) and documented in [`03_Audio_Library/02_SFX/README.md`](./03_Audio_Library/02_SFX/README.md). If you want to use Igor's 209 cinematic sound effects on Audio Track `A3`, download *«Звуки для саунд-дизайна»* from his [Google Drive folder](https://drive.google.com/drive/folders/1QJ5PFyerFwdyHY_K9luzCn26-TsH4lly) and drop the `.wav` files into the corresponding `03_Audio_Library/02_SFX/01_Whooshes_Soft/` .. `19_Ambient_Pads/` folders.
2. **Additional MCP Video Editing Showcases:**
   - **Applorable (`@applorable`):** [Why ArtCraft Beats Adobe for AI Workflows (With MCP)](https://www.youtube.com/watch?v=DBLJZ44TWEg) (FilmCraft & LightCraft MCP integration)
   - **Team 2 Films (`@team2films`):** [DaVinci Resolve 21.1 BEST New Feature TESTED - AI Editing with Claude and ChatGPT](https://www.youtube.com/watch?v=yRxmdTUh7GU)

---

## 9. Optional: Zero-Plaintext Secret Management with 1Password & direnv (Alexander's Protocol)

For zero plaintext secrets on disk, this workspace integrates with Alexander's standard 1Password protocol (`~/src/ai-workflow/scripts/direnv-manager`):

### How It Works
1. In `~/Gdrive-gmail/.envrc`, `source direnv-manager --runtime --account "my.1password.com"` is configured.
2. At shell startup, `direnv-manager` dynamically queries the **`Private`** vault on `my.1password.com` for any items titled `envvar:<VARIABLE_NAME>` (e.g. `envvar:GEMINI_API_KEY`, `envvar:FLICKR_API_KEY`, `envvar:FLICKR_OAUTH_TOKEN`).
3. If the item category is `API_CREDENTIAL`, `direnv-manager` reads the `credential` field; if `PASSWORD`, `LOGIN`, or `SECURE_NOTE`, it reads `password`.
4. The secrets are automatically exported into the shell environment (`export VARIABLE_NAME="..."`).
5. When launching Antigravity, Gemini, or running scripts from this shell, all child processes inherit these environment variables automatically with zero plaintext files on disk.

### Saving New Secrets via `op` CLI
To add new secrets that follow this protocol without opening the 1Password UI, run:
```bash
op item create --category "API Credential" \
  --title "envvar:<VARIABLE_NAME>" \
  --vault "Private" \
  --account "my.1password.com" \
  "credential[concealed]=<SECRET_VALUE>"
```

### Configured Secrets in this Studio
- `GEMINI_API_KEY`: Google Gemini API key.
- `GOOGLE_OAUTH_CLIENT_ID` & `GOOGLE_OAUTH_CLIENT_SECRET`: YouTube Data API v3 OAuth desktop client credentials.
- `GOOGLE_OAUTH_REFRESH_TOKEN`: YouTube OAuth2 refresh token for zero-file, in-memory credential refreshing.
- `FLICKR_API_KEY` & `FLICKR_API_SECRET`: Flickr App Garden developer credentials.
- `FLICKR_OAUTH_TOKEN` & `FLICKR_OAUTH_TOKEN_SECRET`: Flickr OAuth 1.0a access tokens for headless video publishing (`/publish-flickr`).

