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
1. Read `editing_constitution.md`, `my_digital_brain.md`, the project's `Storyboard.md` (or `Context.md`), and `project_manifest.json`.
2. If `Storyboard.md` is still an unrefined skeleton, run the `/storyboard` visual inspection first and ask the user to confirm the story before building the Cut Table.
3. Map every scene (`Scene 00` through `Scene N`) in `Storyboard.md` into rows of the Cut Table:
   - Quantize non-speech visual cuts to the beat interval (`beat_interval_s`) of the #1 recommended track in `recommended_music_candidates` from `~/Music/Cycling_BGM/` (and list Alternates #2 and #3 in the header, or suggest `/find-music` if the local pool needs a track).
   - Apply the **Music for Video Workflow** mixing levels: `A1` native bike/ambient at `-6 dB` (`-24 dB` when GPX speed $\ge 40\text{ km/h}$), `A2` music baseline at `-15 dB` (`-11 dB` when `A1` is muted, ducked to `-20 dB` during speech), with a `1.5s` intro fade-in and `2.0s` outro fade-out.
4. Include any YouTube throwback slices (via `fetch_yt_broll_clip.py`) and on-screen punchline captions on `V2`.
5. Save the complete Markdown Cut Table to `04_Project_Catalog/YEAR/<project_name>/cut_table.md`, display it in chat, and ask:
   **"Cut Table ready [Genre: `<detected_genre>`]. Reply 'OK' to execute timeline assembly in FilmCraft or DaVinci Resolve, reply 'swap music to #2' (or `/find-music`) to change the song, or specify row numbers to adjust."**
