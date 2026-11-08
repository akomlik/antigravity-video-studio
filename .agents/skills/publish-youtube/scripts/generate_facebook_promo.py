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
        flickr_url = meta.get("published_flickr_url", "")
        flickr_line = f"\n🇷🇺 На русском языке (Flickr): {flickr_url}" if flickr_url else ""

        opt1_body = (
            f"{lead_summary}\n\n"
            + (f"{second_summary}\n\n" if second_summary else "")
            + f"🎬 Watch the 4K video on YouTube:\n{yt_url}"
            + flickr_line
        )
        opt1_comment = ""

        bullet_points = []
        for ch in chapters[:4]:
            lbl = ch.get("title", "") if isinstance(ch, dict) else ch[1]
            if lbl and not lbl.startswith("202"):
                bullet_points.append(f"• {lbl}")

        bullets_str = "\n".join(bullet_points) if bullet_points else f"• {clean_title}"
        opt2_body = (
            f"{lead_summary}\n\n"
            f"Highlights:\n{bullets_str}\n\n"
            f"🎬 Watch the full video:\n{yt_url}"
            + flickr_line
        )

        ua_lead = locs.get("ua", {}).get("description", "").split("\n\n")[0] if locs.get("ua") else ""
        opt3_body = (
            f"{lead_summary}\n\n"
            + (f"{ua_lead}\n\n" if ua_lead else "")
            + f"🎬 Video: {yt_url}\n"
            + (f"{lang_note}" if lang_note else "")
        ).strip()

    # Build Flickr Russian Publishing Metadata
    ru_title = locs.get("ru", {}).get("title", title)
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", project_name)
    date_str = date_match.group(1) if date_match else ""
    flickr_title = f"{date_str} · {ru_title}" if date_str and not ru_title.startswith(date_str) else ru_title

    ru_desc = locs.get("ru", {}).get("description", desc)
    clean_ru_desc = "\n\n".join(
        [p.strip() for p in ru_desc.split("\n\n") if p.strip() and not p.strip().startswith(("#", "http", "🎵", "🔊", "━━━━━━━━"))][:4]
    )

    flickr_tags = ["Mallorca", "cycling", "roadbike", "BleeqUP", "video"]
    for t in meta.get("tags", []):
        if t not in flickr_tags and len(flickr_tags) < 12:
            flickr_tags.append(t)
    tags_str = ", ".join(flickr_tags)
    ru_video_file = f"{project_name}_RU.mp4"

    flickr_data = {
        "target_file": ru_video_file,
        "title": flickr_title,
        "description": clean_ru_desc,
        "tags": tags_str,
        "album": "2026 Fall Mallorca Cycling",
    }

    # Option 4: Mallorca Cycling Facebook Group Edition (73.4K Members Community Standard)
    # Strictly non-commercial, road & cafe intel, peer rider tone, first comment link
    opt4_body = ""
    opt4_comment = ""
    is_mallorca = "Mallorca" in title or "mallorca" in str(project_dir).lower() or any(
        kw in desc.lower() for kw in ["mallorca", "alcúdia", "alcudia", "pollença", "pollenca", "buger", "sa pobla", "caimari", "lluc"]
    )

    if "Buger_coffee" in project_name:
        opt4_body = (
            "Decided to skip the brisk early Tuesday group rollout from Port de Pollença this week and wait at home in Malpas-Bonaire until the sun actually warmed up the tarmac.\n\n"
            "Rolled out solo on a quiet 40-mile loop (64 km / 515 m) across the Sa Pobla flatlands and up to Búger.\n\n"
            "If you haven't stopped at Forn Can Rafel in the village square (Plaça de la Constitució), it's well worth the gentle climb. Fresh ensaïmades and chocolate pastries, outdoor tables right under the church clock tower, and none of the crowds you get on the main cycling arteries. Right by the square is the famous cascading stone fountain—great spot to refill bottles or cool off on warmer days.\n\n"
            "On the way back, instead of taking the busy main road, I took Camí Vell de Pollença—a peaceful, narrow lane between ancient dry stone walls and olive groves that connects up toward Pollença, before spinning along the bay into Port de Pollença.\n\n"
            "How are the morning road temps treating everyone this week? Are you still starting early or waiting for the sun to break through?\n\n"
            "(Photos attached; short 2-minute ride recap in the first comment 👇)"
        )
        opt4_comment = (
            f"🚴 Short 2-minute 4K ride recap (Búger village square, Camí Vell de Pollença & coastal return): {yt_url}\n"
            "Clean 4K with captions & multi-language voiceover options in the video description."
        )
    elif "SaPobla_Market_Trip" in project_name:
        opt4_body = (
            "Took a rest-day recovery excursion to the Sa Pobla Sunday market (Plaça Major) via the 302 bus from Alcúdia.\n\n"
            "If you ever need a break from the bike or want to stock up on local produce, Sunday morning in Sa Pobla is pure Mallorca. Fresh oranges, local cheeses, pastries, and roasted nuts, without the tourist tour-bus crowds of some of the larger coastal markets.\n\n"
            "For coffee, Bar Casa Miss right on the square is classic (though packed on Sundays!).\n\n"
            "What's your favorite local village market on the island for non-riding days?\n\n"
            "(Couple photos attached; short 3-minute video in the first comment 👇)"
        )
        opt4_comment = f"☕ 3-minute video of the Sunday market trip: {yt_url}"
    elif "Nina_Pollenca_Loop" in project_name:
        opt4_body = (
            "Quick 21-mile morning spin (34 km) from Port d'Alcúdia around Badia de Pollença, riding the quiet lanes below Puig de Sant Martí and Ranxo Ses Roques before looping through Pollença and along the bay path.\n\n"
            "The coastal bike path along Can Cullerassa is in great shape right now—crisp autumn morning air and very light traffic once the early commuters clear out.\n\n"
            "A quick reminder for everyone doing maintenance before winter: double check your brake pad retaining pins! Rolled backward slightly at a gate and almost lost a front carbon pad on the tarmac—luckily spotted before hitting any descents!\n\n"
            "Anyone else making the most of the quiet autumn roads around Pollença bay this week?\n\n"
            "(Photos attached; ride video in the first comment 👇)"
        )
        opt4_comment = f"🎬 Short 4K ride recap: {yt_url}"
    elif is_mallorca:
        has_pch = "pro cycle" in desc.lower() or "pch" in project_name.lower()
        pch_tag = " with #procyclehire" if has_pch else ""
        opt4_body = (
            f"Awesome morning ride on the island today{pch_tag}! 🚴💪👍 — {title}\n\n"
            f"{yt_url}"
        )
        opt4_comment = ""

    promo_data = {
        "project_name": project_name,
        "youtube_url": yt_url,
        "options": {
            "option_1_direct_card": {
                "name": "Option 1: Direct YouTube Link Card (Personal Feed — Recommended)",
                "description": "Paste directly with the YouTube URL (do not attach separate photos so Facebook renders the full-width clickable 16:9 YouTube thumbnail card).",
                "post_text": opt1_body,
            },
            "option_2_direct_story": {
                "name": "Option 2: Story + Highlights + Direct Link",
                "description": "Engaging narrative with chapter highlights and YouTube link embedded directly in the post.",
                "post_text": opt2_body,
            },
            "option_3_bilingual": {
                "name": "Option 3: Bilingual / Classmates Edition",
                "description": "English narrative hook + UA/RU localized context for European and Ukrainian friends.",
                "post_text": opt3_body,
            },
        },
        "flickr": flickr_data,
    }

    if opt4_body:
        promo_data["options"]["option_4_mallorca_cycling_group"] = {
            "name": "Option 4: Mallorca Cycling Facebook Group (Direct YouTube Preview Card)",
            "description": "Short punchy rider note + #procyclehire + direct YouTube URL so Facebook renders the full-width clickable 16:9 video preview card.",
            "post_text": opt4_body,
        }

    # Write facebook_promo.md
    md_content = f"""# 📱 Social Promotional Copy: `{project_name}`

> **Target Video:** [{title}]({yt_url})  
> **Facebook Best Practice (Proven 265+ Views Standard):** Paste the **direct YouTube URL** inside the post body **without attaching separate photos** so Facebook renders the full-width clickable 16:9 `YOUTUBE.COM` thumbnail card!

---

## 🚀 Option 1: Direct YouTube Link Card (Personal Feed — Recommended)
*Paste directly into Facebook (do not attach separate photos so the full-bleed clickable YouTube card renders):*

### 📝 Post Text:
```text
{opt1_body}
```

---

## 📖 Option 2: Story + Highlights + Direct Link
*Narrative + chapter bullet points + direct YouTube & Flickr links:*

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

---

{f'''## 🚴 Option 4: Mallorca Cycling Facebook Group (Direct YouTube Preview Card)
*Proven format (70+ likes, 265+ views): short rider note + `#procyclehire` + direct YouTube URL so the full-width clickable `YOUTUBE.COM` preview card renders:*

### 📝 Post Text:
```text
{opt4_body}
```

---''' if opt4_body else ''}

## 📸 Flickr Video Upload (RU Edition for Family & Classmates in RU/Crimea)
*Direct 4K video upload for Nina's brother, Alexander's sister in Sevastopol, and WhatsApp classmates who face YouTube restrictions:*

- **Target File:** `~/Movies/Exports/2026/{ru_video_file}` (Russian Voiced Edition)
- **Flickr Title:** `{flickr_title}`
- **Flickr Description:**
```text
{clean_ru_desc}
```
- **Flickr Tags:** `{tags_str}`
- **Recommended Album:** `2026 Fall Mallorca Cycling` (Lightroom / Flickr Publishing Service)
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
    opt1 = opts.get("option_1_direct_card", opts.get("option_1_curiosity_hook", {}))
    opt2 = opts.get("option_2_direct_story", {})
    opt4 = opts.get("option_4_mallorca_cycling_group", {})

    print("\n========================================================")
    print("📱 SUGGESTED FACEBOOK PROMOTIONAL COPY")
    print("========================================================")
    print("💡 Proven Strategy (265+ Views Standard):")
    print("   Paste directly WITH the YouTube link (and no extra photos)")
    print("   so Facebook renders the giant clickable 16:9 YOUTUBE.COM card!\n")
    print("--- [OPTION 1: PERSONAL FEED (DIRECT LINK CARD)] ---")
    print(opt1.get("post_text", "").strip())
    if opt4:
        print("\n--- [OPTION 4: MALLORCA CYCLING GROUP (DIRECT LINK CARD)] ---")
        print(opt4.get("post_text", "").strip())
    print("\n--- [OPTION 2: STORY + HIGHLIGHTS + DIRECT LINK] ---")
    print(opt2.get("post_text", "").strip())

    flickr = promo.get("flickr", {})
    if flickr:
        print("\n========================================================")
        print("📸 FLICKR PUBLISHING (RU EDITION FOR FAMILY/CLASSMATES)")
        print("========================================================")
        print(f"Target Video: ~/Movies/Exports/2026/{flickr.get('target_file')}")
        print(f"Title:        {flickr.get('title')}")
        print(f"Tags:         {flickr.get('tags')}")
        print(f"Album:        {flickr.get('album')}")

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
