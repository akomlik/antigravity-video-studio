## UNIVERSAL EDITING CONSTITUTION (editing_constitution.md)

**System:** Google Antigravity Desktop App — Unified Google AI Ultra (`Gemini 4 Carbon / Argon`) + `agvs_core/` v3 Engine  
**Studio Root:** `./` (configured dynamically via `studio.conf` & `agvs_core.config`)  
**Media Tiers:** `~/Movies/YEAR/YYYY-MM-DD_<name>/` (Hot) & Cold External Archive configured in `studio.conf`  
**Curated Music Pool:** `03_Audio_Library/01_Curated_BGM/` (YouTube Audio Library + `creatormix.com`)  
**Target NLEs:** FilmCraft MCP (`127.0.0.1:9876`) & DaVinci Resolve Studio 21.1 MCP

### ARTICLE I: STAGE 0 COLLABORATIVE Storyboard.md & AUTOMATIC MEMORY HARVESTING

- **Stage 0 — `Storyboard.md` First & The Upfront "Controlling Idea" (`Сверхзадача`) Law:**
    - Every short film must be built around **ONE clear Controlling Idea / Central Thesis ("Сверхзадача")** chosen *before* scripting scenes (inspired by Igor's professional critique).
    - **The "One Spine + Memory Banking" Rule:** Never pack 4–5 competing life stories into a single 2–3 minute ride vlog. During `/storyboard`, the agent proposes 2–3 candidate Controlling Ideas via `ask_question` (e.g., *(A) Resilience: How cycling & friends helped overcome cancer*, *(B) Partnership: How shared passions make a marriage with Nina even stronger*, or *(C) The Peloton Brotherhood: The extraordinary characters you meet on two wheels*). Once one thesis is selected, every scene, flashback (max 1–2 per film), and closing takeaway serves that single idea. Any extra memories discovered along the way are **harvested into `my_digital_brain.md` and banked for future videos**!
    - Every project folder must have a **`Storyboard.md`** file (synced to `04_Project_Catalog/YEAR/<project_name>/Storyboard.md`).
    - If `Storyboard.md` is missing or is an unpopulated skeleton, the agent MUST first run `ingest_and_sync_media.py` (which converts `.HEIC` to `.jpg`, extracts `.proxies/` video thumbnails, and reads EXIF/QuickTime GPS/timestamps), visually inspect the proxy thumbnails, align on the **Single Controlling Idea**, and populate `Storyboard.md` with:
        - **The Controlling Idea (1-Sentence North Star Thesis & Final Takeaway)**
        - **Character Roster & First-Appearance Callout Badges ("Who's Who in the Frame")**
        - **Narrative Overview & Comedic/Emotional Arc**
        - **Scene-by-Scene Breakdown (`Scene 00` $\rightarrow$ `Scene N`)** with exact file ranges, timestamps, GPS coordinates, and visual descriptions.
        - **Two-Phase or Multi-Phase Musical Structure** (e.g., Phase 1 Rolling Cadence $\rightarrow$ Phase 2 Scenic Reveal or Market Comedy).
        - **Archival & Flashback Links** (any throwback photos or YouTube video URLs to slice via `fetch_yt_broll_clip.py`).
    - In interactive `/storyboard` mode, present the drafted `Storyboard.md` and ask the user if they want to refine any scene or add historical media before moving to video production.
- **Mandatory Automatic Memory Harvesting into `my_digital_brain.md`:**
    - Whenever `Storyboard.md` is created or updated with user context, immediately extract any newly mentioned **people/companions**, **landmarks/restaurants/markets**, **recurring wardrobe/gear items**, and **cross-year archival links**, and append them under the appropriate section of `./my_digital_brain.md`.
- **The Unified 3-Stage Conversational Pipeline (Fed by `Storyboard.md`):**
    - **Stage 0 — Interactive `/storyboard` (Narrative Co-Creation & Memory Harvesting):** Ingests raw media, extracts proxies, co-designs the story arc in chat, and automatically harvests memories/people into `my_digital_brain.md`.
    - **Stage 1 — Conversational `/build-timeline` (Zero-IDE, Interactive Timeline Assembly):**
        1. Presents an in-chat clickable alignment card (`ask_question`) for Primary Voice-Over Language, Music Track #1 & #2 (with 10-second Mac speaker preview via `afplay`), and Publishing Mode (`option_a` default).
        2. Automatically writes settings into `Storyboard.md` on disk (no manual YAML/markdown editing in external IDEs!).
        3. Builds the 4-track `.fcproj` timeline (`schema_version: 17`), loads it live into the **FilmCraft GUI**, and **pauses at a Mandatory Pre-Render Gate** so Alexander can play/scrub the timeline in FilmCraft first.
        4. **Only after Alexander approves the live FilmCraft timeline**, exports the clean 4K `.mp4` and lossless Russian edition (`_RU.mp4`) to `~/Movies/Exports/YEAR/`, and generates `facebook_promo.md` and metadata package.
    - **Stage 2 — `/publish-youtube` (Headless Release):**
        - Uploads the 4K MP4 (`unlisted` default), sets metadata & localized titles/subtitles, posts language switcher comment, and prints copy-ready Facebook post in chat.

### ARTICLE II: GENRE-ADAPTIVE NARRATIVE PROFILES (WHEN Storyboard.md HAS NO CUSTOM SCENES)

When `Storyboard.md` defines explicit scenes (like `Scene 00` through `Scene 12` in `2026-11-01_SaPobla_Market_Trip`), follow `Storyboard.md` scenes 1-to-1. Otherwise, adapt the 5-Act structure (90s–300s) to `detected_genre`:

| **Act** | **Profile A: `cycling_ride` (90s–165s)** | **Profile B: `hike_outdoor` / Excursion (90s–180s)** | **Profile C: `social_event` / Party (90s–180s)** | **Profile D: `archival_slideshow` (120s–300s)** |
| :--- | :--- | :--- | :--- | :--- |
| **Act 1 (~10%)** | **Rollout & Title:** Bike check / PCH start + `YYYY-MM-DD Route` + GPX km/m subtitle. | **Flashback Hook or Departure:** Optional `Scene 00` flashback + transit/trailhead establisher. | **Venue & Arrival:** Setting the scene, hosts, decorations, and warm title card. | **Era & Context Hook:** Iconic cover photo (e.g., 1980 campus or 1977 B&W scan) + Era Title. |
| **Act 2 (~30%)** | **Paceline Flow:** Alternate BleeqUP 120° POV with scenic roadside angles on the beat. | **The Journey / Market Stroll:** Exploring stalls, trails, local color, and companion reactions. | **Mingling & Activities:** Candid interactions, games, dancing, or table conversations. | **Early Chapter / Youth:** Chronological or thematic group 1 (e.g., freshman/sophomore 1980–81). |
| **Act 3 (~25%)** | **Crux Climb & Descent:** Peak GPX gradient ($\ge 5\%$) & fast descent ($\ge 40\text{ km/h}$ wind-gated). | **The Discovery / Main Event:** Key find, summit panorama, or comedic punchline (`A1` speech). | **The Centerpiece / Toasts:** Speeches, birthday cake, live toast audio (`A1` priority), laughter. | **Core Memories & Excursions:** Student trips, candid dorm/lab moments, or 1977+ street series. |
| **Act 4 (~25%)** | **Café & Crew Oasis:** GPX $<2.5\text{ km/h}$ stop; mandatory pastry/coffee close-up + crew selfie. | **Lunch, Bakery & Redemption:** Dining comedy, coffee/croissant close-ups, and crew portraits. | **Group Portraits & Warmth:** Posed and candid group photos with slow Ken Burns motion. | **Graduation / Reunion ("Then & Now"):** Senior year (1984) or side-by-side modern reunion photos. |
| **Act 5 (~10%)** | **Homeward Spin & Outro:** Relaxed return spin + final still/map + 2.0s audio fade. | **Epilogue & Payoff:** Home-cooked meal payoff or new gear showcase + 2.0s audio fade. | **Farewells & Finale:** Closing laugh/wave + warm final group frame + 2.0s music fade. | **Timeless Finale:** Signature closing group portrait (5.0s hold) + dedication subtitle. |

### ARTICLE III: ANTI-MONOTONY & GENRE PACING LAWS

- **Clip & Still Duration Matrix by Genre (Quantized to Musical Bars):**
    - **`cycling_ride`:** Fast action/descents: `1.8s–3.2s` (4–6 beats); Paceline cruising: `2.5s–4.5s` (6–8 beats); Café speech clips: `3.0s–6.0s`; Stills: `2.5s–3.5s`.
    - **`hike_outdoor` & Market Excursions:** Walking/strolling clips: `2.5s–4.5s`; Story/punchline clips: `3.5s–7.0s` (preserve full joke/reaction); Stills: `3.0s–4.0s`.
    - **`social_event` (Parties):** B-roll party clips: `2.5s–4.5s`; Toast/dialogue clips: `4.0s–10.0s` (never cut mid-sentence); Stills: `3.0s–4.0s`.
    - **`archival_slideshow` (1980–1984 University / 1977+ B&W):** Individual portrait stills: `3.5s–4.0s`; Multi-person group photos (3+ classmates): **`4.5s–5.5s`** (gives viewers time to scan every face).
- **The 2-Clip Perspective Rule:**
    - Never place more than **2 consecutive BleeqUP Ranger POV clips** of identical road geometry without breaking perspective using an iPhone 15 Pro clip, a still photograph with motion, or an archival B-roll insert.
    - In `archival_slideshow` mode, alternate between wide group shots, medium two-shots, and close-up portraits.
- **BleeqUP Hardware Trim Law (`ranger-sync` Complement):**
    - Trim the first `0.5s` and final `0.5s` of manually triggered BleeqUP Ranger clips to eliminate hand-to-temple shake.

### ARTICLE IV: STILL IMAGE ANIMATION (KEN BURNS) & VINTAGE ASPECT RATIO PROTECTION

- **No Frozen Stills:** Every still photograph placed on the timeline MUST have keyframed motion (`scale` and `position` using Ease-In / Ease-Out Bezier curves):
    - **Action / Ride / Excursion Stills:** Scale `100% -> 108%` (Push-In) or `108% -> 100%` (Pull-Out) over `2.5s–3.5s`.
    - **Archival / 1980–1984 University / 1977+ B&W Stills:** Gentle nostalgic drift — Scale `100% -> 105%` or `105% -> 100%` over `4.0s–5.5s`. Alternate Push-In, Pull-Out, and subtle horizontal drift (`position.x: -15 -> +15`) on consecutive slides.
- **Full 4K UHD (`3840x2160`) Output Standard & Uncropped Face Guarantee:**
    - Whenever any source video or photo in a project exceeds `1920x1080` (e.g., 2.7K BleeqUP Ranger, 4K iPhone/YouTube, 12MP–48MP photos), the sequence and master export MUST be **Full 4K UHD (`3840x2160` at `30` or `60` fps)** with `scale_to_frame: true` and true-center source anchors (`src_w / 2.0, src_h / 2.0`) on every clip.
    - **YouTube Publishing Standard (`/publish-youtube`):** Default to the channel's archival title format (`YYYY-MM-DD · <Title>`) and automatically assign regional/topic playlists (e.g., `Mallorca`).
    - **Rule for Group & Archival Photos:** Never zoom-crop a 4:3 or vertical (9:16 / 3:4) photograph to fill 16:9 if doing so clips people's heads or classmates standing on the edges. Instead, place a scaled-up copy (`180%`) on `V1` with `Gaussian Blur` (`amount: 45`) and `60%` opacity, and animate the uncropped original photo centered on `V2`.
- **Zero-Copy & Zero-Crop Archival Pulls Standard (`~/Movies/Archival_Pulls/`):**
    - Stills published from Lightroom Classic (or external archives) into `~/Movies/Archival_Pulls/LR_Published_4K/` represent a centralized, shared asset pool across all video projects.
    - **Zero Duplication:** Video projects must NEVER duplicate full-resolution still files into individual project folders (`~/Movies/<YEAR>/<project>/`). When a project references an archival photo, reference its relative path directly or create a relative symlink inside the project folder (`ln -sf ../../Archival_Pulls/LR_Published_4K/<category>/<file>.jpg .`).
    - **Zero Pre-Cropping on Disk:** Source images must NEVER be cropped destructively on disk (e.g. using `sips` or `ffmpeg` to force `3840x2160`). Sensor aspect ratios (3:2, 16:10, 4:3, vertical) must be kept 100% intact. FilmCraft and modern NLEs handle aspect ratio adaptation, center anchors, and Ken Burns framing natively in the GPU shader pipeline (`scaleToFill` / `scaleToFit`).
    - **Ken Burns Bleed Advantage:** Preserving the full sensor image provides essential extra margin ("bleed") for Ken Burns panning and zooming across the 16:9 frame without resolution degradation, letterbox bars, or edge clipping. Destructive cropping permanently destroys this motion bleed.
- **GPX Geospatial Flashback Discovery Standard (`find_gpx_flashbacks.py`):**
    - Whenever a project contains Garmin/Wahoo GPX route telemetry, Stage 0 `/storyboard` automatically scans the active Lightroom Classic catalog along the route's spatial corridor (within 50m–100m) in `< 3s`.
    - **Dual Candidate Surface:**
        1. **4K Published Masters ($\ge 3★$):** If the photo is already published in `~/Movies/Archival_Pulls/LR_Published_4K/`, it is marked ready-to-cut and linked via relative symlink.
        2. **Unrated Hidden Gems ($0★$):** If an unrated photo lies right on the route, its high-resolution rendered JPEG preview is extracted directly from Lightroom's `Previews.lrdata` into `.flashback_candidates/` for review.
    - **Co-Creation Feedback Loop:** Over time, working on video projects drives Alexander to rate and publish newly discovered historical photos, organically populating the shared 4K Lightroom stock library as a natural side-effect of video editing.

### ARTICLE V: CURATED FREE MUSIC POOL (`03_Audio_Library/01_Curated_BGM/`), MIXING & TRACK SWAPPING

- **Track Assignment Standard & Zero-Script Project Law (`timeline_spec.json` + `build_timeline.py`):**
    - **The Zero-Script Project Law:** Project folders (`04_Project_Catalog/YEAR/<project>/`) are **100% declarative data** (`Storyboard.md` + `timeline_spec.json` + `narration_scripts.json`). **Never create, clone, or run per-project Python scripts** (`assemble_<project>.py`, `build_<project>_overlays.py`). All timeline assembly, overlay rendering, 1Hz live HUD generation, and RMS audio calibration are executed exclusively by the shared studio engine (`.agents/skills/build-timeline/scripts/build_timeline.py`), which enforces `check_zero_project_scripts_preflight()` and `verify_music_non_reuse()`.
    - `V1`: Primary Video & Background Blur Fill Track
    - `V2`: Warm Vintage Parchment Character Callout Badges & Flashback Memory Cards (e.g. `badge_*.png`)
    - `V3`: Bilingual On-Camera Speech Translation Cards (`sub_*.png` via `render_translation_subtitle_card`; displays simultaneously with `V2` badges without track collisions)
    - `V4`: **Live 1Hz Dynamic Telemetry HUD (`live_hud/hud_XXXX.png`) & GPX Corner Route Maps** (never static HUDs; fades in on first second of run, holds at 100% solid opacity across internal 1s boundaries so the card never blinks, and fades out on the last second)
    - `A1`: Native Camera Audio (Tire roll, freewheel clicks, speech, market punchlines, toasts, café banter)
    - `A2`: Dedicated Background Music Track (`03_Audio_Library/01_Curated_BGM/`) — **dynamically calibrated via `agvs_core.audio_dsp.calculate_bgm_gains()` combining a 4th-order `180 Hz` midrange high-pass filter (`24 dB/oct`, ignoring sub-bass inflation), an EBU R128 integrated loudness ceiling (`max_riding_lufs = -15.5 LUFS`, `max_ducked_lufs = -26.5 LUFS` so hot `-8..-11 LUFS` tracks never overpower narration), Mandatory Peak Headroom Guard (ceiling $\le -1.5\text{ dBFS}$, or $\le -2.0\text{ dBFS}$ with presence EQ), automatic `+1.5 dB` mellow/chillhop (`< 95 BPM` / chill / ambient / warm / lofi) offset + `1800 Hz` (`+2.0 dB`) presence EQ, and a smooth keyframed `11.5 dB` speech duck (`>= 10.5 LU` separation below `-16 LUFS` VO/live speech)**
    - `A3`: Subtle Contextual Sound Effects (`03_Audio_Library/02_SFX/catalog.json` — 209 Brehov cinematic WAVs across `01_Whooshes_Soft` through `19_Ambient_Pads`, aligned by `peak_ms` so the sound peak lands on the exact frame of motion/caption reveal)
    - `A4`: Single-Pass Studio-Dry Replicated Voice-Over (`$GEMINI_VOICE_ID`, `-16 LUFS` integrated loudness, `1.00x` natural speech speed)
- **Anti-Monotony & Mandatory Music Non-Reuse Law:**
    - **Never reuse the same background music track across video projects.** Every ride, hike, party, and event deserves its own distinct musical identity.
    - **Online Catalog Search Threshold ($< 100$ Local Titles):** Until the local pool in `03_Audio_Library/01_Curated_BGM/` exceeds **100 local titles**, `/storyboard`, `/find-music`, and `/build-timeline` MUST NOT default to recycling the same few local tracks.
    - Instead, the system checks `04_Project_Catalog/` to identify all previously used tracks and queries the 130+ track **CreatorMix Online Catalog** (`fetch_creatormix_catalog.py`) or YouTube Audio Library to pull fresh, never-before-used candidate tracks matching the detected genre, auto-downloading new tracks directly into `03_Audio_Library/01_Curated_BGM/<Category>/`.
- **Music Taxonomy & Pool Mapping (`Music for Video Workflow` Standard):**
    - All tracks in `03_Audio_Library/01_Curated_BGM/` follow `[BPM]_[Mood]_[TrackName]_[Artist].mp3` (sourced from **YouTube Audio Library** and **Creator Mix `creatormix.com`**, filtered to `< 3:00` duration):
        - `01_Rolling_Cadence/` (110–125 BPM): Steady pedaling, flat roads, coastal lanes (`cycling_ride` default).
        - `02_Scenic_Wonder/` (80–105 BPM): Ambient / Melodic vistas, summits, rainbows, coastal hikes (`hike_outdoor` default).
        - `03_Punchy_Climbs/` (120–140 BPM): Upbeat / Driving out-of-the-saddle efforts, fast descents.
        - `04_Warm_Social_And_Retro/` (75–115 BPM): Acoustic guitar, bossa nova, warm piano/synth for market trips, café stops, parties, and 1977+ / 1980–1984 slideshows (`social_event` & `archival_slideshow` default).
        - `05_Short_Transitions/` (15–30s): Stingers, quick intros, comedic riffs, and short reels.
    - Quantize non-speech visual cut durations to multiples of the track's `beat_interval_s` ($60 / \text{BPM}$) using FilmCraft's `254,016,000,000` ticks/sec timebase.
- **Gain, Ducking & Fade Matrix (`agvs_core/audio_dsp.py` Canonical Ear-Tested Spec):**
    - **Music Open Swells (`A2` Midrange RMS behind `180 Hz` 24 dB/oct HPF + EBU R128 LUFS Ceiling):** **`-15.5 dB` to `-18.0 dB`** midrange RMS (`-16.0 dB` for mellow/chillhop tracks `< 95 BPM` with `+1.5 dB` midrange offset; `-17.5 dB` for standard upbeat tracks), capped by both `max_riding_lufs = -15.5 LUFS` and the Mandatory Peak Headroom Guard ($\le -1.5\text{ dBFS}$).
    - **Speech & Voice-Over Ducking (`A2` Keyframed Envelope):** Smooth **`11.5 dB` broadcast duck** (`0.35s` ramp) capped at `max_ducked_lufs = -26.5 LUFS` (`~ -27.0 LUFS` under `-16 LUFS` speech)—guaranteeing `>= 10.5 LU` crystal-clear narration separation even on brickwall-mastered (`-10 LUFS`) chillhop tracks like *"Indigo"*, while keeping warm musical texture underneath.
    - **Native BleeqUP Audio (`A1`) when GPX Speed $< 40\text{ km/h}$:** **`-6.0 dB`** (natural road/freehub presence).
    - **Native BleeqUP Audio (`A1`) when GPX Speed $\ge 40\text{ km/h}$:** **`-24.0 dB` or Mute** (mandatory wind-buffeting suppression).
    - **Fades on `A2` & Unified `2.2s` Synchronized Outro Fade Law:**
        - **Head:** `1.0s` to `1.5s` fade-in (`curve=hsin`) starting with clip motion.
        - **Mandatory Synchronized Outro Audio Fade Law (`2.2s` Single-Source Fade):** Whenever a sequence ends with a visual `Dip to Black`, the master audio output (`[fullout]`) executes a single-source **`2.2s` Half-Sine outro fade (`afade=t=out:st=<TOTAL_DUR - 2.2>:d=2.2:curve=hsin`)** reaching complete silence (`-infinity dB`) as the video hits black (never double-stacking redundant fader + master fades).

### ARTICLE VI: TRANSITIONS, STORY CAPTIONS & COLOR CONTINUITY

- **Action, Excursions & Parties (85% Hard Cuts / 15% Dissolves):** Use clean beat-aligned hard cuts within scenes, reserving `Cross Dissolve` (`0.5s`) for scene boundaries and flashback transitions (such as entering/exiting `Scene 00`).
- **Archival Slideshows (`1.0s` Cross Dissolves):** For 1980–1984 university slideshows and 1977+ B&W retrospectives, apply smooth `1.0s` (30 frames) `Cross Dissolve` transitions between slides and a `1.5s` `Dip to Black` between chronological eras.
- **Storyboard Punchline Captions & First-Appearance Character Callout Badges (`V2`):**
    - **Character Identification Law ("Who's Who in the Frame"):** Viewers outside Alexander's immediate circle do not automatically know who is who when multiple riders or companions appear on screen. The first time a key person (e.g., **Nina**, **Bruce**, **Lisa**, **Ian**, **Pete**, **Brian**, **Chas**, **Paula**, **Jeff**, or university classmates) appears clearly in a video clip or still photo, place a sleek `3.0s–3.5s` frosted-glass **Character Callout Badge** on `V2` via `render_character_callout_badge()` in `gpx_widgets.py` (e.g., `NINA KOMLIK · Wife & Riding Partner` / `НИНА · Моя жена и спутница`, or `Left to Right: Paula · Alexander · Jeff (SJBC, April 2016)`).
    - **Narrative Punchline Captions (`V2`):** When `Storyboard.md` highlights a specific narrative joke, archival flashback year, or callback (e.g., *"APRIL 2016 · FIRST DI2 RENTAL AT PRO CYCLE HIRE"*, *"€20 -> €30 inflation (+ he's in Alcúdia every Tuesday!)"*, or *"Saved by Nina's sharp eyes: Front disc brake pad on the ground!"*), generate clean glassmorphic pill overlays on `V2`.
- **Bilingual & Edition-Targeted Speech Cards — "Translation Is Always Primary" Law (`V3`):**
    - **Zero Redundant Cards When Speaking Edition Language Alone:** When on-camera dialogue is spoken in the video edition's primary language and no cross-language translation is requested, suppress redundant cards to keep the visual frame clean.
    - **"Translation Is Always Primary" Typography & Hierarchy (`agvs_core/vintage_cards.py`):** Whenever a speech card (`render_translation_subtitle_card`) is rendered for foreign or bilingual on-camera speech, the **target edition's translation line ALWAYS renders on top in large bold Deep Espresso (`#231F1D`)** with Cyrillic stroke-weight parity (`HelveticaNeue.ttc` Bold index `1` / `Arial Bold`), while any original-quote secondary line renders dimmer underneath; zero Unicode emojis are ever passed to Pillow (preventing `.notdef` tofu boxes), framed with a solid top Postmark Crimson accent bar (`#B83A2A`) on Warm Mediterranean Parchment (`#F4EFE6` / `#F2ECE1`).
    - **Sequential Multi-Sentence Speech Pagination:** Continuous on-camera dialogue (`> 95` chars / multi-sentence takes) automatically paginates via `paginate_speech_segments()` into `_p1.png`, `_p2.png`, etc. with word-proportional durations summing exactly to `dur_s`.
    - **Contiguous Zero-Dip Transition:** For contiguous speech cards on track `V3` (gap $\le 0.08\text{s}$), the engine automatically clamps durations, zeros out fade-out on the earlier card, and zeros out fade-in on the second card (`fade_out_s=0.0`, `fade_in_s=0.0`). The Warm Vintage Parchment box holds completely rock-solid on screen while the text cuts instantaneously.
    - **Hearing Accessibility Preservation:** Full word-for-word multilingual closed captions across all languages (`captions.en.srt`, `captions.ua.srt`, `captions.ru.srt`) remain multiplexed as soft subtitle streams into the MP4 container for viewers who enable CC.
- **Color & Monochrome Integrity:** Conform iPhone 15 Pro `BT.2020` HDR clips to `Rec.709` linear light. Never apply color LUTs or saturation adjustments to 1977+ black-and-white film scans.

### ARTICLE VII: DIRECT TIMELINE ASSEMBLY & MANDATORY PRE-RENDER FILMCRAFT GATE

No human editor wants to proofread hundreds of rows of numerical timecodes in a spreadsheet (`cut_table.md`) to imagine how a video feels. All timeline assembly is executed directly from `Storyboard.md` via FilmCraft:
1. **🛑 Mandatory Pre-Render Sanity Gate (NEVER Render MP4 Before FilmCraft Approval):** Always build `.fcproj` first (`build_timeline.py --project-dir ...` **without** `--render-export`), open it live in the FilmCraft GUI (`file.open` / port `9876`), and **STOP to let Alexander scrub and confirm timeline sanity** before ever running `filmcraft-cli export` / `--render-export`. Never burn GPU render time on an unreviewed cut!
2. **Conversational Adjustments:** Any pacing, trim, or audio adjustments are requested directly in chat (*"shorten the market scene by 2 seconds"*, *"boost Nina's voice"*, *"swap music track"*). The agent updates `timeline_spec.json`, rebuilds `.fcproj`, reloads it in FilmCraft, and only exports 4K MP4s once Alexander gives explicit sign-off.
3. **Cut Table Deprecated:** The intermediate `cut_table.md` file is fully deprecated in favor of direct timeline execution and real-time visual feedback.

### ARTICLE VIII: IMPERIAL UNITS DEFAULT, GPX WIDGETS, LOW-RES B-ROLL FRAMING & BROADCAST AUDIO MIX

- **Universal Edition Unit Law (Imperial Exclusively for EN, Metric for ALL Other Languages):**
    - **The Global Rationale:** Virtually every country outside the United States—and specifically all European nations (Spain, Germany, France, Italy, Ukraine, etc.) as well as Latin America and Asia—operates exclusively on the Metric system. Imperial units are completely foreign and disruptive to viewers listening in any language other than English.
    - **English Master Edition (`master_mp4`, `<project>.fcproj`):** Strictly uses **Imperial units (`mi`, `ft`, `mph`, `°F`)** for all on-screen telemetry HUDs, voice-over narrations, subtitle tracks, and primary video titles (tailored for US and UK/Commonwealth audiences). Zero on-screen metric clutter. (In multi-language YouTube descriptions, metric conversions are included in parentheses for international searchability, e.g., `21.5 mi (34.5 km)` and `531 ft (162 m)`).
    - **ANY and ALL Non-English Editions (`ES`, `DE`, `FR`, `IT`, `UA`, `RU`, etc. / `_<lang>.mp4`, `<project>_<lang>.fcproj`):** MUST strictly use **Metric units (`km`, `m`, `km/h`, `°C`)** across ALL modalities without exception:
        1. **Voice-Over Narration & Audio Synthesis:** Spoken numbers must always use kilometers (`kilómetros`, `Kilometer`, `kilomètres`, `кілометрів`, `километров`), meters, and metric speed/elevation. Spoken miles or feet are strictly prohibited in non-English voiceovers.
        2. **Subtitles & Caption Tracks (`.srt`):** All subtitle text and translations in non-English editions must display metric units only.
        3. **Visual Badges & Waypoint Cards (`V2`):** Contextual distances or altitudes (e.g., `COLL DE FÀMENIA (515 M)` instead of `1,690 FT`) must be in meters and kilometers.
        4. **Live Dynamic Telemetry HUD (`V4`):** Speed in `KM/H` (`КМ/Ч` / `КМ/ГОД`), elevation in meters (`M` / `М`), and power/heart rate. Zero Imperial abbreviations (`MPH`, `FT`).
        5. **Postcard Bookend Tickets (`V1`):** Route stats in metric (`71 КМ | 640 М ПОДЪЕМ` / `71 KM | 640 M ELEVATION`). Zero on-screen Imperial clutter.
- **Zero Burned-In Bottom Titles (`burned_in_titles: false` Default):**
    - Export master 4K MP4s with `--settings '{"burnCaptions": false}'` (keeping `C1` inside `.fcproj` disabled visually, used solely as timing metadata for `.srt` export). This guarantees 100% clean 4K video frames that never collide with YouTube's native CC subtitles on iPhone or desktop.
- **Direct-from-GPX Corner Route Map & Smoothed Telemetry HUD (`gpx_widgets.py`):**
    1. **GPX Corner Route Map (`V2`, top-right, `3.5s`):** Rendered directly from the `.gpx` track into a 4K transparent PNG (`map_01_*.png` .. `map_04_*.png`) showing the full route polyline, highlighted progress up to that scene, pulsing rider marker, and Imperial mileage/elevation header. Always time-shift corner maps clear of close-up mechanical/object stills so key details in the top-right corner remain unobstructed.
    2. **Smoothed Dynamic GPX Telemetry HUD (`V2`/`V3`, top-left, `auto` | `always` | `off`):** Compute road gradient over a **`>= 40 m` horizontal lookback window** (eliminating Garmin `0.2 m` barometric altimeter quantization spikes at low speeds) and power over a **3-second rolling average**.
        - **Activity-Aware Dynamic Speed Thresholds (`auto` Mode):**
            - **Cycling Rides (`cycling_ride`):** Turn HUD **ON** when 3-second rolling speed $> 2.0\text{ mph}$ ($3.2\text{ km/h}$).
            - **Running (`run`):** Turn HUD **ON** when 3-second rolling speed $> 1.5\text{ mph}$ ($2.4\text{ km/h}$).
            - **Hiking & Walking (`hike_outdoor`):** Turn HUD **ON** when 3-second rolling speed $> 0.8\text{ mph}$ ($1.3\text{ km/h}$) so steep uphill mountain climbs are never mistakenly classified as stopped!
        - **Static Scene Suppression & Cut-Boundary Termination (`auto` Mode):**
            - Automatically turn the Telemetry HUD **OFF** for still photos (`.jpg`, `.png`, `.heic`) and stationary video scenes (café stops, bakery counters, terrace chats, gate stops, mechanical adjustments, where speed falls below the activity threshold), keeping the frame clean during conversational and still moments.
            - **Strict Cut-Boundary Termination Law:** Whenever a riding cut transitions to a stationary bike/cockpit shot (e.g., stopping at Mortitx or looking down at the physical Garmin head unit), the simulated Live Telemetry HUD (`live_telemetry_hud`) **MUST terminate precisely at the cut boundary** (`start_s + dur_s == cut_transition_s`). Simulated speed/power overlays must NEVER overflow into a stationary cut where the rider's real Garmin computer is visible displaying 0.0 mph / 0 watts!
        - **Narrative / Historical / Lifestyle Story HUD Suppression Law (`hud_mode: "off"` Default for Non-Performance Stories):**
            - When a project's Controlling Idea (`Сверхзадача`) is a **narrative, historical, memory-driven, or lifestyle story** (e.g., exploring the history behind everyday places, visiting friends, errands, lunch, and swimming, rather than chasing watts/KOMs/climbing intervals), **default `hud_mode` to `"off"`** so speed/wattage telemetry never clutters historic facades, dry-stone lanes, or scenic storytelling.
        - **Manual Override & Conversational Trial/Error:** `gpx_telemetry_hud` can be explicitly set to `always` (display on all video clips) or `off` (hide completely) in the `/build-timeline` alignment card. Because telemetry pacing is inherently aesthetic, visual review happens by scrubbing FilmCraft or watching the rendered MP4; if a specific scene feels unnatural, Alexander can refine it conversationally in chat (*"turn HUD off on Camí Vell"* or *"toggle HUD to always"*).
- **Partial-Screen Picture-in-Picture Card for Low-Resolution B-Roll (`low_res_broll_mode: "pip_card"`):**
    - Never stretch sub-1080p clips (such as `1024x576` WhatsApp/smartphone videos like `2026-11-02_Zumba.mp4`) to full `3840x2160`. Instead, pre-composite them via `ffmpeg` at **62% scale (`2368x1332`) with an `8px` warm white border** centered over a blurred, softly darkened (`boxblur=16:2, brightness=-0.12`) 4K contextual photo on `V1`.
- **Broadcast-Balanced 4-Track Audio Architecture (`-16 LUFS` Speech/VO vs. `-21.5..-24.5 dB` Midrange-Ducked Music):**
    - **Same-Language Live Dialogue Honor Law (`edition_lang == clip_dialog_lang`):**
        - **Voice-Over narration (`A4`) MUST NEVER cover or overpower live on-camera dialogue (`A1`) spoken in the SAME language!**
        - Specifically: the **English (`EN`)** track must honor live English speaking sections on `A1` (suppressing or shifting `EN` VO clear of the live English speech); the **Russian (`RU`)** track must honor live Russian speaking sections on `A1` (suppressing `RU` VO over all cuts containing live Russian dialogue and playing `RU` VO only over silent stills or non-speech ambient sections); and the **Ukrainian (`UA`)** track must honor live Ukrainian speaking sections on `A1`.
        - Conversely, when the edition language is **different** from the clip's live speech language (`edition_lang != clip_dialog_lang`, e.g., `EN` or `UA` VO translating a clip with `RU` camera speech), duck `A1` by **`-12.0 dB`** (down to `-24.0 dB` fader / `-42 dB` mean) during active VO cues so foreign-language camera chatter never competes with the narrator.
    - **`A1` (Live Camera Speech & B-Roll Audio):**
        - **Natural `1.00x` Speech Speed & `1:1 V1 == A1` Lip-Sync Law:** NEVER apply `atempo > 1.0` or internal pause-stripping (`silenceremove=...:stop_periods=-1`) to human speech on `A1` or Voice-Over on `A4`! All live camera speech and synthesized voice-over MUST play at **100% natural `1.00x` speed**. Size each speaking visual cut (`V1`) to match the exact `1.00x` duration of its complete spoken sentence (`src_in` to `src_in + dur`), keeping `V1` and `A1` locked 1:1 so lip movement and camera motion (e.g., tilting down to reveal a coffee cup and croissant as they are named) stay in 100% frame-and-sample sync, without overflowing into the next scene.
        - **Mandatory `1.5s–2.0s` Opening Music Intro Law:** Never start a video abruptly with voice-over at `0.0s–0.2s`. Always let the opening visual and background music (`A2`) establish the scene for **`1.5s–2.0s`** before the first `A4` Voice-Over cue begins (in both `.fcproj` and rendered `.mp4` stems).
        - **Sample-Accurate `atrim` & Post-Mix `dynaudnorm` Rule:** When trimming live dialogue from HEVC `.MOV` files in `ffmpeg`, always use sample-accurate `atrim=start=...:end=...,asetpts=PTS-STARTPTS` (rather than input `-ss` before `-i`, which snaps to video keyframes and shifts audio by up to `1.5s`), and apply `dynaudnorm=f=150:g=7:p=0.90` **once on the combined full-length dialogue stem** after `amix` (never inside short per-clip `atrim` chains where `dynaudnorm`'s multi-frame lookahead buffer can swallow phrase tails).
        - **Camera Speech Normalization (`live_dialog_boost: "auto"`):** Normalize featured live spoken dialog segments (`highpass=f=120, lowpass=f=7500, dynaudnorm=f=150:g=7:p=0.90`) to hit **`-16.0 dB` mean / `-1.0 dB` peak** and strip any overlapping `A3` sound effects so live conversation is crystal clear.
        - **PiP B-Roll Music Taming:** Set smartphone B-roll music (e.g., live Zumba audio) to **`-6.5 dB`** (`-30 dB` mean) with `0.6s` fades so it never overpowers the mix.
    - **`A2` (Multi-Phase Background Music — `180 Hz` Midrange RMS Calibration, Mellow Offset & Smooth Keyframed Ducking):**
        - Because upbeat/funk/retro tracks are often mastered hot (`-10.8 dB` to `-12.6 dB` raw RMS, `-0.5 dB` peak) while chillhop/acoustic tracks contain heavy sub-bass (50–120 Hz) that inflates broadband RMS while sounding quiet on phone speakers, **always measure BGM loudness behind a 4th-order `180 Hz` high-pass filter (`highpass=f=180,highpass=f=180`) and enforce the Mandatory Peak Headroom Guard**.
        - **Mandatory Peak Headroom Guard (Ceiling $\le -1.5\text{ dBFS}$):** Cap `max_allowed_gain_db = -1.5 - raw_max_db` (or `-2.0 - raw_max_db` when `+2.0 dB` presence EQ is applied) so music clips NEVER clip digital full scale (`0 dBFS`).
        - Set baseline fader gains via `calculate_bgm_gains()` in `agvs_core/audio_dsp.py`:
            - **Riding / Open Visual Swells (`target_riding_db` & `max_riding_lufs`):** **`-15.5 to -18.0 dB`** midrange RMS (`-16.0 dB` for mellow/chillhop tracks; `-17.5 dB` for standard tracks), strictly capped at **`-15.5 LUFS`** integrated so brickwall-mastered `-8..-11 LUFS` tracks never overpower the mix.
            - **Ducked Under VO / Live Speech (`duck_amount_db = 11.5` & `max_ducked_lufs = -26.5`):** Smooth keyframed **`11.5 dB` duck** to **`~ -27.0 LUFS`** under `-16 LUFS` narration—delivering `>= 10.5 LU` broadcast story separation while keeping warm musical presence on speakers.
        - **Mellow/Chillhop Presence EQ (`1800 Hz` Definition):**
            - If the BGM filename or path contains mellow keywords (`chillhop`, `chill`, `ambient`, `warm`, `scenic`, `lofi`) or BPM `< 95`:
                - Add a gentle `+1.5 dB` midrange target offset and presence EQ (`equalizer=f=1800:t=q:w=1.2:g=2.0`) on the A2 chain so soft piano/guitar/synth melodies cut cleanly through mobile and laptop speakers without boosting sub-bass kicks into distortion.
    - **`A3` (Contextual Sound Effects):** Keep subtle (`-10 dB`), align by `catalog.json` `peak_ms`, and never place SFX over spoken dialogue.
    - **`A4` (Single-Pass Studio-Dry Anti-Reverb Law, Standard Google TTS Voice & `-16 LUFS` Normalization):**
        - **Standard Google TTS Over Voice Cloning:** Always use clean standard/prompted Google Gemini TTS voices (`Charon` / prompted baritone persona via `$GEMINI_VOICE_ID`) across `EN`, `UA`, and `RU`. Never attempt `type: "replicated"` voice cloning unless explicitly requested (voice cloning produced muffled/inaudible audio and burned API credits). Never hardcode raw `voice_*` IDs into tracked Git files; resolve `$GEMINI_VOICE_ID` via `agvs_core.config.get_gemini_voice_id()`.
        - **Single-Pass Guard (`agvs_studio_dry=1`):** Apply the Studio-Dry Anti-Reverb chain (`highpass=f=95`, `380 Hz`/`600 Hz` room-boxiness notches, `afftdn=nr=12:nf=-38:tn=1`, `agate`, and `loudnorm=I=-16:TP=-1.5:LRA=9`) **strictly once**—never double-filtering already-normalized VO WAVs during timeline pacing!

### ARTICLE IX: YOUTUBE PUBLISHING MODES (`en_only` / `option_a` / `option_b`), ISO `ua` STANDARD & COMPOSITE THUMBNAILS

- **Strict ISO Country Code `ua` for Ukraine:**
    - Always use **`ua`** (`UA`) across all local filenames (`voiceover_ua_part1.wav`, `full_audio_ua.m4a`, `captions.ua.srt`, `*_UA.mp4`) and JSON keys (`localizations.ua`), mapping `"ua" -> "uk"` exclusively inside `upload_youtube_api.py` when calling the YouTube Data API v3 wire format.
- **Mallorca Phonetic Toponym Rule (`ll` Before a Vowel $\rightarrow$ `й` / `є`; Pre-Consonantal `ll` in `Valldemossa` $\rightarrow$ `Валдемоса`):**
    - On Mallorca, intervocalic and word-initial `ll` before a vowel (`V + ll + V` or `# + ll + V`) is pronounced `[j]` (*yeísmo* / *ieisme*). In all Russian (`ru`) and Ukrainian (`ua`) titles, descriptions, subtitles, and voice-over scripts, ALWAYS transcribe `ll` before a vowel phonetically without `"л"`:
        - **Mallorca** $\rightarrow$ RU: **`Майорка`** | UA: **`Майорка`** *(never «Мальорка»)*
        - **Pollença / Port de Pollença / Badia de Pollença** $\rightarrow$ RU: **`Пойенса` / `Порт-де-Пойенса` / `Бадия-де-Пойенса`** (`через Пойенсу`, `залива Пойенса`) | UA: **`Поєнса` / `Порт-де-Поєнса` / `Бадія-де-Поєнса`** (`через Поєнсу`, `затоки Поєнса`) *(never «Польенса» / «Польєнса»)*
        - **Sóller / Port de Sóller** $\rightarrow$ RU: **`Сойер` / `Порт-де-Сойер`** | UA: **`Соєр` / `Порт-де-Соєр`**
        - **Lluc / Llucmajor / Cala Millor** $\rightarrow$ RU: **`Йук` / `Йукмайор` / `Кала-Мийор`** | UA: **`Йук` / `Йукмайор` / `Кала-Мійор`**
        - **Búger (`[ˈbu.ʒə]` — Catalan/Mallorquí soft `"zh"` + muted final `-r`):**
            - **EN Spoken TTS:** Pass **`Boo-zhe`** to TTS so it voices `[ˈbu.ʒə]` (never hard English `"Boo-ger"` or Spanish `"Boo-her"`), while keeping **`Búger`** in `.srt` subtitles and metadata.
            - **RU & UA Written + Spoken:** **`Буже`** (indeclinable, e.g., *«в Буже»*, never *«Бугер»* / *«Буґер»*).
    - **Exception — Pre-Consonantal `ll` (`Valldemossa` = *Vall* + *de Mossa*):** Because `ll` immediately precedes the consonant `d`, Spanish/English speakers reduce it to a clean `[l]`. Write and voice **`Валдемоса`** (or **`Вальдемоса`**, never *«Вайдемосса»*).
- **Zero-Plaintext-Secrets & Biometric Voice Security Environment Setup:**
    - Set `GEMINI_API_KEY`, `GEMINI_VOICE_ID` (Alexander's secret replicated voice ID), `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `FLICKR_API_KEY` via Alexander's 1Password `direnv-manager` convention (`envvar:*` in vault `Private`) or a local git-ignored `.env` file. Antigravity and child processes inherit them automatically. Once authorized, `~/.config/antigravity_youtube/token.json` caches the OAuth refresh token for YouTube API calls. Default video visibility to **`unlisted`** so the creator can preview, test comments/language switchers, and share the link without public feed spam. Never commit API keys, tokens, or custom voice IDs to Git!
- **Primary Voice-Over Language & Target Audience Alignment:**
    - **Default Language Rule:** The primary audio track (voice-over language) defaults to the **predominant language spoken in the raw video clips** (e.g. Ukrainian/Russian for candid conversations with Nina/friends, English for English-spoken group rides or solo cycling).
    - **Target Audience Override:** If the intended target audience requires a different language (e.g. English for US cycling teammates, Silicon Valley tech peers, or broader YouTube reach), Alexander or `Storyboard.md` may set `primary_audio_language: "en"`.
    - **Subtitle Guarantee:** Regardless of the primary voice-over language, all three subtitle tracks (`EN`, `UA`, `RU`) are always generated as native `.srt` files so viewers across all languages are fully supported via YouTube CC.
    - **Pre-Assembly Alignment Check (In-Chat Alignment Card):** The agent must never silently make core creative assumptions. When running `/build-timeline`, the agent presents an interactive in-chat alignment card (`ask_question`, one question per turn) to confirm: (1) Primary voice-over language (defaulting to spoken language in video), (2) Background music selection with 10s audio previews via Mac speaker (`afplay -t 10`) using clear `▶️ Listen` vs `✅ Select` choices, and (3) Publishing mode (`option_a` default, unlisted), prompting Alexander for confirmation before launching audio synthesis and timeline assembly.
- **Three Selectable Localization & Publishing Modes (`publishing_mode` in `Storyboard.md` Section 5):**
    - **MANDATORY APPROVAL GATE:** Video uploads to YouTube MUST NEVER occur automatically on auto-pilot. All pipelines (`/build-timeline`, `/publish-youtube`) must pause after export and metadata generation to ask for explicit user confirmation before uploading.
    1. **`option_a` (Recommended Studio Default — Single Video + Multilingual Subtitles & Localized Metadata):** Uploads a single 4K master (`unlisted`) with `captions.en.srt`, `captions.ua.srt`, and `captions.ru.srt` (matching the spoken voice-over and live dialog word-for-word), sets YouTube native `localizations` (`uk` and `ru`), and embeds `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` story summaries inside the main description (omitting duplicate `00:00` timestamp blocks in the inline sections so YouTube's chapter parser always keeps the English chapter titles). Concentrates all views onto a single video release while serving Ukrainian and Russian friends seamlessly via YouTube's native CC button.
    2. **`en_only`:** Uploads only the primary English 4K master (`unlisted`) with `captions.en.srt`.
    3. **`option_b` (Special Occasions / Major Milestones — 3 Voiced Editions):**
        - Generates balanced stereo mixes `full_audio_en.m4a`, `full_audio_ua.m4a`, and `full_audio_ru.m4a`, and remuxes `_UA.mp4` and `_RU.mp4` in **`0.2 seconds`** via `ffmpeg -c:v copy` (zero video re-encoding!).
        - Uploads `_UA.mp4` and `_RU.mp4` as **Unlisted** (avoiding channel feed clutter), automatically embeds their clickable links (`🔊 Повна версія з українською озвучкою` / `🔊 Полная версия с русской озвучкой`) at the top of the `🇺🇦` / `🇷🇺` sections in the **Unlisted** English master description, and posts a pinned language switcher comment on the English master.
        - *Usage Guidance:* Reserve `option_b` for multi-day family milestones or trips where localized audio is genuinely requested; default everyday cycling and excursion vlogs to `option_a`.
- **YouTube Studio Composite Thumbnail Standard (`thumbnail.mode: "composite_ai"` — Localized per Edition):**
    - Co-design a high-impact 1920×1080 thumbnail in Section 5 of `Storyboard.md` combining: (1) a softly blurred scenic background + sharp hero portrait on the left, (2) a white-outlined sticker cutout of the key story prop/action on the right, and (3) a bold 3–4 word yellow-and-white headline across the top (`headline_text` for `thumbnail.jpg`, plus localized `headline_text_ua` $\rightarrow$ `thumbnail_ua.jpg` and `headline_text_ru` $\rightarrow$ `thumbnail_ru.jpg` for `option_b` editions).

### ARTICLE X: FLICKR PUBLISHING & RUSSIAN EDITION STANDARD (`_RU.mp4`)

- **Bypassing Regional YouTube Blocks for Family & Classmates:**
    - YouTube is heavily throttled or blocked in Russia and occupied Crimea. Family members (such as Nina's brother and Alexander's sister in Sevastopol) and former Institute classmates on WhatsApp cannot easily watch YouTube releases, but have unrestricted access to Alexander's **Flickr feed (`apkom`)** and direct WhatsApp video sharing.
- **Metric Telemetry HUD & 100% Localized Visual Card Law for Russian Editions:**
    - All Russian editions (`_RU.mp4`) and Russian project files (`<project>_RU.fcproj`) **MUST strictly use the Metric system** on track `V4` (Live Telemetry HUD):
        - **Speed:** `КМ/Ч` (km/h) with label `СКОРОСТЬ` (`spd_mph * 1.609344`)
        - **Power:** `ВАТТ` (watts) with label `МОЩНОСТЬ`
        - **Heart Rate:** `УД/МИН` (bpm) with label `ПУЛЬС`
        - **Grade & Elevation:** `+X.X% XXX М` (meters) with label `УКЛОН` (`ele_ft * 0.3048`)
        - Zero English abbreviations (`MPH`, `WATTS`, `BPM`, `FT`) on the Russian edition HUD.
    - **100% Localized Visual Cards & Signature Bookends Law:**
        - **Track `V2` (Character, Flashback & Stat Cards):** All on-screen graphical cards (`badge_*.png`) must be rendered in Russian (`badge_*_ru.png`) using Cyrillic font parity (`HelveticaNeue Bold` / `Arial Bold`). Any contextual altitudes or distances mentioned on cards must be converted to metric (e.g., `ВИНОДЕЛЬНЯ MORTITX (400 М)` instead of `1,300 FT`).
        - **Track `V3` (Translation Dialogue Cards):** Follows the single-language uncluttered subtitle standard: only render a card when on-camera speech is in a foreign language (showing only the Russian translation), and render ZERO cards when speech is already in Russian.
        - **Track `V1` Bookends:** Opening postcard and closing credits bookends (`bookend_intro_4K_RU.mp4`, `bookend_outro_4K_RU.mp4`) must be compiled with Russian route descriptions, cast credits, Cyrillic handwriting Chin text (`«Жаль, что вас здесь нет! — AGVS»`), and metric ticket strips (`56.6 КМ | 503 М ПОДЪЕМ`).
    - The studio automatically compiles and links parallel assets:
        - **Master EN (`<project>.fcproj`):** `live_hud/` (Imperial) + English badges + English bookends + English VO on `A4`.
        - **Russian Edition (`<project>_RU.fcproj`):** `live_hud_ru/` (Metric) + Russian badges (`_ru.png`) + Russian bookends (`_RU.mp4`) + Russian VO on `A5`.
- **Two Clean 4K UHD Edition Export Modes (`edition_visual_mode` in `agvs_core/timeline_builder.py` — Zero `-f concat` Splicing):**
    - Never splice `libx264`/`libx265` bookends onto a `filmcraft-cli` VideoToolbox export via `ffmpeg -f concat -c:v copy` (mismatched `tbn`, SPS/PPS extradata, and non-IDR cuts cause QuickTime/YouTube glitches), and **never downscale `_RU.mp4` to `1080p` during timeline build**:
        1. **`"universal_4k_remux"` (Default — `0.2s` Lossless Copy):** Master 4K (`3840x2160`) renders once with universal AGVS bookends + bilingual cards; `_UA.mp4` and `_RU.mp4` mux `full_audio_{ua,ru}.m4a` onto the untouched 4K video stream in `0.2s` via `ffmpeg -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy`.
        2. **`"localized_4k_render"` (Opt-In when `live_hud_ru/` or `_4K_RU.mp4` bookends are active):** Renders `<project>_RU.fcproj` directly through `filmcraft-cli` at full **`4K UHD` (`3840x2160`)**, then multiplexes `full_audio_ru.m4a` and `.srt` tracks.
    - This guarantees Alexander always has a glitch-free 4K Russian-voiced video ready for instant upload to Flickr or WhatsApp.
- **Flickr 1 GB Ceiling & Auto-1080p Transcode Standard:**
    - Flickr enforces a strict 1,000,000,000 byte (1 GB) upload ceiling and abruptly drops the TCP connection (`BrokenPipeError`) if a file exceeds it.
    - Because 4K UHD masters at 50 Mbps frequently exceed 1 GB, `/publish-flickr` automatically checks `video_path.stat().st_size`. If the file exceeds 980 MB, it automatically produces a high-bitrate 1080p copy (`scale=1920:1080`, 14 Mbps via `h264_videotoolbox`, ~300 MB) with losslessly copied audio (`-c:a copy`).
    - Since Flickr compresses and streams all video playback in 1080p anyway, this upload is visually indistinguishable, 100% compliant with Flickr ceilings, and uploads 3x faster.
- **Flickr Metadata Package (One-Click Upload via Web or Lightroom Publishing Service):**
    - On every release, `/publish-youtube` and `/build-timeline` output a dedicated **Flickr Publishing Box** (in chat and appended to `facebook_promo.md`) containing:
        - **Title:** `YYYY-MM-DD · <Russian Title> (<mi> / <km>)` (matching Alexander's Flickr convention, e.g. `2026-10-27 · Вместо группы: выпечка в Буже и «VIP»-кофе (40.1 мили / 64.5 км)`).
        - **Description:** Clean Russian story description highlighting landmarks, cafe stops, and route lore.
        - **Tags:** `Mallorca, cycling, roadbike, BleeqUP, video, <Village>` (comma-separated for one-click Flickr tagging).
        - **Recommended Album:** e.g., `2026 Fall Mallorca Cycling` in Lightroom Publishing Service / Flickr.

### ARTICLE XI: SOCIAL MEDIA & COMMUNITY PROMOTION (FACEBOOK "MALLORCA CYCLING" STANDARD)

- **The Mallorca Cycling Group Ecosystem (73.4K Members — Rules & Culture):**
    - **Strict Anti-Advertising Rule:** The group rule explicitly states: *"PLEASE DON'T ADVERTISE ANYTHING HERE. Set up for people that love cycling and live in or visit Mallorca."* Commercial promotion, spammy channel promotion, or generic video dumps get flagged or ignored.
    - **Community Currency = Authentic Local Road Knowledge & Route Lore:** Posts that generate massive engagement (e.g., lesser-known climbs like Coll de Sant Llorenç / Cala Tuent, hotel and seasonal closures, bakery stops, quiet rural *camís*) share **practical road intel, surface conditions, cafe/bakery gems, and seasonal reality (morning temperature, wind, autumn calm)**.
    - **Conversational Peer Tone:** Write as a fellow rider based on the island sharing a discovery or a good ride, never as a self-promoting influencer. Ask an engaging question at the end (e.g., favorite cafe stop in the area, hidden alternative lanes).
    - **Facebook Algorithm Best Practice:** Attach 1–3 authentic photos (e.g., the bakery display, the village fountain, the bike at the cafe), share the route story with distance/elevation, and put the YouTube link in the **First Comment** (`link in first comment 👇`) so Facebook doesn't penalize post reach.
- **Dedicated FB Promo Generator Option 4 (`mallorca_community`):**
    - Every cycling project located on Mallorca (`GPX` coordinates in Mallorca bounding box) MUST generate a dedicated **Option 4: Mallorca Cycling Facebook Group Edition** in `facebook_promo.md` alongside Options 1–3.

### ARTICLE XII: NATIVE AI CREATIVE ARTIFACTS & LIVING MEMORIES (ZERO BLEEQUP DEPENDENCY)

- **100% Independence from Third-Party AI Tracking (`generate_ai_creative_assets.py`):**
    - Alexander never needs to enable BleeqUP's proprietary AI tracking feature or rely on watermarked third-party app exports (`BleeqUp_Motion_*.jpg` / `BleeqUp_Remix_*_ai.MP4`).
    - All artistic stylizations, painting-to-reality morphs, 3rd-person FPV drone swoops, and living archival memories are synthesized **100% natively in-studio** from raw camera photos/videos (`IMG_*`, `VIDEO_*`) and Lightroom archival stills (`P110*.jpg`) via `agvs_core.ai_creative` (`.agents/skills/storyboard/scripts/generate_ai_creative_assets.py`) using **`gemini-3-pro-image`** (`2K 16:9` keyframe synthesis), **`gemini-omni-1.2-flash`** (`1080p 16:9` motion & first-to-last-frame transitions via native File API), and **`gemini-4-carbon`** vision analysis.
- **Three Signature Studio AI Creative Modes:**
    1. **`paint_morph` (Artistic Painting $\leftrightarrow$ Reality Morph):**
        - Synthesizes a gallery-grade `16:9` artistic twin (`impasto_oil`, `watercolor`, or `anime`) directly from any raw photo or video frame via `gemini-3-pro-image-preview`, then uses `gemini-omni-1.1-flash` (`--first-frame` + `--last-frame`) to melt the living painting seamlessly into the real camera shot (for cold opens) or freeze reality into a painting (for poetic endings).
    2. **`fpv_drone` (Native 3rd-Person Multi-POV Tracking — Zero Hardcoding, Per-Ride Photo Reference):**
        - Because Alexander's cycling kit and bicycle change from ride to ride (e.g., rental bikes in Mallorca vs California road bikes, or different jerseys/vests each day), **never hardcode a rider or bike reference**.
        - Instead, mirror and surpass the BleeqUP workflow using the **ride-specific photo of Alexander with his bike** taken during or after that day's ride (`--rider-ref <IMG_*.jpg>`):
            1. **Select Source Video Clip:** Pick a raw POV road clip (`--source <VIDEO_*.MP4> --timestamp <sec>`).
            2. **Select Ride-Specific Rider + Bike Photo:** Pass that day's photo of Alexander with his bike (`--rider-ref <IMG_*.jpg>`). `generate_ai_creative_assets.py` dynamically extracts the visual spec of that day's kit & bike via `gemini-2.5-flash` and locks the visual identity via `gemini-3-pro-image-preview` + `gemini-omni-1.1-flash` (`<IMAGE_REF_0>`).
            3. **Choose from 4 POV Templates or Custom Prompt (`--viewpoint`):**
                - `crane_above_to_behind` (High Drone Swoop -> Low Rear-3/4 Chase)
                - `side_tracking` (Pro-Peloton Low Motorcycle Side-Profile Tracking)
                - `low_rear_chase` (Close Pro-Peloton Rear-3/4 Follow)
                - `front_lead` (Low Front-3/4 Lead Camera Looking Back at Rider)
                - `custom` (Custom camera trajectory via `--prompt "..."`)
    3. **`living_memory` (Living Archival Photograph):**
        - Takes a historical Lightroom photograph (`P110*.jpg`, 1977+ B&W film scans, or 1980s university photos) and animates a warm, subtle `5.0s` living memory (e.g., Alexander and Nina turning to each other and clinking wine glasses at Bar Nàutica in 2017) via `gemini-omni-1.1-flash`.
        - **Audio Hygiene Rule for AI Clips:** When weaving a `living_memory`, `paint_morph`, or `fpv_drone` clip into the timeline under `A4` Voice-Over, suppress any random AI-generated speech on `A1` while optionally preserving subtle ambient sound or crisp spot SFX (such as wine glasses clinking or ocean waves) at `-12 dB`.
- **Interactive Co-Design in `/storyboard` & `/build-timeline`:**
    - During `/storyboard` co-design, the agent proposes 2–3 story-driven **AI Creative Artifact Candidates** (`ai_creative_artifacts` in `Storyboard.md` Section 5/6) and presents an interactive choice (`ask_question`) allowing Alexander to pick which AI artifacts to generate and weave into the timeline.

### ARTICLE XIII: LONG-CLIP SEMANTIC DECOMPOSITION & LANDMARK SYNCHRONIZATION LAW

- **The Long-Clip Blindness Prevention Standard ($\ge 12$s):**
    - Clips longer than 12 seconds must never be treated as monolithic B-roll blocks, and must **never** default to arbitrary `src_in: 0.0` or `5.0`.
    - Long video clips often contain critical micro-events, head-turns, roadside interactions, or staged multi-pass camera actions (e.g. riding away, doing a 180° turn, and passing the camera) deep into the file (e.g. at 40s or 50s).
    - **Automated Contact-Strip Semantic Indexing (`extract_video_subclips.py`):**
        - During Stage 0 Ingestion (`ingest_and_sync_media.py`), every video clip $\ge 12.0$s automatically has its 6-frame contact strip (`_strip.jpg`) analyzed via Gemini 3.8 Flash Vision into structured `sub_events` and `landmarks` with exact `[start_s, end_s]` timestamps.
        - Results are permanently cached in `.proxies/<stem>_subclips.json`, written into `project_manifest.json` under each media item, and formatted directly into `Storyboard.md` under Section 3 (Chronological Media & GPS Log).
- **The Landmark Dwell & Narrative Synchronization Rule:**
    - When spoken narration, on-screen subtitles, or scene descriptions reference a specific landmark, hotel, restaurant, ruin, or historical place (e.g. *Hotel Pollentia*, *Restaurante Miramar*, *Muralles d'Alcúdia*, *S'Àmfora*):
        1. The corresponding video cut's source interval `[src_in, src_in + dur]` **MUST encompass the landmark's indexed timestamp range**.
        2. The landmark must enjoy **at least 3.0 to 4.0 seconds of clear visual dwell time** on screen so the viewer can absorb its presence and read its architectural facade/signage.
        3. Never cut away before the landmark appears!
        4. If the landmark is set against complex scenery, accompany it with an unmistakable directional overlay badge (top-left or bottom-left) explicitly identifying its name, founding year/era, and significance.
- **Pre-Flight Timeline Synchronization Guard (`build_timeline.py`):**
    - `build_timeline.py` performs a mandatory pre-flight inspection comparing cut durations and voiceover cues against the landmark index in `project_manifest.json`. If a cut claims to showcase a landmark but terminates prior to its appearance, the build raises an immediate pre-flight desync warning.

### ARTICLE XIV: GPX ROUTE MONOTONICITY, BLEEQUP PHYSICAL CONTINUITY & CALIBRATION EXCLUSION LAW

- **GPX Route Milepost Monotonicity (`build_timeline.py` Pre-Flight):**
    - A ride's `.gpx` file defines the ground-truth spatial and chronological sequence of places visited (`distance_mi` / `distance_km` from `0.0` to finish).
    - Every non-flashback timeline cut captured within the GPX ride window (`editorial.in_gpx_ride_window == True`) **MUST progress monotonically forward along the GPX route** (within a `0.15 km` / `150m` stationary-stop turnaround tolerance) and in monotonically non-decreasing manifest capture order. Any out-of-order place or backward GPX jump immediately halts `build_timeline.py` with a `GPX Route Sequence Violation` error.
- **BleeqUP Physical Overlap Assertion & Low-Battery Offload Rule (`ranger-sync` + `ingest_and_sync_media.py`):**
    - `ranger-sync` enforces `ts[i+1] - ts[i] >= clip_duration[i]` across all BleeqUP captures. If two clips overlap or start milliseconds apart (e.g., `91ms` app batch-remux or depleted-battery Camera SoC RTC brownout), `ranger-sync apply` aborts with exit code `2` (`CRITICAL: Non-physical BleeqUP timestamp overlap detected`), and `ingest_and_sync_media.py` halts immediately rather than writing a poisoned manifest.
    - **Field Rule:** Whenever the glasses drop near empty on a ride, plug them into external USB power before opening the BleeqUP iOS app, and never install a firmware update until all clips are offloaded and verified on Mac.
- **Calibration Clock Photo Exclusion (`bigclock.app`):**
    - Reference calibration photos shot solely to verify camera clock drift (e.g., `bigclock.app`, Garmin clock screen, `calibration_clock_only: true`) are automatically flagged `"exclude_from_timeline": true` during ingest and strictly blocked from appearing as timeline cuts in `build_timeline.py`.


