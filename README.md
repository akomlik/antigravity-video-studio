# Antigravity Video Studio v2 — User Tutorial & Daily Playbook (`@akomlik`)

Welcome to **Antigravity Video Studio v2**! This guide walks you through your complete end-to-end workflow—from writing a 5-line rough draft and dropping raw camera files into `~/Movies/2026/`, to co-developing `Storyboard.md` (with Section 5 YouTube Publishing & Composite Thumbnail specs), rendering GPX route maps & telemetry HUDs, synthesizing warm replicated voice-over (`EN` / `UA` / `RU`), building a broadcast-balanced 4-track timeline in **FilmCraft** (or **DaVinci Resolve**), and publishing 1 or 3 localized 4K editions to YouTube via the YouTube Data API v3.

> **Environment Setup (Bring Your Own Env Manager):**
> Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, and `GOOGLE_OAUTH_CLIENT_SECRET` using whichever method you prefer (`direnv` + 1Password, `.zshrc`, or a local git-ignored `.env` file in the studio root), then launch **Gemini** or **Antigravity** from that shell session so all skills and scripts inherit your environment variables automatically with zero wrapper dependencies:
> ```bash
> open -a Gemini
> # or
> open -a Antigravity
> # or launch the CLI directly:
> agy .
> ```
> Once you authorize YouTube once, `~/.config/antigravity_youtube/token.json` caches your OAuth refresh token for all future uploads.

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

## 2. End-to-End Studio v2 Architecture Diagram (Gear 1 Express & Gear 2 Supervised)

```
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STEP 0: Drop Raw Media + 5-Line Draft into ~/Movies/2026/YYYY-MM-DD_<Name>/                   │
│ (iPhone .MOV/.HEIC, BleeqUP Ranger .MP4/.JPG, Garmin .gpx, 5-line rough note)                 │
└───────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0: Run  /storyboard ~/Movies/2026/YYYY-MM-DD_<Name>                                     │
│ • Enforces FilmCraft >= v0.17.0 (auto-syncs filmcraft-cli) & runs ranger-sync if needed       │
│ • Converts .HEIC -> .jpg, extracts .proxies/, syncs .gpx (Imperial mi/ft/mph + 40m grade)     │
│ • Co-develops Storyboard.md (Scenes 00..N + Section 5 Publishing & Composite Thumbnail Spec)  │
│ • Harvests new people, landmarks & gear lore into my_digital_brain.md                         │
└──────────────────────┬─────────────────────────────────────────────────┬──────────────────────┘
                       │                                                 │
       [GEAR 1: Express Auto-Pilot]                      [GEAR 2: Supervised Precision]
                       ▼                                                 ▼
┌─────────────────────────────────────────────┐   ┌─────────────────────────────────────────────┐
│ Run  /magic-movie <path>                    │   │ 1. Run  /build-cut-table <path>             │
│ • Zero-pause build straight from            │   │    • Uses Argon 95% Implicit Context Cache  │
│   Storyboard.md (auto-logs cut_table.md)    │   │    • Generates scene-by-scene cut_table.md  │
│                                             │   │      with beat-quantized cuts & top 3 BGM   │
│                                             │   │    • PAUSES for human "OK" (or row tweaks   │
│                                             │   │      / "/swap-music to #2")                 │
│                                             │   │ 2. Run  /assemble-timeline                  │
│                                             │   │    • Executes approved cut_table.md in      │
│                                             │   │      FilmCraft MCP or DaVinci Resolve MCP   │
└──────────────────────┬──────────────────────┘   └──────────────────────┬──────────────────────┘
                       └────────────────────────┬────────────────────────┘
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ TIMELINE ENGINE & BROADCAST AUDIO MIX (assemble_engine.py + FilmCraft v0.17.0+ / Resolve)     │
│ • V1: 4K video cuts, Ken Burns stills, 62% PiP card over blurred 4K backdrop for <1080p clips │
│ • V2: Translucent GPX Corner Route Maps + conditional smoothed Telemetry HUD                  │
│ • A1: Speech-boosted live camera dialog (-22 dB mean, 120 Hz HPF + dynaudnorm) / Ambience     │
│ • A2: Multi-phase BGM (-7.5 dB under VO, native Essential Sound auto-ducking & +3.5 dB swell) │
│ • A3: Tamed PiP B-roll audio (-6.5 dB) / peak_ms-aligned Brehov SFX (never over speech)       │
│ • A4: Replicated warm Voice-Over (voice_jntybwupjc1s, -16 LUFS, EN / UA / RU)                 │
│ • Exports clean 4K MP4 (burnCaptions: false) + 0.2s remuxed _UA.mp4 & _RU.mp4 (ffmpeg copy)   │
└───────────────────────────────────────────────┬───────────────────────────────────────────────┘
                                                ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────┐
│ STAGE 4: YouTube Publishing (/publish-youtube or auto via /magic-movie)                       │
│ • Generates Imperial titles, clean 00:00 chapters, .srt tracks (en, ua -> uk, ru)             │
│ • Generates localized 1920x1080 Composite Thumbnails (thumbnail.jpg, _ua.jpg, _ru.jpg)        │
│ • Uploads via YouTube Data API v3 (inherited env vars + cached OAuth token):                  │
│   - en_only : 1 English 4K video (Private) + captions.en.srt                                  │
│   - option_a: 1 English 4K video (Private) + EN/UA/RU titles, descs & .srts                   │
│   - option_b: All 3 4K editions (EN Private + UA & RU Unlisted cross-linked)                  │
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
| **`/find-music [query]`** | Curates, non-reuse checks, & auto-downloads matching `< 3:00` tracks from the 134-track CreatorMix direct CDN catalog or YouTube Audio Library into `03_Audio_Library/01_Curated_BGM/`. |
| **`/swap-music [track]`** | Swaps the background music track on `A2` while preserving all video cuts and audio ducking. |
| **`/build-cut-table <path>`** | Gear 2: Generates the scene-by-scene Markdown Cut Table (`cut_table.md`) and waits for your `"OK"`. |
| **`/assemble-timeline`** | Executes an approved `cut_table.md` in FilmCraft or DaVinci Resolve. |
| **`/ingest-media <path>`** | Standalone media pre-processor (`ranger-sync`, `.HEIC` $\rightarrow$ `.jpg`, `.proxies/`, GPX sync). |
| **`/interview-brain [topic]`** | Interactive Q&A session to enrich `my_digital_brain.md` (`1977+ B&W`, `1980–1984 University`, Mallorca/California cycling). |
| **`/relink-archive <path>`** | Rewrites media paths in `.fcproj` & `project_manifest.json` when moving folders between `~/Movies/` and `/Volumes/Crucial-4T/Movies/`. |

---

## 6b. FilmCraft Version Gate (`>= v0.17.0`), CLI Auto-Sync & MCP Capability Diffing

Because [`storytold/filmcraft`](https://github.com/storytold/filmcraft/releases) ships new releases every 48–72 hours via the **ArtCraft Launcher**, Studio v2 includes an automatic version gate and capability tracker ([`check_filmcraft_env.py`](./.agents/skills/assemble-timeline/scripts/check_filmcraft_env.py) + [`00_Archive_Indexes/filmcraft_capabilities.json`](./00_Archive_Indexes/filmcraft_capabilities.json)) wired directly into `ingest_and_sync_media.py` and `assemble_engine.py`:

1. **Enforces `MIN_FILMCRAFT_VERSION = "0.17.0"`:** Prevents older FilmCraft versions from running without `essentialSound.*` auto-ducking, 5x faster GPU Bokeh Blur, and serialized bridge frame rendering.
2. **Auto-Syncs `filmcraft-cli` with `FilmCraft.app`:** Updating `FilmCraft.app` inside the ArtCraft Launcher does *not* automatically update `/opt/homebrew/bin/filmcraft-cli`. Whenever `check_filmcraft_env.py` detects that `filmcraft-cli` lags behind `FilmCraft.app`, it automatically downloads the matching `filmcraft-cli-<ver>-macos-universal.zip` from GitHub, clears macOS quarantine attributes, and ad-hoc signs the binary.
3. **Leverages Native FilmCraft `v0.17.0+` `essentialSound.*` Auto-Ducking:** [`assemble_engine.py`](./.agents/skills/assemble-timeline/scripts/assemble_engine.py) automatically tags `A4`/`A1` voice clips as `Dialogue` (with rumble repair + `Balanced Voice` clarity EQ), `A2` tracks as `Music`, `A1` riding clips as `Ambience`, and `A3` clips as `SFX`, and runs `essentialSound.generateDucking` so background music automatically ducks `-3.5 dB` under voiceover and swells back up during pure riding!
4. **Diffs New MCP Commands on Every Upgrade:** Whenever you update FilmCraft in the ArtCraft Launcher, run:
   ```bash
   ./.venv/bin/python .agents/skills/assemble-timeline/scripts/check_filmcraft_env.py --sync-cli
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

