---
name: build-cut-table
description: Generates the scene-by-scene Cut Table from Storyboard.md, editing_constitution.md, my_digital_brain.md, and project_manifest.json. Saves cut_table.md to Google Drive 04_Project_Catalog/YEAR/ and waits for human OK.
---

# Gear 2: Build Universal Master Cut Table (`/build-cut-table`)

## Implicit Context Caching & Quota Guardrail
1. Switch to **Gemini 4 Argon** (`thinking_level: "medium"`).
2. To trigger Gemini 4 Argon's **95% Implicit Context Cache** (enabled automatically for prompts $\ge 4,096$ tokens), always load `editing_constitution.md` and `my_digital_brain.md` as the static prefix at the very top of your context before reading `Storyboard.md` and `project_manifest.json`.
3. Do NOT call any mutating FilmCraft or DaVinci Resolve MCP tools during this skill.

## Step-by-Step Procedure
1. Read `editing_constitution.md`, `my_digital_brain.md`, the project's `Storyboard.md` (including **Section 5: Production & YouTube Publishing Spec**), and `project_manifest.json`.
2. If `Storyboard.md` is still an unrefined skeleton, run the `/storyboard` visual inspection first and ask the user to confirm the story before building the Cut Table.
3. Map every scene (`Scene 00` through `Scene N`) in `Storyboard.md` into rows of the Cut Table (`cut_table.md`):
   - Quantize non-speech visual cuts to the beat interval (`beat_interval_s`) of the #1 recommended track in `recommended_music_candidates` from `03_Audio_Library/01_Curated_BGM/` (and list Alternates #2 and #3 in the header, or suggest `/find-music` if the local pool needs a track).
   - Apply the **Studio v2 4-Track Broadcast Audio Mix & Visual Standards** (honoring any Section 5 overrides in `Storyboard.md`):
     - `V1`: 4K video cuts, Ken Burns stills (`EaseIn`/`EaseOut`), and `62%` framed PiP cards (`low_res_broll_mode: pip_card`) over a blurred 4K backdrop for `<1080p` B-roll clips.
     - `V2`: Direct-from-GPX Corner Route Maps (`3.5s` at scene transitions) and smoothed conditional Telemetry HUD (`>= 40 m` grade window, `3s` rolling power; hidden on flat/slow stops).
     - `A1 (Native / Live Dialog)`: Speech-normalized BleeqUP camera dialog (`-22 dB` mean, `0 dB` fader) during spoken exchanges; `-6 dB` during normal riding (`-24 dB` wind gate at $\ge 25\text{ mph}$ / $40\text{ km/h}$); `-6.5 dB` for PiP B-roll music.
     - `A2 (Multi-Phase BGM)`: `-7.5 dB` under Voice-Over (`A4`), swelling `+3.5 dB` (`-4.0 dB`) during pure riding intervals via FilmCraft `v0.17.0+` `essentialSound.generateDucking` (`reduceDb: -3.5`, `fadeS: 0.45`), and muted during live camera dialog or live B-roll music.
     - `A3 (SFX)`: Subtle (`-10 dB`) `peak_ms`-aligned Brehov SFX from `03_Audio_Library/02_SFX/catalog.json` (strictly zero SFX overlapping live speech).
     - `A4 (Replicated Voice-Over)`: Warm scene-synced narration (`voice_jntybwupjc1s`, `-16 LUFS`, `-0.5 dB` fader) in `EN` (plus `UA` and `RU` when `publishing_mode: option_b`).
     - `C1 (Captions)`: Stored in `.fcproj` for `.srt` export, with `burned_in_titles: false` (`burnCaptions: false`) by default so the 4K frames remain 100% clean.
4. Include any YouTube throwback slices (via `fetch_yt_broll_clip.py`) and Section 5 YouTube publishing/thumbnail metadata summary at the bottom of `cut_table.md`.
5. Save the complete Markdown Cut Table to `04_Project_Catalog/YEAR/<project_name>/cut_table.md`, display it in chat, and ask:
   **"Cut Table ready [Genre: `<detected_genre>` | Mode: `<publishing_mode>`]. Reply 'OK' (or run `/assemble-timeline`) to execute timeline assembly in FilmCraft or DaVinci Resolve, reply 'swap music to #2' (or `/find-music`) to change the song, or specify row numbers to adjust."**
