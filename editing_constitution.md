## UNIVERSAL EDITING CONSTITUTION (editing_constitution.md)

**System:** Google Antigravity Desktop App (Gemini 3.8 Flash + Gemini 4 Argon)  
**Studio Root:** `./`  
**Media Tiers:** `~/Movies/YEAR/YYYY-MM-DD_<name>/` (Hot) & `/Volumes/Crucial-4T/Movies/YEAR/` (Cold Archive)  
**Curated Music Pool:** `03_Audio_Library/01_Curated_BGM/` (YouTube Audio Library + `creatormix.com`)  
**Target NLEs:** FilmCraft MCP (`127.0.0.1:9876`) & DaVinci Resolve Studio 21.1 MCP

### ARTICLE I: STAGE 0 COLLABORATIVE Storyboard.md & AUTOMATIC MEMORY HARVESTING

- **Stage 0 — `Storyboard.md` First:**
    - Every project folder must have a **`Storyboard.md`** file (synced to `04_Project_Catalog/YEAR/<project_name>/Storyboard.md`).
    - If `Storyboard.md` is missing or is an unpopulated skeleton, the agent MUST first run `ingest_and_sync_media.py` (which converts `.HEIC` to `.jpg`, extracts `.proxies/` video thumbnails, and reads EXIF/QuickTime GPS/timestamps), visually inspect the proxy thumbnails, and populate `Storyboard.md` with:
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
        3. Builds the 4-track timeline in FilmCraft MCP, exports clean 4K `.mp4` to `~/Movies/Exports/YEAR/`, and generates `facebook_promo.md` and metadata package.
        4. Invites human visual review directly via FilmCraft GUI playback (completely replacing tedious `cut_table.md` spreadsheets).
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

### ARTICLE V: CURATED FREE MUSIC POOL (`03_Audio_Library/01_Curated_BGM/`), MIXING & TRACK SWAPPING

- **Track Assignment Standard:**
    - `V1`: Primary Video & Background Blur Fill Track
    - `V2`: Foreground Uncropped Stills, Archival B-Roll & Storyboard Caption Overlays
    - `A1`: Native Camera Audio (Tire roll, freewheel clicks, speech, market punchlines, toasts, café banter)
    - `A2`: Dedicated Background Music Track (`03_Audio_Library/01_Curated_BGM/`) — **kept completely separate on `A2` for one-command swapping (`/swap-music`)**
    - `A3`: Subtle Contextual Sound Effects (`03_Audio_Library/02_SFX/catalog.json` — 209 Brehov cinematic WAVs across `01_Whooshes_Soft` through `19_Ambient_Pads`, aligned by `peak_ms` so the sound peak lands on the exact frame of motion/caption reveal)
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
- **Gain, Ducking & Fade Matrix (`gainDb` — Reified from `Music for Video Workflow`):**
    - **Music Baseline (`A2`) over Native Riding / Ambient Audio (`A1` active):** **`-14.0 dB` to `-16.0 dB`** so natural bike soundscapes (tire buzz, freewheel clicks) sit naturally against the music.
    - **Music Baseline (`A2`) when Native Audio is Muted (Pure Slideshows / Silent B-Roll):** **`-10.0 dB` to `-12.0 dB`**.
    - **Speech & Notable Sound Ducking (`A2`):** When native speech (market banter, café talk, party toasts) or a notable sound occurs on `A1`, duck `A2` by an additional **`-4.0 dB` to `-6.0 dB`** (bringing `A2` to **`-18.0 dB` to `-20.0 dB`**) with a `0.4s` ramp.
    - **Native BleeqUP Audio (`A1`) when GPX Speed $< 40\text{ km/h}$:** **`-6.0 dB`** (natural road/freehub presence).
    - **Native BleeqUP Audio (`A1`) when GPX Speed $\ge 40\text{ km/h}$:** **`-24.0 dB` or Mute** (mandatory wind-buffeting suppression).
    - **Fades on `A2` & Synchronized Outro Fade Law:**
        - **Head:** `1.0s` to `1.5s` fade-in (`curve=hsin`) starting with clip motion.
        - **Mandatory Synchronized Outro Audio Fade Law:** Whenever a sequence ends with a visual `Dip to Black` (typically `1.5s–2.0s`), the audio mix MUST NEVER cut off abruptly. The master audio output (`[fullout]`) and background music (`A2`) MUST execute a synchronized **`2.0s–2.5s` Half-Sine outro fade (`afade=t=out:st=<TOTAL_DUR - FADE_DUR>:d=<FADE_DUR>:curve=hsin`)** reaching complete silence (`-infinity dB`) exactly as the video hits black. In `.fcproj`, track `A2` MUST include an `exponential_fade` or `constant_power` transition (`from: Some(clip.id), to: None, align: "EndAtCut"`). Never allow room tone, SFX decay, or music to hard-cut at the end of a video.

