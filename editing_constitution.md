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
- **The Two-Gear Execution Dial (Fed by `Storyboard.md`):**
    - **Gear 1 — Express `/magic-movie` Mode (Hands-Off Auto-Pilot):** Reads `Storyboard.md` (or auto-generates it on the fly if missing), picks Candidate #1 from `recommended_music_candidates` in `03_Audio_Library/01_Curated_BGM/`, writes `cut_table.md` to `04_Project_Catalog/YEAR/<project_name>/`, immediately builds the timeline via MCP (`command_batch` in FilmCraft) without pausing for "OK", saves the `.fcproj`, verifies 3 rendered frames, and exports the `.mp4` to `~/Movies/Exports/YEAR/`.
    - **Gear 2 — Supervised `/build-cut-table` Mode (Brehov Approval Gate):** Translates `Storyboard.md` (`Scene 00` $\rightarrow$ `Scene N`) directly into the Markdown **Cut Table** (`cut_table.md`), displays the top 3 recommended music tracks (or offers to run `/find-music` on your open YouTube Audio Library / `creatormix.com` tabs), and waits for the user to reply **"OK"** before calling any mutating MCP timeline tools.

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
    - **Fades on `A2`:**
        - **Head:** `1.0s` to `1.5s` linear fade-in starting with clip motion.
        - **Tail:** `1.5s` to `2.0s` exponential fade-out over the closing cooldown or static shot.

### ARTICLE VI: TRANSITIONS, STORY CAPTIONS & COLOR CONTINUITY

- **Action, Excursions & Parties (85% Hard Cuts / 15% Dissolves):** Use clean beat-aligned hard cuts within scenes, reserving `Cross Dissolve` (`0.5s`) for scene boundaries and flashback transitions (such as entering/exiting `Scene 00`).
- **Archival Slideshows (`1.0s` Cross Dissolves):** For 1980–1984 university slideshows and 1977+ B&W retrospectives, apply smooth `1.0s` (30 frames) `Cross Dissolve` transitions between slides and a `1.5s` `Dip to Black` between chronological eras.
- **Storyboard Punchline Captions (`V2`):** When `Storyboard.md` highlights a specific narrative joke or callback (e.g., *"Scene 00: July 2025 — Last sighting of the €20 jacket at SJC"*, *"€20 -> €30 inflation (+ he's in Alcúdia every Tuesday!)"*, or *"Saved by Nina's sharp eyes: Front disc brake pad on the ground!"*), generate clean lower-third text overlays on `V2`.
- **Color & Monochrome Integrity:** Conform iPhone 15 Pro `BT.2020` HDR clips to `Rec.709` linear light. Never apply color LUTs or saturation adjustments to 1977+ black-and-white film scans.

### ARTICLE VII: REQUIRED CUT TABLE SCHEMA

Before assembling any timeline in Supervised Mode (or when logging the auto-plan in `/magic-movie` Mode), write `04_Project_Catalog/YEAR/<project_name>/cut_table.md` mapping every scene from `Storyboard.md`:

**Storyboard Source:** `Storyboard.md` | **Selected Music (`A2`):** `<[BPM]_[Mood]_[TrackName]_[Artist].mp3>` (`<BPM>` BPM, `<beat_interval_s>s/beat`) | **Alternates:** 1. `<alt1.mp3>`, 2. `<alt2.mp3>`

| **Cut #** | **Timeline TC** | **Duration** | **Storyboard Scene** | **Source File** | **Source / Era** | **In -> Out (s)** | **Visual Action / Caption Overlay** | **Context / Telemetry** | **Audio (A1 / A2 dB)** |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | 00:00.0 – 00:03.5 | 3.5s | Scene 00: Flashback | `IMG_E9287.jpg` | iPhone (2024) | Still (3.5s) | Push-In 100%->106% + Caption | SJC Jacket Backstory | Mute / -11 dB (1.5s fade-in) |

### ARTICLE VIII: IMPERIAL UNITS DEFAULT, GPX WIDGETS, LOW-RES B-ROLL FRAMING & BROADCAST AUDIO MIX

- **Imperial Units by Default (US Primary Audience):**
    - All titles, voice-overs, GPX widgets, `.srt` subtitles, and YouTube descriptions MUST use **Imperial units (`mi`, `ft`, `mph`, `°F`) by default** (followed by metric in parentheses in the YouTube description, e.g., `21.5 mi (34.5 km)` and `531 ft (162 m)`).
- **Zero Burned-In Bottom Titles (`burned_in_titles: false` Default):**
    - Export master 4K MP4s with `--settings '{"burnCaptions": false}'` (keeping `C1` inside `.fcproj` disabled visually, used solely as timing metadata for `.srt` export). This guarantees 100% clean 4K video frames that never collide with YouTube's native CC subtitles on iPhone or desktop.
