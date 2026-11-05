#!/usr/bin/env python3
"""
generate_facebook_promo.py — Generates high-converting, Facebook-algorithm-optimized promotional copy
for Alexander Komlik's YouTube releases.

Features:
  - Option 1 (Curiosity Hook / Algorithm Optimized): No outbound link in post body (avoids FB reach penalty)
    + cliffhanger ending + copy-ready First Comment with YouTube link and edition notes.
  - Option 2 (Direct Story Narrative): Engaging narrative with emoji bullet highlights and direct link.
  - Option 3 (Bilingual / Classmates): English story hook + UA/RU localized notes for European/UA classmates.
  - Updates `youtube_metadata.json` ("facebook_promo" key) and saves `facebook_promo.md`.
  - Can be invoked standalone, imported by `generate_youtube_metadata.py`, or called by `upload_youtube_api.py`.
"""

import argparse
import json
import re
from pathlib import Path


def build_facebook_promo(
    project_dir: Path,
    meta: dict | None = None,
    live_url: str | None = None,
    edition_urls: dict | None = None,
) -> dict:
    project_dir = Path(project_dir).expanduser().resolve()
    project_name = project_dir.name

    if meta is None:
        json_p = project_dir / "youtube_metadata.json"
        if json_p.exists():
            try:
                meta = json.loads(json_p.read_text(encoding="utf-8"))
            except Exception:
                meta = {}
        else:
            meta = {}

    yt_url = live_url or meta.get("published_youtube_url") or "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
    editions = edition_urls or meta.get("edition_urls") or {}

    title = meta.get("title", project_name.replace("_", " "))
    desc = meta.get("description", "")
    chapters = meta.get("chapters", [])
    locs = meta.get("localizations", {})

    has_ua = bool(editions.get("ua") or locs.get("ua"))
    has_ru = bool(editions.get("ru") or locs.get("ru"))
    lang_note = ""
    if has_ua and has_ru:
        lang_note = "(🇺🇦 & 🇷🇺 editions with author voiceover linked in the pinned YouTube comment)"
    elif has_ua:
        lang_note = "(🇺🇦 Українська версія з авторським закадровим голосом у закріпленому коментарі)"

    # Check project-specific curated storytelling
    if "SaPobla_Market_Trip" in project_name:
        opt1_body = (
            "Four years ago at the Sa Pobla market, I bought a fleece jacket that became my favorite travel companion until I lost it on a flight to San Jose.\n\n"
            "This Sunday, Nina and I took the 302 bus back to Sa Pobla on a mission: find that exact same vendor in Plaça Major.\n\n"
            "Not only was he still there... but he had a surprise waiting for us at checkout that made the entire bus ride completely unnecessary. 😂\n\n"
            "(Link to the 3-minute video saga in the first comment below! 👇)"
        )
        opt1_comment = (
            f"🎬 Watch the 3-minute video here (featuring the jacket haggle, the toughest steak in Alcúdia, and fresh Llampuga): {yt_url}\n"
            + (f"{lang_note}" if lang_note else "")
        ).strip()

        opt2_body = (
            "The quest: Catch the 302 bus inland to Sa Pobla to track down the exact market vendor who sold me my favorite olive fleece four years ago (which I carelessly left on a plane to San Jose).\n\n"
            "Against all odds, the man was standing in the exact same spot on Plaça Major.\n\n"
            "What followed was a masterclass in Mallorca reality:\n"
            "• 4 years of inflation (+50% price hike)\n"
            "• The vendor dropping the ultimate deadpan revelation right as we paid\n"
            "• A lunch battle with the toughest entrecôte in Alcúdia (prompting immediate peace offerings of complimentary house wine)\n"
            "• And sweet redemption at Forn Can Torres 🥐\n\n"
            f"Full 3-minute mini-movie of Sunday’s expedition:\n👉 {yt_url}"
        )

        opt3_body = (
            "Sunday mission in Mallorca: take the 302 bus to Sa Pobla to replace my favorite fleece jacket lost on a flight to San Jose.\n\n"
            "Found the exact same vendor at the exact same spot on Plaça Major! Though four years of inflation bumped it from €20 to €30, the real punchline came right as we handed over the cash...\n\n"
            "Add in a Sunday lunch featuring an un-chewable steak and complimentary peacemaking wine, and you have a classic island adventure.\n\n"
            f"🎬 3-minute video: {yt_url}\n"
            "(🇺🇦 & 🇷🇺 версії з авторським закадровим голосом — у закріпленому коментарі на YouTube!)"
        )

    elif "Nina_Pollenca_Loop" in project_name:
        opt1_body = (
            "Monday morning rollout from Alcúdia, escorting Nina on bikes to her outdoor Zumba session at the Bellevue courts below Puig de Sant Martí.\n\n"
            "Right as I rolled up to the court gate to say goodbye, Nina stopped me in my tracks with six words: \"Something just fell off your bike!\"\n\n"
            "Turned out her sharp eyes had just saved my entire ride—and quite possibly my collarbone. 🚴‍♂️💨\n\n"
            "(Link to the 1-minute video in the first comment below! 👇)"
        )
        opt1_comment = (
            f"🎬 Watch the 1-minute video here: {yt_url}\n"
            "Featuring Nina's live catch at the gate, the blue Reynolds carbon pad re-seat, and a 21.5 mi loop around Pollença Bay!\n"
            + (f"{lang_note}" if lang_note else "")
        ).strip()

        opt2_body = (
            "Monday morning ride from Port d'Alcúdia, escorting Nina past the horse paddocks to her outdoor Zumba class at Bellevue.\n\n"
            "Right at the tennis court gate, Nina's sharp eyes saved my day: she spotted my blue front disc brake pad lying on the pebble ground right after it slipped out of the caliper!\n\n"
            "Popped it back in by hand, took a peaceful 21.5-mile cruise around Badia de Pollença past Pro Cycle Hire, and hauled an Eroski grocery run home in my San Jose Bicycle Club musette.\n\n"
            f"🎬 Watch the ride (1 min):\n👉 {yt_url}"
        )

        opt3_body = (
            "Monday ride escorting Nina to Zumba & 21.5 mi Pollença Loop: right at the Bellevue gate, Nina spotted my front brake pad lying on the ground after it slipped out! Popped it back in by hand and finished a great coastal loop.\n\n"
            "Понеділковий виїзд: проводжав Ніну на Зумбу в Bellevue, і просто біля воріт корту Ніна врятувала мою поїздку — помітила на землі передню гальмівну колодку, яка щойно випала!\n\n"
            f"🎬 Video (1 min): {yt_url}\n"
            "(🇺🇦 & 🇷🇺 версії з авторським закадровим голосом — у закріпленому коментарі на YouTube!)"
        )

    else:
        # Generic algorithmic synthesizer for future projects
        clean_title = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[·\-–]\s*", "", title)
        # Extract first 2 narrative paragraphs from description
        desc_paras = [p.strip() for p in desc.split("\n\n") if p.strip() and not p.startswith("━") and not p.startswith("📊") and not p.startswith("⏱️") and not p.startswith("🎵") and not p.startswith("#")]
        lead_summary = desc_paras[0] if desc_paras else f"Highlights and scenes from {clean_title}."
        second_summary = desc_paras[1] if len(desc_paras) > 1 else ""

        opt1_body = (
            f"{lead_summary}\n\n"
            + (f"{second_summary}\n\n" if second_summary else "")
            + "(Link to the full video in the first comment below! 👇)"
        )
        opt1_comment = (
            f"🎬 Watch the full video here: {yt_url}\n"
            + (f"{lang_note}" if lang_note else "")
        ).strip()

        bullet_points = []
        for ch in chapters[:4]:
            lbl = ch.get("title", "") if isinstance(ch, dict) else ch[1]
            if lbl and not lbl.startswith("202"):
                bullet_points.append(f"• {lbl}")

        bullets_str = "\n".join(bullet_points) if bullet_points else f"• {clean_title}"
        opt2_body = (
            f"{lead_summary}\n\n"
            f"Highlights:\n{bullets_str}\n\n"
            f"🎬 Watch the full video:\n👉 {yt_url}"
        )

        ua_lead = locs.get("ua", {}).get("description", "").split("\n\n")[0] if locs.get("ua") else ""
        opt3_body = (
            f"{lead_summary}\n\n"
            + (f"{ua_lead}\n\n" if ua_lead else "")
            + f"🎬 Video: {yt_url}\n"
            + (f"{lang_note}" if lang_note else "")
        ).strip()

    promo_data = {
        "project_name": project_name,
        "youtube_url": yt_url,
        "options": {
            "option_1_curiosity_hook": {
                "name": "Option 1: The Curiosity Hook (Algorithm-Optimized)",
                "description": "Zero external links in post body (avoids FB reach suppression) + curiosity cliffhanger. Post YouTube link in the first comment.",
                "post_text": opt1_body,
                "first_comment": opt1_comment,
            },
            "option_2_direct_story": {
                "name": "Option 2: Direct Story Narrative (All-in-One)",
                "description": "Engaging narrative with bullet highlights and YouTube link embedded directly in the post.",
                "post_text": opt2_body,
            },
            "option_3_bilingual": {
                "name": "Option 3: Bilingual / Classmates Edition",
                "description": "English narrative hook + UA/RU localized context for European and Ukrainian friends.",
                "post_text": opt3_body,
            },
        },
    }

    # Write facebook_promo.md
    md_content = f"""# 📱 Facebook Promotional Copy: `{project_name}`

> **Target Video:** [{title}]({yt_url})  
> **Facebook Best Practice:** Use **Option 1** with 1–3 still photos attached natively to the Facebook post, then paste the link into the **First Comment** to avoid Facebook's outbound link reach penalty.

---

## 🚀 Option 1: The Curiosity Hook (Algorithm-Optimized — Recommended)
*Attach 1–3 still photos from the project, post this text, then immediately add the first comment below:*

### 📝 Post Text:
```text
{opt1_body}
```

### 💬 First Comment:
```text
{opt1_comment}
```

---

## 📖 Option 2: Direct Story Narrative (All-in-One)
*Single-step post with the YouTube link directly in the post body:*

### 📝 Post Text:
```text
{opt2_body}
```

---

## 🌍 Option 3: Bilingual / Classmates Edition
*Optimized for both Silicon Valley friends and Ukrainian/European classmates:*

### 📝 Post Text:
```text
{opt3_body}
```
"""

    md_out = project_dir / "facebook_promo.md"
    md_out.write_text(md_content, encoding="utf-8")

    # Update youtube_metadata.json if it exists
    json_p = project_dir / "youtube_metadata.json"
    if json_p.exists():
        try:
            curr_json = json.loads(json_p.read_text(encoding="utf-8"))
            curr_json["facebook_promo"] = promo_data
            json_p.write_text(json.dumps(curr_json, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            print(f"Warning updating youtube_metadata.json: {e}")

    return promo_data


def print_promo_box(promo: dict):
    opts = promo.get("options", {})
    opt1 = opts.get("option_1_curiosity_hook", {})
    opt2 = opts.get("option_2_direct_story", {})
    opt3 = opts.get("option_3_bilingual", {})

    print("\n========================================================")
    print("📱 SUGGESTED FACEBOOK PROMOTIONAL COPY")
    print("========================================================")
    print("💡 Recommended Strategy (Algorithm-Optimized):")
    print("   Post Option 1 text (with 1-3 project photos), then paste")
    print("   the link into the FIRST COMMENT to avoid FB reach penalties.\n")
    print("--- [OPTION 1: POST TEXT] ---")
    print(opt1.get("post_text", "").strip())
    print("\n--- [OPTION 1: FIRST COMMENT] ---")
    print(opt1.get("first_comment", "").strip())
    print("\n--- [OPTION 2: DIRECT ALL-IN-ONE POST] ---")
    print(opt2.get("post_text", "").strip())
    print("\nSaved full copy options -> facebook_promo.md")
    print("========================================================\n")


def main():
    parser = argparse.ArgumentParser(description="Generate copy-ready Facebook promo options for a project")
    parser.add_argument("--project-dir", required=True, help="Path to project directory")
    parser.add_argument("--url", help="Live YouTube URL (optional, overrides metadata)")
    args = parser.parse_args()

    p_dir = Path(args.project_dir).expanduser().resolve()
    promo = build_facebook_promo(p_dir, live_url=args.url)
    print_promo_box(promo)


if __name__ == "__main__":
    main()