### ARTICLE VI: TRANSITIONS, STORY CAPTIONS & COLOR CONTINUITY

- **Action, Excursions & Parties (85% Hard Cuts / 15% Dissolves):** Use clean beat-aligned hard cuts within scenes, reserving `Cross Dissolve` (`0.5s`) for scene boundaries and flashback transitions (such as entering/exiting `Scene 00`).
- **Archival Slideshows (`1.0s` Cross Dissolves):** For 1980–1984 university slideshows and 1977+ B&W retrospectives, apply smooth `1.0s` (30 frames) `Cross Dissolve` transitions between slides and a `1.5s` `Dip to Black` between chronological eras.
- **Storyboard Punchline Captions (`V2`):** When `Storyboard.md` highlights a specific narrative joke or callback (e.g., *"Scene 00: July 2025 — Last sighting of the €20 jacket at SJC"*, *"€20 -> €30 inflation (+ he's in Alcúdia every Tuesday!)"*, or *"Saved by Nina's sharp eyes: Front disc brake pad on the ground!"*), generate clean lower-third text overlays on `V2`.
- **Color & Monochrome Integrity:** Conform iPhone 15 Pro `BT.2020` HDR clips to `Rec.709` linear light. Never apply color LUTs or saturation adjustments to 1977+ black-and-white film scans.

### ARTICLE VII: DIRECT TIMELINE ASSEMBLY & FILMCRAFT PLAYBACK REVIEW

No human editor wants to proofread hundreds of rows of numerical timecodes in a spreadsheet (`cut_table.md`) to imagine how a video feels. All timeline assembly is executed directly from `Storyboard.md` via FilmCraft MCP:
1. **Live Assembly & Verification:** As clips and audio tracks are assembled in FilmCraft, visual review happens directly where it belongs: in the open FilmCraft GUI playback window or the rendered 4K `.mp4` export.
2. **Conversational Adjustments:** Any pacing, trim, or audio adjustments are requested directly in chat (*"shorten the market scene by 2 seconds"*, *"boost Nina's voice"*, *"swap music track"*). The agent applies the edits instantly via FilmCraft MCP socket calls.
3. **Cut Table Deprecated:** The intermediate `cut_table.md` file is fully deprecated in favor of direct timeline execution and real-time visual feedback.

### ARTICLE VIII: IMPERIAL UNITS DEFAULT, GPX WIDGETS, LOW-RES B-ROLL FRAMING & BROADCAST AUDIO MIX

- **Imperial Units by Default (US Primary Audience):**
    - All titles, voice-overs, GPX widgets, `.srt` subtitles, and YouTube descriptions MUST use **Imperial units (`mi`, `ft`, `mph`, `°F`) by default** (followed by metric in parentheses in the YouTube description, e.g., `21.5 mi (34.5 km)` and `531 ft (162 m)`).
- **Zero Burned-In Bottom Titles (`burned_in_titles: false` Default):**
    - Export master 4K MP4s with `--settings '{"burnCaptions": false}'` (keeping `C1` inside `.fcproj` disabled visually, used solely as timing metadata for `.srt` export). This guarantees 100% clean 4K video frames that never collide with YouTube's native CC subtitles on iPhone or desktop.