- **Direct-from-GPX Corner Route Map & Smoothed Telemetry HUD (`gpx_widgets.py`):**
    1. **GPX Corner Route Map (`V2`, top-right, `3.5s`):** Rendered directly from the `.gpx` track into a 4K transparent PNG (`map_01_*.png` .. `map_04_*.png`) showing the full route polyline, highlighted progress up to that scene, pulsing rider marker, and Imperial mileage/elevation header. Always time-shift corner maps clear of close-up mechanical/object stills so key details in the top-right corner remain unobstructed.
    2. **Smoothed Dynamic GPX Telemetry HUD (`V2`/`V3`, top-left, `auto`):** Compute road gradient over a **`>= 40 m` horizontal lookback window** (eliminating Garmin `0.2 m` barometric altimeter quantization spikes at low speeds) and power over a **3-second rolling average**. Only display the telemetry HUD on riding video clips when smoothed gradient $\ge 4\%$, speed $\ge 25\text{ mph}$, or 3s average power $\ge 220\text{ W}$ (suppressing HUD clutter on flat easy spins).
- **Partial-Screen Picture-in-Picture Card for Low-Resolution B-Roll (`low_res_broll_mode: "pip_card"`):**
    - Never stretch sub-1080p clips (such as `1024x576` WhatsApp/smartphone videos like `2026-11-02_Zumba.mp4`) to full `3840x2160`. Instead, pre-composite them via `ffmpeg` at **62% scale (`2368x1332`) with an `8px` warm white border** centered over a blurred, softly darkened (`boxblur=16:2, brightness=-0.12`) 4K contextual photo on `V1`.
- **Broadcast-Balanced 4-Track Audio Architecture (`-19 dB` to `-22 dB` Mean Target):**
    - **`A1` (Live Camera Speech & B-Roll Audio):**
        - **BleeqUP Camera Speech Normalization (`live_dialog_boost: "auto"`):** BleeqUP Ranger microphones record raw speech at `-45 dB` to `-53 dB` mean. Always extract spoken dialog segments into a speech-normalized stereo WAV (`highpass=f=120, lowpass=f=7500, volume=16..22dB, dynaudnorm=f=150:g=11:p=0.92`, hitting **`-22 dB` mean / `0.0 dB` peak**) and strip any overlapping `A3` sound effects so live conversation is crystal clear.
        - **PiP B-Roll Music Taming:** Set smartphone B-roll music (e.g., live Zumba audio) to **`-6.5 dB`** (`-30 dB` mean) with `0.6s` fades so it never overpowers the mix.
    - **`A2` (Multi-Phase Background Music):**
        - Play at **`-7.5 dB`** (`-26 dB` mean) underneath Voice-Over segments so the warm groove is clearly felt, and **swell by `+3.5 dB` (`-4.0 dB`, `-22.9 dB` mean)** during riding-only sections where no voice-over or dialog is active. Mute `A2` completely during live music B-roll or live gate dialog.
    - **`A3` (Contextual Sound Effects):** Keep subtle (`-10 dB`) and never place SFX over spoken dialogue.
    - **`A4` (Replicated Warm Voice-Over, `voice_jntybwupjc1s`):**
        - Synthesize scene-synced narration segments (`part1`, `part2`, etc.) using `gemini-3.8-flash-tts` with Alexander's vocal persona (`03_Audio_Library/03_Voice_Profile/voice_id.json`, derived from `Zero-T Performance Self-Talk.m4a`) at an upbeat, natural conversational storytelling pace, normalized to `48 kHz` stereo PCM (`-16 LUFS`, placed at `-0.5 dB` for **`-19.0 dB` mean**).

### ARTICLE IX: YOUTUBE PUBLISHING MODES (`en_only` / `option_a` / `option_b`), ISO `ua` STANDARD & COMPOSITE THUMBNAILS

- **Strict ISO Country Code `ua` for Ukraine:**
    - Always use **`ua`** (`UA`) across all local filenames (`voiceover_ua_part1.wav`, `full_audio_ua.m4a`, `captions.ua.srt`, `*_UA.mp4`) and JSON keys (`localizations.ua`), mapping `"ua" -> "uk"` exclusively inside `upload_youtube_api.py` when calling the YouTube Data API v3 wire format.
