---
name: build-timeline
description: Interactive & one-command 4K timeline builder (Studio v2). Presents an in-chat clickable alignment card (Primary Language, Music Selection with 10s audio preview, Publishing Mode), writes choices to Storyboard.md automatically, downloads linked YouTube flashbacks, renders GPX corner maps & telemetry HUD, generates replicated voice-over (EN/UA/RU), builds the 4-track broadcast audio mix in FilmCraft MCP, exports clean 4K MP4, generates composite thumbnail, metadata & facebook_promo.md, and pauses for review before YouTube upload.
---

# Stage 1: Interactive & Unified Timeline Assembly (`/build-timeline`)

## Purpose & Conversational Zero-IDE Workflow
Use `/build-timeline <folder>` to turn an approved `Storyboard.md` into a finished, broadcast-quality 4K `.mp4` video.

### Core Philosophy: Zero-IDE, Chat-First
- **No Spreadsheets (`cut_table.md` retired):** You never have to inspect or edit a massive spreadsheet of timecodes. Visual review happens where it belongs: by watching the rendered video or scrubbing the live timeline in FilmCraft.
- **No Manual YAML/Markdown Editing:** You never have to switch to IntelliJ IDEA to tweak settings like `primary_audio_language` or `publishing_mode`. The agent presents an **interactive, clickable multiple-choice card** (`ask_question`) directly in the chat, updates `Storyboard.md` on disk automatically, and can play 10-second audio previews of candidate music tracks on your Mac speakers (`afplay`).

---

## Execution Sequence

### Step 1: Bridge & Environment Verification
1. Run `python3 ./.agents/skills/build-timeline/scripts/check_filmcraft_env.py` to enforce FilmCraft $\ge$ `v0.17.0`, auto-sync `filmcraft-cli` if `FilmCraft.app` was updated, and verify bridge capabilities.
2. Ensure FilmCraft is running with render caches isolated to `~/Movies/Cache_And_Previews`:
   ```bash
   mkdir -p ~/Movies/Cache_And_Previews && cd ~/Movies/Cache_And_Previews
   open -a FilmCraft --args --control 9876
   ```
3. If `Storyboard.md` does not yet exist, run `/storyboard <folder>` first to co-create the narrative arc.

---

### Step 2: The In-Chat Clickable Alignment Card (`ask_question`)
Before synthesizing voice-over, rendering GPX maps, or building the timeline, prompt Alexander with **one focused question per turn** using `ask_question` (never bundle all 3 into one card, so each choice receives dedicated focus and cannot be accidentally bulk-submitted):

1. **Question 1: Primary Voice-Over Language**
   - Detect the predominant language spoken in the raw video clips (e.g. Russian, Ukrainian, or English).
   - Options:
     - `(Recommended) Match spoken in clips (<Detected Language>)`
     - `English (for US cycling channel / SJBC teammates)`
     - `Ukrainian`
     - `Russian`
     - `No Voice-Over (Music + live ambient audio only)`

2. **Question 2: Background Music Selection (with Speaker Preview)**
   - Present the top 2 curated tracks from `03_Audio_Library/01_Curated_BGM/` matching the project genre & BPM.
   - Use clear, unmistakable action prefixes (`▶️ Listen` vs `✅ Select`):
     - `▶️ Listen to Track #1 ("<Track 1 Name>" — <BPM> BPM, <Genre>)`
     - `▶️ Listen to Track #2 ("<Track 2 Name>" — <BPM> BPM, <Genre>)`
     - `(Recommended) ✅ Select Track #1 ("<Track 1 Name>")`
     - `✅ Select Track #2 ("<Track 2 Name>")`
     - `🔍 Search for a different mood or genre...`
   *(If the user selects a preview, run `afplay -t 10 "03_Audio_Library/01_Curated_BGM/<path_to_track>"` and immediately re-prompt for their choice).*