- **Direct-from-GPX Corner Route Map & Smoothed Telemetry HUD (`gpx_widgets.py`):**
    1. **GPX Corner Route Map (`V2`, top-right, `3.5s`):** Rendered directly from the `.gpx` track into a 4K transparent PNG (`map_01_*.png` .. `map_04_*.png`) showing the full route polyline, highlighted progress up to that scene, pulsing rider marker, and Imperial mileage/elevation header. Always time-shift corner maps clear of close-up mechanical/object stills so key details in the top-right corner remain unobstructed.
    2. **Smoothed Dynamic GPX Telemetry HUD (`V2`/`V3`, top-left, `auto` | `always` | `off`):** Compute road gradient over a **`>= 40 m` horizontal lookback window** (eliminating Garmin `0.2 m` barometric altimeter quantization spikes at low speeds) and power over a **3-second rolling average**.
        - **Activity-Aware Dynamic Speed Thresholds (`auto` Mode):**
            - **Cycling Rides (`cycling_ride`):** Turn HUD **ON** when 3-second rolling speed $> 2.0\text{ mph}$ ($3.2\text{ km/h}$).
            - **Running (`run`):** Turn HUD **ON** when 3-second rolling speed $> 1.5\text{ mph}$ ($2.4\text{ km/h}$).
            - **Hiking & Walking (`hike_outdoor`):** Turn HUD **ON** when 3-second rolling speed $> 0.8\text{ mph}$ ($1.3\text{ km/h}$) so steep uphill mountain climbs are never mistakenly classified as stopped!
        - **Static Scene Suppression (`auto` Mode):** Automatically turn the Telemetry HUD **OFF** for still photos (`.jpg`, `.png`, `.heic`) and stationary video scenes (café stops, bakery counters, terrace chats, gate stops, mechanical adjustments, where speed falls below the activity threshold), keeping the frame clean during conversational and still moments.
        - **Manual Override & Conversational Trial/Error:** `gpx_telemetry_hud` can be explicitly set to `always` (display on all video clips) or `off` (hide completely) in the `/build-timeline` alignment card. Because telemetry pacing is inherently aesthetic, visual review happens by scrubbing FilmCraft or watching the rendered MP4; if a specific scene feels unnatural, Alexander can refine it conversationally in chat (*"turn HUD off on Camí Vell"* or *"toggle HUD to always"*).
- **Partial-Screen Picture-in-Picture Card for Low-Resolution B-Roll (`low_res_broll_mode: "pip_card"`):**
    - Never stretch sub-1080p clips (such as `1024x576` WhatsApp/smartphone videos like `2026-11-02_Zumba.mp4`) to full `3840x2160`. Instead, pre-composite them via `ffmpeg` at **62% scale (`2368x1332`) with an `8px` warm white border** centered over a blurred, softly darkened (`boxblur=16:2, brightness=-0.12`) 4K contextual photo on `V1`.