- **Mallorca Phonetic Toponym Rule (`ll` Before a Vowel $\rightarrow$ `й` / `є`; Pre-Consonantal `ll` in `Valldemossa` $\rightarrow$ `Валдемоса`):**
    - On Mallorca, intervocalic and word-initial `ll` before a vowel (`V + ll + V` or `# + ll + V`) is pronounced `[j]` (*yeísmo* / *ieisme*). In all Russian (`ru`) and Ukrainian (`ua`) titles, descriptions, subtitles, and voice-over scripts, ALWAYS transcribe `ll` before a vowel phonetically without `"л"`:
        - **Mallorca** $\rightarrow$ RU: **`Майорка`** | UA: **`Майорка`** *(never «Мальорка»)*
        - **Pollença / Port de Pollença / Badia de Pollença** $\rightarrow$ RU: **`Пойенса` / `Порт-де-Пойенса` / `Бадия-де-Пойенса`** (`через Пойенсу`, `залива Пойенса`) | UA: **`Поєнса` / `Порт-де-Поєнса` / `Бадія-де-Поєнса`** (`через Поєнсу`, `затоки Поєнса`) *(never «Польенса» / «Польєнса»)*
        - **Sóller / Port de Sóller** $\rightarrow$ RU: **`Сойер` / `Порт-де-Сойер`** | UA: **`Соєр` / `Порт-де-Соєр`**
        - **Lluc / Llucmajor / Cala Millor** $\rightarrow$ RU: **`Йук` / `Йукмайор` / `Кала-Мийор`** | UA: **`Йук` / `Йукмайор` / `Кала-Мійор`**
    - **Exception — Pre-Consonantal `ll` (`Valldemossa` = *Vall* + *de Mossa*):** Because `ll` immediately precedes the consonant `d`, Spanish/English speakers reduce it to a clean `[l]`. Write and voice **`Валдемоса`** (or **`Вальдемоса`**, never *«Вайдемосса»*).
- **Zero-Plaintext-Secrets Environment Setup:**
    - Set `GEMINI_API_KEY`, `GOOGLE_OAUTH_CLIENT_ID`, and `GOOGLE_OAUTH_CLIENT_SECRET` via your preferred environment manager (e.g., `direnv` + 1Password, shell profile, or a git-ignored `.env` file) and start Antigravity from that shell session so child processes inherit them automatically. Once authorized once, `~/.config/antigravity_youtube/token.json` caches the OAuth refresh token for subsequent YouTube API calls. Default primary video visibility to **`private`** so the creator can review before switching to Public.
- **Three Selectable Localization & Publishing Modes (`publishing_mode` in `Storyboard.md` Section 5):**
    1. **`en_only`:** Uploads only the primary English 4K master (`private`) with `captions.en.srt`.
    2. **`option_a` (Single Video + Multilingual Subtitles & Inline Description):** Uploads a single 4K master (`private`) with `captions.en.srt`, `captions.ua.srt`, and `captions.ru.srt` (matching the spoken voice-over and live dialog word-for-word), sets YouTube native `localizations` (`uk` and `ru`), and embeds `🇺🇦 УКРАЇНСЬКОЮ` and `🇷🇺 ПО-РУССКИ` story summaries inside the main description (omitting duplicate `00:00` timestamp blocks in the inline sections so YouTube's chapter parser always keeps the English chapter titles).
    3. **`option_b` (All 3 Locales — Special Occasions / Family Voice-Over Editions):**
        - Generates balanced stereo mixes `full_audio_en.m4a`, `full_audio_ua.m4a`, and `full_audio_ru.m4a`, and remuxes `_UA.mp4` and `_RU.mp4` in **`0.2 seconds`** via `ffmpeg -c:v copy` (zero video re-encoding!).
        - Uploads `_UA.mp4` and `_RU.mp4` as **Unlisted** (avoiding channel feed clutter), automatically embeds their clickable links (`🔊 Повна версія з українською озвучкою` / `🔊 Полная версия с русской озвучкой`) at the top of the `🇺🇦` / `🇷🇺` sections in the **Private** English master description, and cross-links the English master URL back into the `_UA` and `_RU` descriptions.
- **YouTube Studio Composite Thumbnail Standard (`thumbnail.mode: "composite_ai"` — Localized per Edition):**
    - Co-design a high-impact 1920×1080 thumbnail in Section 5 of `Storyboard.md` combining: (1) a softly blurred scenic background + sharp hero portrait on the left, (2) a white-outlined sticker cutout of the key story prop/action on the right, and (3) a bold 3–4 word yellow-and-white headline across the top (`headline_text` for `thumbnail.jpg`, plus localized `headline_text_ua` $\rightarrow$ `thumbnail_ua.jpg` and `headline_text_ru` $\rightarrow$ `thumbnail_ru.jpg` for `option_b` editions).