3. **Question 3: Native AI Creative Artifacts (`ai_creative_artifacts`)** *(Multi-select or preset choice)*
   - Present the candidate AI creative shots from `Storyboard.md` (synthesized 100% natively via `.agents/skills/storyboard/scripts/generate_ai_creative_assets.py` using `gemini-3-pro-image-preview` + `gemini-omni-1.1-flash`, with zero dependency on BleeqUP's AI tracking feature):
     - `(Recommended) Weave All Selected Studio AI Artifacts (Painting->Reality Cold Open + Native FPV Drone Swoop + Living Archival Memory)`
     - `Living Archival Memory Only (Animate 2017/archival Lightroom photos on V1)`
     - `Painting->Reality Cold Open + Living Archival Memory`
     - `Pure Documentary Cut (100% real camera footage & static archival photos only)`

4. **Question 4: Telemetry HUD Overlays (`gpx_telemetry_hud`)** *(When GPX track is present)*
   - Options:
     - `(Recommended) Auto — On for moving scenes (> 2.0 mph for ride / > 0.8 mph for hike), Off at stops & stills`
     - `Always ON — Show Telemetry HUD on all video clips`
     - `OFF — Hide Telemetry HUD completely (clean screen)`

5. **Question 5: YouTube Publishing Mode**
   - Options:
     - `(Recommended) Option A — 1 Clean 4K Master (Unlisted) + EN/UA/RU Subtitles`
     - `English Only (1 4K Master, Unlisted)`
     - `Option B — 3 Separate Voiced Videos (EN + UA + RU)`

6. **Question 6: Flickr Publishing Choice**
   - Options:
     - `(Recommended) Russian Edition (_RU.mp4) — For family & classmates (bypasses YouTube censorship)`
     - `Both EN Master + RU Edition`
     - `English Master Only`
     - `Skip Flickr for now`

**Automatic Persistence:** Once Alexander selects his choices and submits the form, the agent writes the selected language, music tracks, HUD setting, and publishing modes (YouTube and Flickr) directly into Section 5 of `Storyboard.md` on disk. **Zero window switching, zero manual file edits.**

---

### Step 3: Fetch B-Roll & Render GPX Widgets
1. **YouTube Flashbacks:** If `Storyboard.md` links an `@akomlik` YouTube URL, pull the slice via `fetch_yt_broll_clip.py`. If low-res ($< 720\text{p}$), frame it as a **62% centered Picture-in-Picture (PiP) card** with an 8px warm white border over a soft-blurred 4K photo backdrop (`low_res_broll_mode: pip_card`).
2. **GPX Widgets:** If a `.gpx` track is present, run `gpx_widgets.py` to generate:
   - **Corner Route Map (`V2`, top-right, 3.5s):** 26% width, 82% opacity, cyan route + orange progress + glowing marker dot.
   - **Telemetry HUD (`V2`, bottom-right, auto):** Displayed only on riding scenes where speed $\ge 5\text{ mph}$, grade $\ge 4\%$, or 3s power $\ge 150\text{ W}$.
3. **Signature AGVS Bookends (`agvs_bookends.py`):** If `agvs_bookends.enabled: true` in Section 5 (default), run `agvs_bookends.py` to generate:
   - **Opening Pre-Flight Postcard (`bookend_intro_4K.mp4`, 3.5s):** Composites the first 3.5s of opening footage inside a -2.0° tilted white postcard frame over a 4K topographic GPX route canvas with the AGVS aerospace stamp, dynamic motto, and ticket-stub manifest bar.
   - **Closing Post-Ride Bar Tab & Credits (`bookend_outro_4K.mp4`, 4.5s):** Composites the final 4.5s of timeline footage inside a +1.5° tilted postcard with "Wish you were here! — AGVS" on the left, alongside the "AGVS Production Receipt / Credits Card" on the right. Both live A1 ambient audio and A2 music tail shine during the credits.

---

### Step 4: Synthesize Voice-Over & 4-Track Broadcast Mix
1. **Replicated Voice-Over (`A4`):**
   - Run `generate_voiceover.py` using Alexander's custom voice persona (`voice_jntybwupjc1s`) to synthesize scene-synced 48 kHz stereo narration (`-16 LUFS`) for the selected primary language (and UA/RU if `option_b` was chosen).
   - **Same-Language Dialogue Honor Law:** Never place voice-over in language $L$ over live camera dialogue spoken in that same language $L$ (`filter_vo_cues_for_same_language_dialog`). Duck foreign-language dialogue by `-12 dB` under translation VO.
2. **Live Dialogue Normalization (`A1`):**
   - Extract and normalize camera conversation with a 120 Hz high-pass filter + `+16..22 dB` boost + `dynaudnorm` (`-22 dB` mean). Remove overlapping SFX.
3. **BGM Audio Architecture (`A2`):**
   - Calibrate music so it sits at **`-28.5 dB` mean** under speech (`12.5 dB` quieter than VO/dialogue), swelling by `+5.0 dB` (`-23.5 dB` mean) during pure riding.
   - Begin with a `1.5s–2.0s` music intro before the first VO cue.
   - End with a mandatory `2.0s–2.5s` half-sine audio fade-out (`curve=hsin`) matching the visual dip-to-black.
4. **Captions (`C1`):**
   - Set `burnCaptions: false` and `enabled: false` inside `.fcproj` so the 4K video frame has **zero burned-in bottom titles** (subtitles served via `.srt`).

---

### Step 5: Load `.fcproj` in FilmCraft GUI & Mandatory Live Preview Gate (BEFORE 4K Render!)
1. **Build & Save Valid `schema_version: 17` `.fcproj`:** Write `04_Project_Catalog/YEAR/<project_name>/<project_name>.fcproj` with all video clips (`V1`), overlays/PiP/HUD (`V2`), camera audio (`A1`), music (`A2`), SFX (`A3`), and synthesized voice-over (`A4`).
2. **Open Live in FilmCraft GUI:** Launch or refresh `FilmCraft.app` (`v0.18.0+`) with the `.fcproj` file so Alexander can press Spacebar and play the timeline immediately:
   ```bash
   cd ~/Movies/Cache_And_Previews && open -a FilmCraft --args --control 9876 "<absolute_path_to_fcproj>"
   ```
3. **🛑 MANDATORY PRE-RENDER GATE (NEVER RENDER MP4 WITHOUT USER OK):**
   - **STOP HERE** before running any full-timeline 4K MP4 export (`ffmpeg` or `render.export`).
   - Ask Alexander in chat:
     *"Timeline `.fcproj` is built and loaded in FilmCraft! Please play/scrub it in FilmCraft and let me know if any cuts, audio levels, or overlays need tweaking—or say **'OK to render'** to export the final 4K MP4 and Russian edition."*

---

### Step 6: Export 4K MP4, Russian Edition (`_RU.mp4`) & Metadata Package (Only After User Approves Timeline)
1. **Render 4K Master:** Once Alexander approves the timeline in FilmCraft, export `~/Movies/Exports/YEAR/<project_name>.mp4` (`3840x2160`, `H.264`, `AAC 192k`).
2. **Lossless Russian Remux (`_RU.mp4` by Default):** Always build `full_audio_ru.m4a` and losslessly remux with the 4K video stream in `0.2s` (`ffmpeg -c:v copy -c:a aac`) into `<project_name>_RU.mp4` by default (plus `_UA.mp4` if `option_b`). This ensures Alexander always has the Russian-voiced 4K edition ready for instant upload to Flickr (`apkom`) and WhatsApp channels for family (Nina's brother, Alexander's sister in Sevastopol) and classmates who face YouTube restrictions.
3. **Metadata, Thumbnails & Social/Flickr Package:** Run `generate_youtube_metadata.py` to create:
   - `youtube_metadata.json` (Imperial stats, hook-first title, chapters, localized text)
   - `thumbnail.jpg`, `thumbnail_ua.jpg`, `thumbnail_ru.jpg`
   - `facebook_promo.md` (Facebook Curiosity Hook + First Comment, Direct Story, Bilingual, and the **📸 Flickr Publishing Box** with Russian title, description, tags, and album recommendation).

---

### Step 7: Final Upload Approval Gate
1. Present the export summary, hook-first title, and thumbnail previews in chat.
2. **MANDATORY UPLOAD GATE (NEVER AUTO-UPLOAD):** Pause and ask:
   *"4K MP4 (`<project_name>.mp4` and `_RU.mp4`) exported to `~/Movies/Exports/YEAR/`. Ready to publish to YouTube (`/publish-youtube`) and Flickr (`/publish-flickr`)?"*