- **Broadcast-Balanced 4-Track Audio Architecture (`-16.0 dB` Speech Mean vs. `-28.5 dB` Ducked Music Mean):**
    - **Same-Language Live Dialogue Honor Law (`edition_lang == clip_dialog_lang`):**
        - **Voice-Over narration (`A4`) MUST NEVER cover or overpower live on-camera dialogue (`A1`) spoken in the SAME language!**
        - Specifically: the **English (`EN`)** track must honor live English speaking sections on `A1` (suppressing or shifting `EN` VO clear of the live English speech); the **Russian (`RU`)** track must honor live Russian speaking sections on `A1` (suppressing `RU` VO over all cuts containing live Russian dialogue and playing `RU` VO only over silent stills or non-speech ambient sections); and the **Ukrainian (`UA`)** track must honor live Ukrainian speaking sections on `A1`.
        - Conversely, when the edition language is **different** from the clip's live speech language (`edition_lang != clip_dialog_lang`, e.g., `EN` or `UA` VO translating a clip with `RU` camera speech), duck `A1` by **`-12.0 dB`** (down to `-24.0 dB` fader / `-42 dB` mean) during active VO cues so foreign-language camera chatter never competes with the narrator.
    - **`A1` (Live Camera Speech & B-Roll Audio):**
        - **Natural `1.00x` Speech Speed & `1:1 V1 == A1` Lip-Sync Law:** NEVER apply `atempo > 1.0` or internal pause-stripping (`silenceremove=...:stop_periods=-1`) to human speech on `A1` or Voice-Over on `A4`! All live camera speech and synthesized voice-over MUST play at **100% natural `1.00x` speed**. Size each speaking visual cut (`V1`) to match the exact `1.00x` duration of its complete spoken sentence (`src_in` to `src_in + dur`), keeping `V1` and `A1` locked 1:1 so lip movement and camera motion (e.g., tilting down to reveal a coffee cup and croissant as they are named) stay in 100% frame-and-sample sync, without overflowing into the next scene.
        - **Mandatory `1.5s–2.0s` Opening Music Intro Law:** Never start a video abruptly with voice-over at `0.0s–0.2s`. Always let the opening visual and background music (`A2`) establish the scene for **`1.5s–2.0s`** before the first `A4` Voice-Over cue begins (in both `.fcproj` and rendered `.mp4` stems).
        - **Sample-Accurate `atrim` & Post-Mix `dynaudnorm` Rule:** When trimming live dialogue from HEVC `.MOV` files in `ffmpeg`, always use sample-accurate `atrim=start=...:end=...,asetpts=PTS-STARTPTS` (rather than input `-ss` before `-i`, which snaps to video keyframes and shifts audio by up to `1.5s`), and apply `dynaudnorm=f=150:g=7:p=0.90` **once on the combined full-length dialogue stem** after `amix` (never inside short per-clip `atrim` chains where `dynaudnorm`'s multi-frame lookahead buffer can swallow phrase tails).
        - **Camera Speech Normalization (`live_dialog_boost: "auto"`):** Normalize featured live spoken dialog segments (`highpass=f=100, lowpass=f=7500, dynaudnorm=f=150:g=7:p=0.90, volume=1.35`) to hit **`-16.0 dB` mean / `-1.0 dB` peak** and strip any overlapping `A3` sound effects so live conversation is crystal clear.
        - **PiP B-Roll Music Taming:** Set smartphone B-roll music (e.g., live Zumba audio) to **`-6.5 dB`** (`-30 dB` mean) with `0.6s` fades so it never overpowers the mix.
    - **`A2` (Multi-Phase Background Music — Mandatory RMS Loudness Calibration):**
        - Because upbeat/funk/retro tracks are often mastered hot (`-10.8 dB` to `-12.6 dB` RMS mean vs. `-18.5 dB` on acoustic tracks), **never apply a blind fixed `-7.5 dB` fader gain**.
        - Always measure each BGM track's `mean_volume` via `ffmpeg volumedetect` (`compute_bgm_ducked_gain_db`) and set its ducked gain (`gain_db = -28.5 - raw_mean_db`) so `A2` hits **`-28.5 dB` mean** underneath any Voice-Over or Featured Live Dialogue — guaranteeing **`>= 12.5 dB` of speech-to-music separation**!
        - During purely visual/ambient sections with **zero** VO and **zero** live dialogue, swell `A2` by **`+5.0 dB` (`-23.5 dB` mean)**.
    - **`A3` (Contextual Sound Effects):** Keep subtle (`-10 dB`) and never place SFX over spoken dialogue.
    - **`A4` (Replicated Warm Voice-Over, `voice_jntybwupjc1s`):**
        - Synthesize scene-synced narration segments using `gemini-3.8-flash-tts` with Alexander's vocal persona (`03_Audio_Library/03_Voice_Profile/voice_id.json`), normalized via `highpass=f=90, dynaudnorm=f=150:g=11:p=0.90, volume=2.5dB` to **`-16.0 dB` mean / `-1.0 dB` peak** (`12.5 dB` louder than ducked music).

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
- **Zero-Plaintext-Secrets Environment Setup:**
    - Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, and `GOOGLE_OAUTH_CLIENT_SECRET` via your preferred environment manager (e.g., `direnv` + 1Password, shell profile, or a git-ignored `.env` file) and start Antigravity from that shell session so child processes inherit them automatically. Once authorized once, `~/.config/antigravity_youtube/token.json` caches the OAuth refresh token for subsequent YouTube API calls. Default video visibility to **`unlisted`** so the creator can preview, test comments/language switchers, and share the link without public feed spam (and avoiding YouTube's `private` mode comment-blocking).
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
- **Default Lossless Remux Law (`_RU.mp4` Always Ready):**
    - Regardless of whether YouTube uses `option_a` (single video + CC) or `option_b`, `/build-timeline` MUST ALWAYS losslessly remux `<project>_RU.mp4` in **`0.2 seconds`** (`ffmpeg -c:v copy -c:a aac`) and save it to `~/Movies/Exports/YEAR/<project>_RU.mp4`.
    - This guarantees Alexander always has the Russian-voiced 4K video ready for instant upload to Flickr or WhatsApp without needing to re-render.
- **Flickr Metadata Package (One-Click Upload via Web or Lightroom Publishing Service):**
    - On every release, `/publish-youtube` and `/build-timeline` output a dedicated **Flickr Publishing Box** (in chat and appended to `facebook_promo.md`) containing:
        - **Title:** `YYYY-MM-DD · <Russian Title> (<mi> / <km>)` (matching Alexander's Flickr convention, e.g. `2026-10-27 · Вместо группы: выпечка в Буже и «VIP»-кофе (40.1 мили / 64.5 км)`).
        - **Description:** Clean Russian story description highlighting landmarks, cafe stops, and route lore.
        - **Tags:** `Mallorca, cycling, roadbike, BleeqUP, video, <Village>` (comma-separated for one-click Flickr tagging).
        - **Recommended Album:** e.g., `2026 Fall Mallorca Cycling` in Lightroom Publishing Service / Flickr.
