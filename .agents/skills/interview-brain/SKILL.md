---
name: interview-brain
description: Conducts an interactive Q&A interview session to build and enrich my_digital_brain.md across life eras (1977+ B&W film photography, 1980-1984 university classmates, family/parties, hikes, and Mallorca/California cycling) and links matching Lightroom folders.
---

# Interactive Digital Brain Q&A Builder (`/interview-brain`)

## Quota Guardrail
Always run this conversational skill on **Gemini 3.8 Flash** so multi-turn Q&A interviews consume **0%** of the 5-hour Gemini 4 Argon quota.

## Interview Protocol
1. Read `./my_digital_brain.md` to see which life chapters or project domains already have notes and which have open placeholders.
2. Ask Alexander which memory domain he wants to expand today (or use the argument passed to `/interview-brain`), choosing from:
   - **1977+ Photography & B&W Film Era:** First cameras, darkroom/scanning stories, favorite 1970s/1980s rolls, and where they sit on `Crucial-4T`.
   - **1980–1984 University Classmates:** University/faculty name, key classmates and inside stories, memorable excursions, and which Lightroom folders/collections hold those scans.
   - **Parties, Family & Social Gatherings:** Recurring family/friend traditions, key people to recognize in photos, and favorite musical moods.
   - **Hikes & Outdoor Travel:** Favorite trails in California (Big Sur, Bay Area) and Europe, travel companions, and storytelling preferences.
   - **Cycling Crew & Routes (Mallorca PCH & SJBC):** Stories behind the Mallorca crew, favorite coffee stops (Búger, Ses Muralles, Petra, Can Picafort, Sa Batalla, Pollença), and bikes.
3. **Ask only 1 or 2 focused questions per turn.** Keep the conversation natural and concise.
4. If Alexander mentions a folder or collection name, search `00_Archive_Indexes/lightroom_stock_index.json` or `00_Archive_Indexes/youtube_motion_index.jsonl` via `grep`/`jq` to link the exact file paths into `my_digital_brain.md`.
5. After every 2–3 answers (or when Alexander says `"done"`), update `my_digital_brain.md` in place with clean, structured Markdown bullet points and confirm what was saved.
