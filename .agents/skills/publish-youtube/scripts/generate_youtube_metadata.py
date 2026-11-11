#!/usr/bin/env python3
"""
generate_youtube_metadata.py
Automatically generates:
- YouTube Title options (Imperial units by default: mi, ft, mph)
- Chapter-indexed Description (00:00+) in English (en), plus localized Titles & Descriptions
  for Ukrainian (uk) and Russian (ru) family & friends (YouTube native `localizations` schema)
- Multi-language .srt subtitle tracks (captions.en.srt, captions.uk.srt, captions.ru.srt)
- Voice-over narration scripts (narration_script.json) in en, uk, and ru for voice replication
- 1920x1080 Custom Thumbnail (thumbnail.jpg)
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

TICKS_PER_SEC = 254016000000


def fmt_mmss(sec: float) -> str:
    sec = max(0, int(round(sec)))
    m, s = divmod(sec, 60)
    h, m = divmod(m, 60)
    if h > 0:
        return f"{h:d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def fmt_srt_tc(sec: float) -> str:
    sec = max(0.0, float(sec))
    whole = int(sec)
    ms = int(round((sec - whole) * 1000))
    if ms >= 1000:
        whole += 1
        ms -= 1000
    m, s = divmod(whole, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def extract_cues_and_chapters_from_fcproj(fcproj_path: Path):
    """Extracts raw caption cues (for .srt export) and >=10s grouped chapters + A2 music tracks."""
    if not fcproj_path.exists():
        return [], [(0.0, "Intro")], []

    data = json.loads(fcproj_path.read_text(encoding="utf-8"))
    items = data.get("project", {}).get("items", {})
    seq_id = str(data.get("view", {}).get("active_sequence") or 98)
    seq = items.get(seq_id, {}).get("kind", {}).get("Sequence", {})

    raw_cues = []
    for ct in seq.get("caption_tracks", []):
        for cap in ct.get("captions", []):
            st = cap.get("start", 0) / TICKS_PER_SEC
            dur = cap.get("duration", int(3.5 * TICKS_PER_SEC)) / TICKS_PER_SEC
            txt = cap.get("text", "").strip()
            if txt:
                raw_cues.append((st, st + dur, txt))

    raw_cues.sort(key=lambda x: x[0])

    chapters = []
    for st, _end, txt in raw_cues:
        clean_txt = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[·•-]\s*", "", txt)
        if not chapters:
            chapters.append((0.0, clean_txt))
        elif st - chapters[-1][0] >= 10.0:
            chapters.append((st, clean_txt))

    music_tracks = []
    audio_tracks = seq.get("audio_tracks", [])
    if len(audio_tracks) > 1:
        for clip in audio_tracks[1].get("items", []):
            name = clip.get("name", "")
            if name and name not in music_tracks:
                music_tracks.append(name)

    return raw_cues, chapters, music_tracks


def write_srt(cues: list[tuple[float, float, str]], out_path: Path):
    lines = []
    for idx, (st, end, txt) in enumerate(cues, 1):
        lines.append(str(idx))
        lines.append(f"{fmt_srt_tc(st)} --> {fmt_srt_tc(end)}")
        lines.append(txt)
        lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def format_music_credit(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 4:
        bpm, mood, track, artist = parts[0], parts[1], parts[2], parts[3]
        track_spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", track)
        return f'"{track_spaced}" by {artist} ({mood}, {bpm})'
    return stem


def extract_thumbnail(mp4_path: Path, out_jpg: Path, timestamp_sec: float = 51.0):
    if not mp4_path.exists():
        return False
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "/opt/homebrew/bin/ffmpeg",
        "-ss", f"{timestamp_sec:.3f}",
        "-i", str(mp4_path),
        "-vf", "scale=1920:1080",
        "-vframes", "1",
        "-q:v", "2",
        "-update", "1",
        str(out_jpg),
        "-y",
    ]
    subprocess.run(cmd, capture_output=True, check=True)
    return out_jpg.exists()


def generate_composite_thumbnail(
    out_jpg: Path,
    headline_text: str,
    hero_img_path: Path | None = None,
    prop_img_path: Path | None = None,
) -> bool:
    """
    Generates a YouTube Studio 'Ask Suggestions'-style 16:9 composite thumbnail:
    - Blurred scenic background
    - Left foreground: smiling rider / subject portrait
    - Right foreground: white-bordered sticker cutout of the story's key prop
    - Top banner: bold ALL-CAPS yellow/white 3-4 word headline with drop shadow
    Uses Gemini 3 Pro Image (`gemini-3-pro-image`) when GEMINI_API_KEY is available.
    """
    import os
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    try:
        from google import genai
        from google.genai import types
        from PIL import Image

        client = genai.Client(api_key=api_key)
        contents = []
        if hero_img_path and hero_img_path.exists():
            contents.append(Image.open(hero_img_path))
        if prop_img_path and prop_img_path.exists():
            contents.append(Image.open(prop_img_path))

        prompt = (
            f"Create a high-impact 16:9 YouTube thumbnail in the style of YouTube Studio's thumbnail designer. "
            f"Place the smiling cyclist from the first image on the left over a softly blurred coastal background, "
            f"and place a clean white-bordered die-cut sticker cutout of the key prop from the second image on the right. "
            f"Across the top, render the bold ALL-CAPS headline '{headline_text}' in high-contrast yellow and white "
            f"sans-serif typography with a clean dark drop shadow."
        )
        contents.append(prompt)
        resp = client.models.generate_content(
            model="gemini-3-pro-image",
            contents=contents,
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data:
                out_jpg.write_bytes(part.inline_data.data)
                return out_jpg.exists()
    except Exception as e:
        print(f"Warning: AI composite thumbnail generation failed ({e}); falling back to frame extraction.")
    return False


def localize_existing_thumbnail(
    base_jpg: Path,
    out_jpg: Path,
    lang_label: str,
    original_headline: str,
    localized_headline: str,
) -> bool:
    """
    Takes an existing English composite thumbnail.jpg and generates a pixel-matched
    localized edition (thumbnail_ua.jpg / thumbnail_ru.jpg) by replacing ONLY the top
    headline text while keeping the portrait, background, and prop cutout identical.
    """
    import os
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not base_jpg.exists():
        return False
    try:
        from google import genai
        from google.genai import types
        from PIL import Image

        client = genai.Client(api_key=api_key)
        prompt = (
            f"Keep this exact image, cyclist portrait, background, and prop cutout 100% identical, "
            f"and ONLY replace the top text \"{original_headline}\" with the {lang_label} text "
            f"\"{localized_headline}\" in the exact same bold uppercase sans-serif font, size, "
            f"drop shadow, and yellow-white-yellow word color pattern."
        )
        resp = client.models.generate_content(
            model="gemini-3-pro-image",
            contents=[Image.open(base_jpg), prompt],
            config=types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                image_config=types.ImageConfig(aspect_ratio="16:9"),
            ),
        )
        for part in resp.candidates[0].content.parts:
            if part.inline_data:
                out_jpg.write_bytes(part.inline_data.data)
                return out_jpg.exists()
    except Exception as e:
        print(f"Warning: Localized thumbnail generation ({lang_label}) failed: {e}")
    return False


def main():
    p = argparse.ArgumentParser(description="Generate Imperial YouTube metadata, ua/ru localizations & .srt files")
    p.add_argument("--project-dir", required=True, help="Path to 04_Project_Catalog/YEAR/<project_name>")
    p.add_argument("--mp4", required=True, help="Path to rendered master MP4")
    p.add_argument("--thumb-sec", type=float, default=56.5, help="Timestamp in seconds for custom thumbnail")
    p.add_argument("--thumb-mode", choices=["preserve", "composite_ai", "frame"], default="preserve",
                   help="Thumbnail mode: preserve existing thumbnail.jpg, generate composite_ai, or extract frame")
    p.add_argument("--thumb-text", default="SAVED AT THE GATE", help="3-4 word ALL-CAPS headline for EN composite thumbnail")
    p.add_argument("--thumb-text-ua", default="ВРЯТОВАНИЙ БІЛЯ ВОРІТ", help="3-4 word ALL-CAPS headline for UA composite thumbnail")
    p.add_argument("--thumb-text-ru", default="СПАСЁН У ВОРОТ", help="3-4 word ALL-CAPS headline for RU composite thumbnail")
    p.add_argument("--thumb-hero", default=None, help="Hero image path for composite thumbnail")
    p.add_argument("--thumb-prop", default=None, help="Prop image path for composite thumbnail (white-bordered cutout)")
    args = p.parse_args()

    proj_dir = Path(args.project_dir).expanduser().resolve()
    mp4_path = Path(args.mp4).expanduser().resolve()
    project_name = proj_dir.name

    fcproj_path = proj_dir / f"{project_name}.fcproj"
    storyboard_path = proj_dir / "Storyboard.md"

    raw_cues, chapters, music_files = extract_cues_and_chapters_from_fcproj(fcproj_path)
    music_credits = [format_music_credit(m) for m in music_files]

    storyboard_text = storyboard_path.read_text(encoding="utf-8") if storyboard_path.exists() else ""
    # Exclude Section 5 / Published YouTube URLs so the video's own published URLs are never scraped as flashback links
    story_body_only = re.split(r"(?m)^(?:##\s*5\.|###\s*Published YouTube URLs)", storyboard_text)[0]
    yt_links = list(dict.fromkeys(re.findall(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]+", story_body_only)))

    clean_name = project_name.replace("_", " ")
    title_primary = clean_name
    title_alt_1 = f"{clean_name} | Mallorca Cycling & Adventure"
    title_alt_2 = f"{clean_name} — Highlights & Story"
    playlists = ["Mallorca", "2026 Mallorca Cycling"]
    summary_lines = []
    ride_stats = [f"📅 Project: {project_name}"]
    chapters_en = list(chapters)
    localizations = {}
    srt_en, srt_ua, srt_ru = [], [], []
    narration_scripts = {}
    tags = ["Mallorca", "Cycling", "Adventure", "Pro Cycle Hire", "Strava", "San Jose Bicycle Club"]
    hashtags = "#MallorcaCycling #ProCycleHire #CyclingMallorca"

    # 1. Parse Title Options from Section 1 (including optional UA/RU localized titles)
    m_pri = re.search(r"\*\s*\*\*Primary.*?\*\*:?\s*`?([^`\n]+)`?", storyboard_text)
    m_alt1 = re.search(r"\*\s*\*\*Alt 1.*?\*\*:?\s*`?([^`\n]+)`?", storyboard_text)
    m_arch = re.search(r"\*\s*\*\*Archival.*?\*\*:?\s*`?([^`\n]+)`?", storyboard_text)
    m_title_ua = re.search(r"\*\s*\*\*(?:Ukrainian|Title UA|UA).*?\*\*:?\s*`?([^`\n]+)`?", storyboard_text)
    m_title_ru = re.search(r"\*\s*\*\*(?:Russian|Title RU|RU).*?\*\*:?\s*`?([^`\n]+)`?", storyboard_text)
    if m_pri:
        title_primary = m_pri.group(1).strip()
    if m_alt1:
        title_alt_1 = m_alt1.group(1).strip()
    if m_arch:
        title_alt_2 = m_arch.group(1).strip()
    title_ua_parsed = m_title_ua.group(1).strip() if m_title_ua else title_primary
    title_ru_parsed = m_title_ru.group(1).strip() if m_title_ru else title_primary

    # 2. Parse Narrative Summary from Section 1
    m_sum = re.search(r"###\s*Narrative Summary.*?\n(.*?)(?=\n###|\n##|\Z)", storyboard_text, re.DOTALL)
    if m_sum:
        for p in m_sum.group(1).strip().split("\n\n"):
            p_clean = p.strip()
            if p_clean and not p_clean.startswith("- **") and not p_clean.startswith("```"):
                summary_lines.append(p_clean)

    # 3. Parse Metadata Header Lines
    for line in storyboard_text.splitlines()[:25]:
        l_strip = line.strip()
        if l_strip.startswith("**Date:**"):
            ride_stats.append(f"📅 Date: {l_strip.replace('**Date:**', '').strip()}")
        elif l_strip.startswith("**Route:**"):
            ride_stats.append(f"🗺️ Route: {l_strip.replace('**Route:**', '').strip()}")
        elif l_strip.startswith("**Primary Subjects:**"):
            ride_stats.append(f"👥 Companions: {l_strip.replace('**Primary Subjects:**', '').strip()}")
        elif l_strip.startswith("**GPX Track:**"):
            ride_stats.append(f"🚴‍♂️ Telemetry: {l_strip.replace('**GPX Track:**', '').strip()}")

    # 4. Parse Chapters from Section 2 table if not in fcproj
    if not chapters_en:
        for row in re.finditer(r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*`?([0-9.]+)\s*[–-]\s*([0-9.]+)`?\*\*\s*\|\s*`?[0-9.]+s?`?\s*\|\s*([^\|]+)\|\s*([^\|]+)\|", storyboard_text):
            sc_num = row.group(1)
            st_sec = float(row.group(2))
            action_text = row.group(5).strip()
            sc_title = f"Scene {sc_num}: {action_text[:40]}"
            chapters_en.append((st_sec, sc_title))

    # 5. Helper to parse voice-over parts and .srt subtitle cues from Section 4
    def parse_vo_parts_and_srt(text: str, header_regex: str):
        m_sec = re.search(header_regex + r".*?\n(.*?)(?=\n###|\n##|\Z)", text, re.DOTALL)
        if not m_sec:
            return {}, []
        sec_body = m_sec.group(1)
        parts = {}
        cues = []
        pattern = re.compile(
            r"-\s*\*\*(Part|Cue)\s*(\d+)\s*\(`?([0-9.]+)\s*s?\s*[\u2013\u2014-]\s*([0-9.]+)\s*s?`?\):?\*\*:?\s*(.*)"
        )
        for line in sec_body.splitlines():
            m = pattern.match(line.strip())
            if m:
                kind_lbl = m.group(1).lower()
                p_num = m.group(2)
                st = float(m.group(3))
                et = float(m.group(4))
                raw_txt = m.group(5).strip().strip('*').strip('"').strip('«').strip('»').strip()
                key_name = f"cue{int(p_num):02d}" if kind_lbl == "cue" else f"part{p_num}"
                parts[key_name] = raw_txt
                sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", raw_txt) if s.strip()]
                if len(sentences) > 1:
                    total_chars = max(sum(len(s) for s in sentences), 1)
                    cur_st = st
                    dur = et - st
                    for s in sentences:
                        s_dur = dur * (len(s) / total_chars)
                        cues.append((round(cur_st, 1), round(cur_st + s_dur, 1), s))
                        cur_st += s_dur
                else:
                    cues.append((round(st, 1), round(et, 1), raw_txt))
        return parts, cues

    en_parts, srt_en = parse_vo_parts_and_srt(storyboard_text, r"###\s*🇺🇸\s*English Master Script")
    ua_parts, srt_ua = parse_vo_parts_and_srt(storyboard_text, r"###\s*🇺🇦\s*Ukrainian Script")
    ru_parts, srt_ru = parse_vo_parts_and_srt(storyboard_text, r"###\s*🇷🇺\s*Russian Script")

    narration_scripts = {
        "en": en_parts,
        "ua": ua_parts,
        "ru": ru_parts,
    }

    # Build Ukrainian & Russian localizations for YouTube
    if ua_parts:
        ua_desc = "\n\n".join(ua_parts.values())
        localizations["ua"] = {
            "title": title_ua_parsed[:100],
            "description": f"{ua_desc}\n\n#Майорка #Велоспорт #ProCycleHire",
        }
    if ru_parts:
        ru_desc = "\n\n".join(ru_parts.values())
        localizations["ru"] = {
            "title": title_ru_parsed[:100],
            "description": f"{ru_desc}\n\n#Майорка #Велоспорт #ProCycleHire",
        }

    desc_parts = []
    desc_parts.extend(summary_lines)
    desc_parts.append("")
    desc_parts.append("━━━━━━━━━━━━━━━━━━━━")
    desc_parts.append("📊 RIDE & TRIP NOTES (IMPERIAL & METRIC)")
    desc_parts.extend(ride_stats)

    if chapters_en:
        desc_parts.append("")
        desc_parts.append("━━━━━━━━━━━━━━━━━━━━")
        desc_parts.append("⏱️ CHAPTERS")
        for st, label in chapters_en:
            desc_parts.append(f"{fmt_mmss(st)} {label}")

    if yt_links:
        desc_parts.append("")
        desc_parts.append("━━━━━━━━━━━━━━━━━━━━")
        desc_parts.append("🔗 RELATED / FLASHBACK VIDEOS")
        for link in yt_links:
            desc_parts.append(f"• Flashback clip featured in this video: {link}")

    if music_credits:
        desc_parts.append("")
        desc_parts.append("━━━━━━━━━━━━━━━━━━━━")
        desc_parts.append("🎵 MUSIC")
        for mc in music_credits:
            desc_parts.append(f"• {mc}")

    # Preserve existing published URL and edition_urls if already registered
    json_out = proj_dir / "youtube_metadata.json"
    existing_url, existing_vid, existing_editions = None, None, {}
    if json_out.exists():
        try:
            old = json.loads(json_out.read_text(encoding="utf-8"))
            existing_url = old.get("published_youtube_url")
            existing_vid = old.get("published_video_id")
            existing_editions = old.get("edition_urls") or {}
        except Exception:
            pass

    if localizations.get("ua") or localizations.get("ru"):
        desc_parts.append("")
        desc_parts.append("━━━━━━━━━━━━━━━━━━━━")
        if localizations.get("ua"):
            desc_parts.append("🇺🇦 УКРАЇНСЬКОЮ")
            if existing_editions.get("ua"):
                ua_line = f"🔊 Повна версія з українською озвучкою: {existing_editions['ua']}"
                desc_parts.append(ua_line)
                desc_parts.append("")
                localizations["ua"]["description"] = f"{ua_line}\n\n" + localizations["ua"]["description"]
            desc_parts.append(localizations["ua"]["title"])
            desc_parts.append("")
            desc_parts.append(localizations["ua"]["description"].split("\n\n⏱️")[0].replace(f"🔊 Повна версія з українською озвучкою: {existing_editions.get('ua', '')}\n\n", ""))
        if localizations.get("ru"):
            desc_parts.append("")
            desc_parts.append("━━━━━━━━━━━━━━━━━━━━")
            desc_parts.append("🇷🇺 ПО-РУССКИ")
            if existing_editions.get("ru"):
                ru_line = f"🔊 Полная версия с русской озвучкой: {existing_editions['ru']}"
                desc_parts.append(ru_line)
                desc_parts.append("")
                localizations["ru"]["description"] = f"{ru_line}\n\n" + localizations["ru"]["description"]
            desc_parts.append(localizations["ru"]["title"])
            desc_parts.append("")
            desc_parts.append(localizations["ru"]["description"].split("\n\n⏱️")[0].replace(f"🔊 Полная версия с русской озвучкой: {existing_editions.get('ru', '')}\n\n", ""))

    desc_parts.append("")
    desc_parts.append(hashtags)
    description_text = "\n".join(desc_parts)

    # Write .srt subtitle files (using ISO country code `ua` for Ukraine)
    srt_files = {}
    en_cues_to_write = srt_en if srt_en else raw_cues
    if en_cues_to_write:
        en_srt = proj_dir / "captions.en.srt"
        write_srt(en_cues_to_write, en_srt)
        srt_files["en"] = "captions.en.srt"
    if srt_ua:
        ua_srt = proj_dir / "captions.ua.srt"
        write_srt(srt_ua, ua_srt)
        srt_files["ua"] = "captions.ua.srt"
    if srt_ru:
        ru_srt = proj_dir / "captions.ru.srt"
        write_srt(srt_ru, ru_srt)
        srt_files["ru"] = "captions.ru.srt"

    if narration_scripts:
        (proj_dir / "narration_scripts.json").write_text(
            json.dumps(narration_scripts, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # Parse Section 5 thumbnail spec from Storyboard.md if present
    sb_thumb_cfg = {}
    if storyboard_path.exists():
        try:
            m_th = re.search(r"thumbnail:\s*\n((?:\s{2,}.*\n?)+)", storyboard_text)
            if m_th:
                for line in m_th.group(1).splitlines():
                    if ":" in line:
                        k, v = line.split(":", 1)
                        sb_thumb_cfg[k.strip()] = v.strip().strip("\"'")
        except Exception:
            pass

    thumb_headline = args.thumb_text or sb_thumb_cfg.get("headline_text", "THE 140 BPM RULE")
    thumb_headline_ua = args.thumb_text_ua or sb_thumb_cfg.get("headline_text_ua", "ПРАВИЛО 140 УДАРІВ")
    thumb_headline_ru = args.thumb_text_ru or sb_thumb_cfg.get("headline_text_ru", "ПРАВИЛО 140 УДАРОВ")

    thumb_path = proj_dir / "thumbnail.jpg"
    thumb_ok = False
    if args.thumb_mode == "preserve" and thumb_path.exists():
        thumb_ok = True
    elif args.thumb_mode in ("composite_ai", "preserve"):
        hero_p = Path(args.thumb_hero).expanduser() if args.thumb_hero else None
        prop_p = Path(args.thumb_prop).expanduser() if args.thumb_prop else None
        if not hero_p and (proj_dir / "thumb_candidates" / "alexander_selfie.jpg").exists():
            hero_p = proj_dir / "thumb_candidates" / "alexander_selfie.jpg"
        thumb_ok = generate_composite_thumbnail(thumb_path, thumb_headline, hero_p, prop_p)
        if not thumb_ok and not thumb_path.exists():
            thumb_ok = extract_thumbnail(mp4_path, thumb_path, args.thumb_sec)
    else:
        thumb_ok = extract_thumbnail(mp4_path, thumb_path, args.thumb_sec)

    thumb_ua_path = proj_dir / "thumbnail_ua.jpg"
    thumb_ru_path = proj_dir / "thumbnail_ru.jpg"
    if thumb_ok and not thumb_ua_path.exists() and thumb_headline_ua:
        localize_existing_thumbnail(thumb_path, thumb_ua_path, "Ukrainian", thumb_headline, thumb_headline_ua)
    if thumb_ok and not thumb_ru_path.exists() and thumb_headline_ru:
        localize_existing_thumbnail(thumb_path, thumb_ru_path, "Russian", thumb_headline, thumb_headline_ru)

    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", project_name)
    recording_date_iso = f"{m_date.group(1)}T00:00:00.000Z" if m_date else None

    metadata = {
        "project_name": project_name,
        "recording_date": recording_date_iso,
        "video_file": mp4_path.name,
        "thumbnail_file": thumb_path.name if thumb_ok else None,
        "thumbnail_timestamp_sec": args.thumb_sec,
        "title": title_primary,
        "title_ua": localizations.get("ua", {}).get("title"),
        "title_ru": localizations.get("ru", {}).get("title"),
        "title_alternatives": [title_alt_1, title_alt_2],
        "playlists": playlists,
        "description": description_text,
        "localizations": localizations,
        "srt_files": srt_files,
        "narration_scripts": narration_scripts,
        "tags": tags,
        "category_id": "17",
        "privacy_status": "private",
        "made_for_kids": False,
        "chapters": [{"start_sec": round(st, 1), "timecode": fmt_mmss(st), "title": lbl} for st, lbl in chapters_en],
        "music_credits": music_credits,
        "related_youtube_links": yt_links,
    }
    if existing_url:
        metadata["published_youtube_url"] = existing_url
    if existing_vid:
        metadata["published_video_id"] = existing_vid
    if existing_editions:
        metadata["edition_urls"] = existing_editions

    json_out.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved YouTube metadata JSON (Imperial + uk/ru localizations) -> {json_out}")
    print(f"Saved .srt subtitle tracks -> {list(srt_files.keys())}")

    # Generate Facebook promotional copy options
    try:
        from generate_facebook_promo import build_facebook_promo, print_promo_box
        promo = build_facebook_promo(proj_dir, metadata, live_url=existing_url, edition_urls=existing_editions)
        print(f"Saved Facebook promotional copy -> {proj_dir / 'facebook_promo.md'}")
    except Exception as e:
        print(f"Note: Facebook promo generation notice: {e}")


if __name__ == "__main__":
    main()