GitHub and Google Workspace use the existing `/Users/akomlik/src/ai-workflow/scripts/direnv-mcp` launcher. It reuses the inherited environment when `WORKFLOW_CONTEXT` is set; otherwise, it loads the environment through `direnv exec ~/src`. The project JSON contains no credentials. Fully quit IDEA before launching it from your configured shell with `open -a "IntelliJ IDEA"` when refreshing inherited environment variables.

Enable the project entries in **Settings → Tools → AI Assistant → Model Context Protocol (MCP)** and click **Apply**. If global entries with the same names already exist, use the project configuration for this workspace. Start a new agent chat after enabling changed servers. Chrome DevTools and DaVinci Resolve are mentioned elsewhere in this guide but are not configured in the Antigravity MCP file above.

### FilmCraft desktop connection

IDEA's AI Assistant reads this project's [`.ai/mcp/mcp.json`](./.ai/mcp/mcp.json), which registers **`filmcraft`** over STDIO. It uses the existing `/Users/akomlik/.local/bin/filmcraft-mcp-bridge` launcher to control the visible FilmCraft app on `127.0.0.1:9876`. The launcher reads the private token from `~/.config/filmcraft/control_token` and runs `~/src/filmcraft/target/release/filmcraft-cli mcp --bridge 127.0.0.1:9876`. These are local installation paths; adjust the configuration if setting up another Mac.

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

If you shoot POV cycling or outdoor footage with [**BleeqUP Ranger AI Sports Camera Glasses**](https://www.bleequp.com/products/bleequp-ranger-ai-sports-camera-glasses) alongside an iPhone and a Garmin `.gpx` computer, [`ingest_and_sync_media.py`](./.agents/skills/ingest-media/scripts/ingest_and_sync_media.py) (used by `/storyboard`, `/ingest-media`, and `/magic-movie`) automatically integrates with the companion open-source utility:

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
