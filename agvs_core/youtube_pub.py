"""YouTube Data API v3 publisher, Imperial-first metadata generator, SHA-256 `.srt` hash caching, and Facebook promo copy."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from agvs_core.config import find_binary, get_exports_dir, get_studio_root

TICKS_PER_SEC = 254016000000
DEFAULT_YOUTUBE_PRIVACY_STATUS = "unlisted"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

OAUTH_DIR = Path("~/.config/antigravity_youtube").expanduser()
TOKEN_FILE = OAUTH_DIR / "token.json"

YT_WIRE_LANG = {"en": "en", "ua": "uk", "ru": "ru"}
YT_LANG_NAMES = {"en": "English", "ua": "Українська (UA)", "ru": "Русский"}


def to_youtube_bcp47_lang(lang: str) -> str:
    """Map Studio local language code (`ua`) to YouTube Data API v3 BCP-47 wire code (`uk`)."""
    clean = (lang or "en").strip().lower()
    return YT_WIRE_LANG.get(clean, clean)


def get_yt_index_path() -> Path:
    return get_studio_root() / "00_Archive_Indexes" / "youtube_motion_index.jsonl"


def compute_srt_sha256(srt_path: Path) -> str:
    return hashlib.sha256(srt_path.read_bytes()).hexdigest()


def resolve_thumbnail_headline(
    cli_thumb_text: str | None,
    storyboard_thumb_cfg: dict[str, Any] | None = None,
    key: str = "headline_text",
    fallback: str = "MALLORCA CYCLING",
) -> str:
    """Honor explicit CLI `--thumb-text` when provided; otherwise read Storyboard Section 5 `headline_text`."""
    if cli_thumb_text is not None and str(cli_thumb_text).strip():
        return str(cli_thumb_text).strip()
    if storyboard_thumb_cfg and storyboard_thumb_cfg.get(key):
        val = str(storyboard_thumb_cfg[key]).strip()
        if val:
            return val
    return fallback


def should_skip_video_insert_on_resume(
    meta: dict[str, Any],
    force_reupload: bool = False,
    edition_key: str | None = None,
) -> bool:
    """
    Prevent duplicate 1,600-quota-unit `videos.insert` calls when resuming a partially completed
    upload where `published_video_id` (or `edition_urls[edition_key]`) was already persisted.
    """
    if force_reupload:
        return False
    if edition_key:
        ed_urls = meta.get("edition_urls") or {}
        return bool(ed_urls.get(edition_key))
    return bool(meta.get("published_video_id") or meta.get("youtube_video_id"))


def fmt_mmss(sec: float) -> str:
    sec_i = max(0, int(round(sec)))
    m, s = divmod(sec_i, 60)
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


def extract_cues_and_chapters_from_fcproj(fcproj_path: Path) -> tuple[list[tuple[float, float, str]], list[tuple[float, str]], list[str]]:
    if not fcproj_path.exists():
        return [], [(0.0, "Intro")], []

    data = json.loads(fcproj_path.read_text(encoding="utf-8"))
    items = data.get("project", {}).get("items", {})
    seq_id = str(data.get("view", {}).get("active_sequence") or 98)
    seq = items.get(seq_id, {}).get("kind", {}).get("Sequence", {})

    raw_cues: list[tuple[float, float, str]] = []
    for ct in seq.get("caption_tracks", []):
        for cap in ct.get("captions", []):
            st = cap.get("start", 0) / TICKS_PER_SEC
            dur = cap.get("duration", int(3.5 * TICKS_PER_SEC)) / TICKS_PER_SEC
            txt = cap.get("text", "").strip()
            if txt:
                raw_cues.append((st, st + dur, txt))
    raw_cues.sort(key=lambda x: x[0])

    chapters: list[tuple[float, str]] = []
    for st, _end, txt in raw_cues:
        clean_txt = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[·•-]\s*", "", txt)
        if not chapters:
            chapters.append((0.0, clean_txt))
        elif st - chapters[-1][0] >= 10.0:
            chapters.append((st, clean_txt))

    music_tracks: list[str] = []
    audio_tracks = seq.get("audio_tracks", [])
    if len(audio_tracks) > 1:
        for clip in audio_tracks[1].get("items", []):
            name = clip.get("name", "")
            if name and name not in music_tracks:
                music_tracks.append(name)

    return raw_cues, chapters, music_tracks


def write_srt(cues: list[tuple[float, float, str]], out_path: Path) -> None:
    lines: list[str] = []
    for idx, (st, end, txt) in enumerate(cues, 1):
        lines.extend([str(idx), f"{fmt_srt_tc(st)} --> {fmt_srt_tc(end)}", txt, ""])
    out_path.write_text("\n".join(lines), encoding="utf-8")


def format_music_credit(filename: str) -> str:
    stem = Path(filename).stem
    parts = stem.split("_")
    if len(parts) >= 4:
        bpm, mood, track, artist = parts[0], parts[1], parts[2], parts[3]
        track_spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", track)
        return f'"{track_spaced}" by {artist} ({mood}, {bpm})'
    return stem


def extract_thumbnail(mp4_path: Path, out_jpg: Path, timestamp_sec: float = 51.0) -> bool:
    if not mp4_path.exists():
        return False
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    subprocess.run(
        [
            ffmpeg_bin,
            "-ss", f"{timestamp_sec:.3f}",
            "-i", str(mp4_path),
            "-vf", "scale=1920:1080",
            "-vframes", "1",
            "-q:v", "2",
            "-update", "1",
            str(out_jpg),
            "-y",
        ],
        capture_output=True,
        check=True,
    )
    return out_jpg.exists()


def generate_composite_thumbnail(
    out_jpg: Path,
    headline_text: str,
    hero_img_path: Path | None = None,
    prop_img_path: Path | None = None,
) -> bool:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    try:
        from google import genai
        from google.genai import types
        from PIL import Image

        client = genai.Client(api_key=api_key)
        contents: list[Any] = []
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
    except Exception:
        pass
    return False


def localize_existing_thumbnail(
    base_jpg: Path,
    out_jpg: Path,
    lang_label: str,
    original_headline: str,
    localized_headline: str,
) -> bool:
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
    except Exception:
        pass
    return False


# ---------------------------------------------------------------------------
# Facebook Promo Copy Generator
# ---------------------------------------------------------------------------
def build_facebook_promo(
    project_dir: Path,
    meta: dict[str, Any] | None = None,
    live_url: str | None = None,
    edition_urls: dict[str, str] | None = None,
) -> dict[str, Any]:
    project_dir = Path(project_dir).expanduser().resolve()
    project_name = project_dir.name

    if meta is None:
        json_p = project_dir / "youtube_metadata.json"
        meta = json.loads(json_p.read_text(encoding="utf-8")) if json_p.exists() else {}

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

    clean_title = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[·\-–]\s*", "", title)
    desc_paras = [
        p.strip()
        for p in desc.split("\n\n")
        if p.strip() and not p.startswith(("━", "📊", "⏱️", "🎵", "#"))
    ]
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

    is_mallorca = "Mallorca" in title or "mallorca" in str(project_dir).lower() or any(
        kw in desc.lower() for kw in ("mallorca", "alcúdia", "alcudia", "pollença", "pollenca", "buger", "sa pobla", "caimari", "lluc", "bonaire")
    )
    opt4_body = ""
    opt4_first_comment = ""
    if is_mallorca:
        # Strip commercial-looking hashtags (#procyclehire, etc.) and build an authentic peer rider report
        # (modeled on the 47-like Sa Batalla & 28-like Búger Forn Can Rafel posts; zero link-drop boilerplate).
        clean_lead = re.sub(r"#\w+", "", lead_summary).strip()
        clean_second = re.sub(r"#\w+", "", second_summary).strip()
        story_block = f"{clean_lead}\n\n{clean_second}" if clean_second else clean_lead
        opt4_body = (
            f"{story_block}\n\n"
            f"Anyone else riding around this corner of the island this week — what's your favorite quiet lane or café stop nearby? 🚴‍♂️\n"
            f"(4K ride film in the first comment 👇 — or paste {yt_url} directly here if not attaching photos)"
        )
        opt4_first_comment = f"Full 4K ride & route highlights: {yt_url}"

    promo_data: dict[str, Any] = {
        "project_name": project_name,
        "youtube_url": yt_url,
        "options": {
            "option_1_direct_card": {
                "name": "Option 1: Direct YouTube Link Card (Personal Feed — Recommended)",
                "description": "Paste directly with the YouTube URL (without attaching separate photos).",
                "post_text": opt1_body,
            },
            "option_2_direct_story": {
                "name": "Option 2: Story + Highlights + Direct Link",
                "description": "Engaging narrative with chapter highlights and YouTube link.",
                "post_text": opt2_body,
            },
            "option_3_bilingual": {
                "name": "Option 3: Bilingual / Classmates Edition",
                "description": "English narrative hook + UA/RU localized context.",
                "post_text": opt3_body,
            },
        },
        "flickr": flickr_data,
    }
    if opt4_body:
        promo_data["options"]["option_4_mallorca_cycling_group"] = {
            "name": "Option 4: Mallorca Cycling Facebook Group (Authentic Route & Café Story — Zero Hashtags)",
            "description": "Peer rider story + local road/café intel + community question (attach 2–3 ride photos and drop YouTube link in First Comment, max 1–2x/week to honor group rules).",
            "post_text": opt4_body,
            "first_comment": opt4_first_comment,
        }

    md_content = (
        f"# 📱 Social Promotional Copy: `{project_name}`\n\n"
        f"> **Target Video:** [{title}]({yt_url})\n\n"
        f"## 🚀 Option 1: Direct YouTube Link Card\n```text\n{opt1_body}\n```\n\n"
        f"## 📖 Option 2: Story + Highlights\n```text\n{opt2_body}\n```\n\n"
        f"## 🌍 Option 3: Bilingual / Classmates\n```text\n{opt3_body}\n```\n"
    )
    if opt4_body:
        md_content += (
            f"\n## 🚴 Option 4: Mallorca Cycling Facebook Group (Zero Hashtags · Max 1–2x/Week)\n"
            f"```text\n{opt4_body}\n```\n"
            f"**First Comment (if attaching 2–3 ride photos):**\n```text\n{opt4_first_comment}\n```\n"
        )
    md_content += (
        f"\n## 📸 Flickr Video Upload (RU Edition)\n"
        f"- **Target File:** `{ru_video_file}`\n"
        f"- **Flickr Title:** `{flickr_title}`\n"
        f"- **Flickr Description:**\n```text\n{clean_ru_desc}\n```\n"
        f"- **Flickr Tags:** `{tags_str}`\n"
        f"- **Recommended Album:** `2026 Fall Mallorca Cycling`\n"
    )
    (project_dir / "facebook_promo.md").write_text(md_content, encoding="utf-8")

    json_p = project_dir / "youtube_metadata.json"
    if json_p.exists():
        try:
            curr_json = json.loads(json_p.read_text(encoding="utf-8"))
            curr_json["facebook_promo"] = promo_data
            json_p.write_text(json.dumps(curr_json, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    return promo_data


def print_promo_box(promo: dict[str, Any]) -> None:
    opts = promo.get("options", {})
    opt1 = opts.get("option_1_direct_card", {})
    opt2 = opts.get("option_2_direct_story", {})
    opt4 = opts.get("option_4_mallorca_cycling_group", {})
    print("\n========================================================")
    print("📱 SUGGESTED FACEBOOK PROMOTIONAL COPY")
    print("========================================================")
    print("--- [OPTION 1: PERSONAL FEED (DIRECT LINK CARD)] ---")
    print(opt1.get("post_text", "").strip())
    if opt4:
        print("\n--- [OPTION 4: MALLORCA CYCLING GROUP] ---")
        print(opt4.get("post_text", "").strip())
    print("\n--- [OPTION 2: STORY + HIGHLIGHTS] ---")
    print(opt2.get("post_text", "").strip())
    print("========================================================\n")


# ---------------------------------------------------------------------------
# Metadata Generation
# ---------------------------------------------------------------------------
def parse_storyboard_thumbnail_cfg(storyboard_text: str) -> dict[str, str]:
    cfg: dict[str, str] = {}
    m_th = re.search(r"thumbnail:\s*\n((?:\s{2,}.*\n?)+)", storyboard_text)
    if m_th:
        for line in m_th.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                cfg[k.strip()] = v.strip().strip("\"'")
    return cfg


def generate_project_youtube_metadata(
    proj_dir: Path,
    mp4_path: Path,
    thumb_sec: float = 56.5,
    thumb_mode: str = "preserve",
    thumb_text: str | None = None,
    thumb_text_ua: str | None = None,
    thumb_text_ru: str | None = None,
    thumb_hero: Path | None = None,
    thumb_prop: Path | None = None,
) -> dict[str, Any]:
    proj_dir = Path(proj_dir).expanduser().resolve()
    mp4_path = Path(mp4_path).expanduser().resolve()
    project_name = proj_dir.name

    fcproj_path = proj_dir / f"{project_name}.fcproj"
    storyboard_path = proj_dir / "Storyboard.md"

    raw_cues, chapters, music_files = extract_cues_and_chapters_from_fcproj(fcproj_path)
    music_credits = [format_music_credit(m) for m in music_files]

    storyboard_text = storyboard_path.read_text(encoding="utf-8") if storyboard_path.exists() else ""
    story_body_only = re.split(r"(?m)^(?:##\s*5\.|###\s*Published YouTube URLs)", storyboard_text)[0]
    yt_links = list(dict.fromkeys(re.findall(r"https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[A-Za-z0-9_-]+", story_body_only)))

    clean_name = project_name.replace("_", " ")
    title_primary = clean_name
    title_alt_1 = f"{clean_name} | Mallorca Cycling & Adventure"
    title_alt_2 = f"{clean_name} — Highlights & Story"
    playlists = ["Mallorca", "2026 Mallorca Cycling"]
    summary_lines: list[str] = []
    ride_stats = [f"📅 Project: {project_name}"]
    chapters_en = list(chapters)
    localizations: dict[str, dict[str, str]] = {}
    tags = ["Mallorca", "Cycling", "Adventure", "Pro Cycle Hire", "Strava", "San Jose Bicycle Club"]
    hashtags = "#MallorcaCycling #ProCycleHire #CyclingMallorca"

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

    m_sum = re.search(r"###\s*Narrative Summary.*?\n(.*?)(?=\n###|\n##|\Z)", storyboard_text, re.DOTALL)
    if m_sum:
        for p_txt in m_sum.group(1).strip().split("\n\n"):
            p_clean = p_txt.strip()
            if p_clean and not p_clean.startswith(("- **", "```")):
                summary_lines.append(p_clean)

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

    if not chapters_en:
        for row in re.finditer(r"\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*`?([0-9.]+)\s*[–-]\s*([0-9.]+)`?\*\*\s*\|\s*`?[0-9.]+s?`?\s*\|\s*([^\|]+)\|\s*([^\|]+)\|", storyboard_text):
            chapters_en.append((float(row.group(2)), f"Scene {row.group(1)}: {row.group(5).strip()[:40]}"))

    def parse_vo_parts_and_srt(text: str, header_regex: str) -> tuple[dict[str, str], list[tuple[float, float, str]]]:
        m_sec = re.search(header_regex + r".*?\n(.*?)(?=\n###|\n##|\Z)", text, re.DOTALL)
        if not m_sec:
            return {}, []
        parts: dict[str, str] = {}
        cues: list[tuple[float, float, str]] = []
        pattern = re.compile(r"-\s*\*\*(Part|Cue)\s*(\d+)\s*\(`?([0-9.]+)\s*s?\s*[\u2013\u2014-]\s*([0-9.]+)\s*s?`?\):?\*\*:?\s*(.*)")
        for ln in m_sec.group(1).splitlines():
            m = pattern.match(ln.strip())
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
    narration_scripts = {"en": en_parts, "ua": ua_parts, "ru": ru_parts}

    if ua_parts:
        localizations["ua"] = {
            "title": title_ua_parsed[:100],
            "description": "\n\n".join(ua_parts.values()) + "\n\n#Майорка #Велоспорт #ProCycleHire",
        }
    if ru_parts:
        localizations["ru"] = {
            "title": title_ru_parsed[:100],
            "description": "\n\n".join(ru_parts.values()) + "\n\n#Майорка #Велоспорт #ProCycleHire",
        }

    desc_parts = [*summary_lines, "", "━━━━━━━━━━━━━━━━━━━━", "📊 RIDE & TRIP NOTES (IMPERIAL & METRIC)", *ride_stats]
    if chapters_en:
        desc_parts.extend(["", "━━━━━━━━━━━━━━━━━━━━", "⏱️ CHAPTERS"])
        for st, label in chapters_en:
            desc_parts.append(f"{fmt_mmss(st)} {label}")
    if yt_links:
        desc_parts.extend(["", "━━━━━━━━━━━━━━━━━━━━", "🔗 RELATED / FLASHBACK VIDEOS"])
        for link in yt_links:
            desc_parts.append(f"• Flashback clip featured in this video: {link}")
    if music_credits:
        desc_parts.extend(["", "━━━━━━━━━━━━━━━━━━━━", "🎵 MUSIC"])
        for mc in music_credits:
            desc_parts.append(f"• {mc}")

    json_out = proj_dir / "youtube_metadata.json"
    existing_url, existing_vid, existing_editions, existing_hashes = None, None, {}, {}
    if json_out.exists():
        try:
            old = json.loads(json_out.read_text(encoding="utf-8"))
            existing_url = old.get("published_youtube_url")
            existing_vid = old.get("published_video_id")
            existing_editions = old.get("edition_urls") or {}
            existing_hashes = old.get("caption_hashes") or {}
        except Exception:
            pass

    if localizations.get("ua") or localizations.get("ru"):
        desc_parts.extend(["", "━━━━━━━━━━━━━━━━━━━━"])
        if localizations.get("ua"):
            desc_parts.append("🇺🇦 УКРАЇНСЬКОЮ")
            if existing_editions.get("ua"):
                ua_line = f"🔊 Повна версія з українською озвучкою: {existing_editions['ua']}"
                desc_parts.extend([ua_line, ""])
                localizations["ua"]["description"] = f"{ua_line}\n\n" + localizations["ua"]["description"]
            desc_parts.extend([localizations["ua"]["title"], "", localizations["ua"]["description"].split("\n\n⏱️")[0]])
        if localizations.get("ru"):
            desc_parts.extend(["", "━━━━━━━━━━━━━━━━━━━━", "🇷🇺 ПО-РУССКИ"])
            if existing_editions.get("ru"):
                ru_line = f"🔊 Полная версия с русской озвучкой: {existing_editions['ru']}"
                desc_parts.extend([ru_line, ""])
                localizations["ru"]["description"] = f"{ru_line}\n\n" + localizations["ru"]["description"]
            desc_parts.extend([localizations["ru"]["title"], "", localizations["ru"]["description"].split("\n\n⏱️")[0]])

    desc_parts.extend(["", hashtags])
    description_text = "\n".join(desc_parts)

    srt_files: dict[str, str] = {}
    en_cues_to_write = srt_en if srt_en else raw_cues
    if en_cues_to_write and not (proj_dir / "captions.en.srt").exists():
        write_srt(en_cues_to_write, proj_dir / "captions.en.srt")
    if (proj_dir / "captions.en.srt").exists():
        srt_files["en"] = "captions.en.srt"
    if srt_ua and not (proj_dir / "captions.ua.srt").exists():
        write_srt(srt_ua, proj_dir / "captions.ua.srt")
    if (proj_dir / "captions.ua.srt").exists():
        srt_files["ua"] = "captions.ua.srt"
    if srt_ru and not (proj_dir / "captions.ru.srt").exists():
        write_srt(srt_ru, proj_dir / "captions.ru.srt")
    if (proj_dir / "captions.ru.srt").exists():
        srt_files["ru"] = "captions.ru.srt"

    if any(narration_scripts.values()) and not (proj_dir / "narration_scripts.json").exists():
        (proj_dir / "narration_scripts.json").write_text(json.dumps(narration_scripts, indent=2, ensure_ascii=False), encoding="utf-8")

    sb_thumb_cfg = parse_storyboard_thumbnail_cfg(storyboard_text)
    thumb_headline = resolve_thumbnail_headline(thumb_text, sb_thumb_cfg, key="headline_text", fallback="MALLORCA CYCLING")
    thumb_headline_ua = resolve_thumbnail_headline(thumb_text_ua, sb_thumb_cfg, key="headline_text_ua", fallback="")
    thumb_headline_ru = resolve_thumbnail_headline(thumb_text_ru, sb_thumb_cfg, key="headline_text_ru", fallback="")

    thumb_path = proj_dir / "thumbnail.jpg"
    thumb_ok = False
    if thumb_mode == "preserve" and thumb_path.exists():
        thumb_ok = True
    elif thumb_mode in ("composite_ai", "preserve"):
        hero_p = thumb_hero
        if not hero_p and (proj_dir / "thumb_candidates" / "alexander_selfie.jpg").exists():
            hero_p = proj_dir / "thumb_candidates" / "alexander_selfie.jpg"
        thumb_ok = generate_composite_thumbnail(thumb_path, thumb_headline, hero_p, thumb_prop)
        if not thumb_ok and not thumb_path.exists():
            thumb_ok = extract_thumbnail(mp4_path, thumb_path, thumb_sec)
    else:
        thumb_ok = extract_thumbnail(mp4_path, thumb_path, thumb_sec)

    thumb_ua_path = proj_dir / "thumbnail_ua.jpg"
    thumb_ru_path = proj_dir / "thumbnail_ru.jpg"
    if thumb_ok and not thumb_ua_path.exists() and thumb_headline_ua:
        localize_existing_thumbnail(thumb_path, thumb_ua_path, "Ukrainian", thumb_headline, thumb_headline_ua)
    if thumb_ok and not thumb_ru_path.exists() and thumb_headline_ru:
        localize_existing_thumbnail(thumb_path, thumb_ru_path, "Russian", thumb_headline, thumb_headline_ru)

    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", project_name)
    recording_date_iso = f"{m_date.group(1)}T00:00:00.000Z" if m_date else None

    metadata: dict[str, Any] = {
        "project_name": project_name,
        "recording_date": recording_date_iso,
        "video_file": mp4_path.name,
        "thumbnail_file": thumb_path.name if thumb_ok else None,
        "thumbnail_timestamp_sec": thumb_sec,
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
        "privacy_status": DEFAULT_YOUTUBE_PRIVACY_STATUS,
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
    if existing_hashes:
        metadata["caption_hashes"] = existing_hashes

    json_out.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
    build_facebook_promo(proj_dir, metadata, live_url=existing_url, edition_urls=existing_editions)
    return metadata


# ---------------------------------------------------------------------------
# YouTube Data API v3 Upload & Sync
# ---------------------------------------------------------------------------
def load_dotenv_if_needed() -> None:
    env_file = get_studio_root() / ".env"
    if not os.environ.get("GOOGLE_OAUTH_CLIENT_ID") and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def get_youtube_service() -> Any:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    load_dotenv_if_needed()
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN") or os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN")
    creds = None

    if refresh_token and client_id and client_secret:
        try:
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
            creds.refresh(Request())
        except Exception:
            creds = None

    if not creds and TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except Exception:
            creds = None

    if not creds or not creds.valid:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "antigravity-video-studio")
        if not client_id or not client_secret:
            raise RuntimeError("GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET not found in environment.")
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "project_id": project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)
        OAUTH_DIR.mkdir(parents=True, exist_ok=True)
        os.chmod(OAUTH_DIR, 0o700)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(TOKEN_FILE, 0o600)

    return build("youtube", "v3", credentials=creds)


def register_in_archive_index(meta: dict[str, Any], youtube_url: str) -> None:
    m = re.search(r"(?:v=|youtu\.be/|video/)([A-Za-z0-9_-]{11})", youtube_url)
    vid_id = m.group(1) if m else youtube_url
    clean_url = f"https://www.youtube.com/watch?v={vid_id}"
    entry = {
        "id": vid_id,
        "url": clean_url,
        "title": meta.get("title", ""),
        "upload_date": datetime.date.today().strftime("%Y%m%d"),
        "description_snippet": meta.get("description", "")[:500],
        "chapters": meta.get("chapters", []),
        "project_name": meta.get("project_name", ""),
    }
    yt_idx = get_yt_index_path()
    yt_idx.parent.mkdir(parents=True, exist_ok=True)
    with yt_idx.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def assign_playlists_and_captions(youtube: Any, vid_id: str, meta: dict[str, Any], meta_path: Path | None = None) -> None:
    from googleapiclient.http import MediaFileUpload

    target_playlists = set(meta.get("playlists", []))
    if target_playlists:
        try:
            pl_resp = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
            for item in pl_resp.get("items", []):
                pl_title = item.get("snippet", {}).get("title", "")
                if pl_title in target_playlists:
                    youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": item["id"],
                                "resourceId": {"kind": "youtube#video", "videoId": vid_id},
                            }
                        },
                    ).execute()
        except Exception:
            pass

    existing_langs: dict[str, list[str]] = {}
    try:
        cap_list = youtube.captions().list(part="snippet", videoId=vid_id).execute()
        for c in cap_list.get("items", []):
            if c["snippet"].get("trackKind") != "ASR":
                existing_langs.setdefault(c["snippet"]["language"], []).append(c["id"])
    except Exception:
        pass

    caption_hashes = meta.setdefault("caption_hashes", {})
    if meta_path and Path(meta_path).exists():
        try:
            disk_meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            if "caption_hashes" in disk_meta:
                caption_hashes.update(disk_meta["caption_hashes"])
        except Exception:
            pass

    hashes_changed = False
    for lang, srt_path in meta.get("srt_files", {}).items():
        yt_lang = to_youtube_bcp47_lang(lang)
        srt_file = Path(srt_path)
        if not srt_file.is_absolute() and meta_path:
            srt_file = Path(meta_path).parent / srt_path
        if srt_file.exists():
            current_hash = compute_srt_sha256(srt_file)
            cache_key = f"{vid_id}:{yt_lang}"
            if yt_lang in existing_langs and caption_hashes.get(cache_key) == current_hash:
                continue

            media = MediaFileUpload(str(srt_file), mimetype="application/x-subrip")
            for old_id in existing_langs.get(yt_lang, []):
                try:
                    youtube.captions().delete(id=old_id).execute()
                except Exception:
                    pass
            youtube.captions().insert(
                part="snippet",
                body={
                    "snippet": {
                        "videoId": vid_id,
                        "language": yt_lang,
                        "name": YT_LANG_NAMES.get(lang, lang),
                        "isDraft": False,
                    }
                },
                media_body=media,
            ).execute()
            caption_hashes[cache_key] = current_hash
            hashes_changed = True

    if hashes_changed and meta_path and Path(meta_path).exists():
        try:
            stored_meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            stored_meta.setdefault("caption_hashes", {}).update(caption_hashes)
            Path(meta_path).write_text(json.dumps(stored_meta, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass


def infer_recording_date_iso(meta: dict[str, Any], video_path: Path | None = None) -> str | None:
    raw = meta.get("recording_date") or ""
    if raw:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(raw))
        if m:
            return f"{m.group(1)}T00:00:00.000Z"
    for candidate in (meta.get("project_name", ""), meta.get("title", ""), video_path.name if video_path else ""):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(candidate))
        if m:
            return f"{m.group(1)}T00:00:00.000Z"
    return None


def sanitize_yt_description(desc: str, max_bytes: int = 4850) -> str:
    cleaned = (desc or "").replace("<", "‹").replace(">", "›")
    encoded = cleaned.encode("utf-8")
    if len(encoded) <= max_bytes:
        return cleaned
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    last_nl = truncated.rfind("\n")
    if last_nl > max_bytes // 2:
        truncated = truncated[:last_nl]
    return truncated.rstrip()


def update_existing_video_via_api(
    meta_path: Path,
    vid_id: str,
    skip_playlists: bool = False,
    skip_captions: bool = False,
    youtube: Any | None = None,
) -> None:
    youtube = youtube or get_youtube_service()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    localizations = meta.get("localizations", {})
    rec_date_iso = infer_recording_date_iso(meta)

    body: dict[str, Any] = {
        "id": vid_id,
        "snippet": {
            "title": meta["title"][:100],
            "description": sanitize_yt_description(meta["description"]),
            "tags": meta.get("tags", []),
            "categoryId": str(meta.get("category_id", "17")),
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
    }
    parts = ["snippet"]
    if localizations:
        body["localizations"] = {
            to_youtube_bcp47_lang(lang): {
                "title": loc["title"][:100],
                "description": sanitize_yt_description(loc["description"]),
            }
            for lang, loc in localizations.items()
        }
        parts.append("localizations")
    if rec_date_iso:
        body["recordingDetails"] = {"recordingDate": rec_date_iso}
        parts.append("recordingDetails")

    youtube.videos().update(part=",".join(parts), body=body).execute()
    meta_for_sync = dict(meta)
    if skip_playlists:
        meta_for_sync["playlists"] = []
    if skip_captions:
        meta_for_sync["srt_files"] = {}
    if meta_for_sync.get("playlists") or meta_for_sync.get("srt_files"):
        assign_playlists_and_captions(youtube, vid_id, meta_for_sync, meta_path=meta_path)


def upload_raw_video(
    youtube: Any,
    video_path: Path,
    title: str,
    description: str,
    privacy: str = DEFAULT_YOUTUBE_PRIVACY_STATUS,
    default_lang: str = "en",
    tags: list[str] | None = None,
    category_id: str = "17",
    thumbnail_path: Path | None = None,
    playlists: list[str] | None = None,
    srt_files: dict[str, str] | None = None,
    localizations: dict[str, dict[str, str]] | None = None,
    recording_date_iso: str | None = None,
    meta_path: Path | None = None,
) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload

    wire_default_lang = to_youtube_bcp47_lang(default_lang)
    rec_iso = recording_date_iso or infer_recording_date_iso({"title": title}, video_path)
    body: dict[str, Any] = {
        "snippet": {
            "title": title[:100],
            "description": sanitize_yt_description(description),
            "tags": tags or [],
            "categoryId": str(category_id),
            "defaultLanguage": wire_default_lang,
            "defaultAudioLanguage": wire_default_lang,
        },
        "status": {
            "privacyStatus": privacy or DEFAULT_YOUTUBE_PRIVACY_STATUS,
            "selfDeclaredMadeForKids": False,
        },
    }
    parts = ["snippet", "status"]
    if localizations:
        body["localizations"] = {
            to_youtube_bcp47_lang(lang): {
                "title": loc["title"][:100],
                "description": sanitize_yt_description(loc["description"]),
            }
            for lang, loc in localizations.items()
        }
        parts.append("localizations")
    if rec_iso:
        body["recordingDetails"] = {"recordingDate": rec_iso}
        parts.append("recordingDetails")

    media = MediaFileUpload(str(video_path), chunksize=16 * 1024 * 1024, resumable=True)
    req = youtube.videos().insert(part=",".join(parts), body=body, media_body=media)
    response = None
    while response is None:
        _status, response = req.next_chunk()

    vid_id = response["id"]
    yt_url = f"https://www.youtube.com/watch?v={vid_id}"

    if thumbnail_path and thumbnail_path.exists():
        try:
            youtube.thumbnails().set(
                videoId=vid_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
        except Exception:
            pass

    assign_playlists_and_captions(
        youtube,
        vid_id,
        {"playlists": playlists or [], "srt_files": srt_files or {}},
        meta_path=meta_path,
    )
    return vid_id, yt_url


def post_pinned_language_comment(youtube: Any, video_id: str, edition_urls: dict[str, str]) -> None:
    if not edition_urls or not any(k in edition_urls for k in ("ua", "ru")):
        return
    comment_lines = ["🔊 Watch with full localized voice-over:"]
    if "ua" in edition_urls:
        comment_lines.append(f"• 🇺🇦 Українська версія: {edition_urls['ua']}")
    if "ru" in edition_urls:
        comment_lines.append(f"• 🇷🇺 Русская версия: {edition_urls['ru']}")
    comment_text = "\n".join(comment_lines)
    try:
        existing = youtube.commentThreads().list(part="snippet", videoId=video_id).execute().get("items", [])
        for item in existing:
            txt = item["snippet"]["topLevelComment"]["snippet"].get("textOriginal", "")
            if any(u in txt for u in edition_urls.values()):
                return
        youtube.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": video_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment_text}},
                }
            },
        ).execute()
    except Exception:
        pass


def _resolve_video_path(meta_path: Path, video_file: str) -> Path:
    p = Path(video_file)
    if p.is_absolute():
        return p
    cand = meta_path.parent / p
    if cand.exists():
        return cand
    exports_cand = get_exports_dir() / meta_path.parent.parent.name / p.name
    if exports_cand.exists():
        return exports_cand
    return cand


def upload_option_b_multilingual(
    meta_path: Path,
    privacy_primary: str = DEFAULT_YOUTUBE_PRIVACY_STATUS,
    privacy_editions: str = DEFAULT_YOUTUBE_PRIVACY_STATUS,
    reuse_en_id: str | None = None,
    delete_old_editions: list[str] | None = None,
    force_reupload: bool = False,
) -> str:
    youtube = get_youtube_service()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    primary_mp4 = _resolve_video_path(meta_path, meta["video_file"])
    thumb_path = Path(meta["thumbnail_file"]) if meta.get("thumbnail_file") else None
    if thumb_path and not thumb_path.is_absolute():
        thumb_path = meta_path.parent / thumb_path

    playlists = meta.get("playlists", [])
    tags = meta.get("tags", [])
    cat_id = meta.get("category_id", "17")
    srt_files = meta.get("srt_files", {})
    locs = meta.get("localizations", {})

    ua_mp4 = primary_mp4.with_name(f"{primary_mp4.stem}_UA.mp4")
    ru_mp4 = primary_mp4.with_name(f"{primary_mp4.stem}_RU.mp4")
    proj_dir = meta_path.parent
    ua_thumb = proj_dir / "thumbnail_ua.jpg"
    ru_thumb = proj_dir / "thumbnail_ru.jpg"
    rec_date_iso = infer_recording_date_iso(meta, primary_mp4)

    edition_urls: dict[str, str] = dict(meta.get("edition_urls") or {})

    if ua_mp4.exists() and not should_skip_video_insert_on_resume(meta, force_reupload=force_reupload, edition_key="ua"):
        ua_title = locs.get("ua", {}).get("title", f"{meta['title']} (Українська озвучка)")
        ua_base_desc = locs.get("ua", {}).get("description", meta["description"])
        ua_desc = f"🇺🇦 Українська версія з авторським закадровим голосом.\n\n{ua_base_desc}"
        ua_srts = {"ua": srt_files["ua"]} if "ua" in srt_files else {}
        _ua_id, ua_url = upload_raw_video(
            youtube,
            video_path=ua_mp4,
            title=ua_title,
            description=ua_desc,
            privacy=privacy_editions,
            default_lang="uk",
            tags=tags + ["Майорка", "Українська озвучка"],
            category_id=cat_id,
            thumbnail_path=ua_thumb if ua_thumb.exists() else thumb_path,
            playlists=playlists,
            srt_files=ua_srts,
            recording_date_iso=rec_date_iso,
            meta_path=meta_path,
        )
        edition_urls["ua"] = ua_url
        meta["edition_urls"] = edition_urls
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        register_in_archive_index({"title": ua_title, "description": ua_desc, "chapters": meta.get("chapters", []), "project_name": meta.get("project_name", "")}, ua_url)

    if ru_mp4.exists() and not should_skip_video_insert_on_resume(meta, force_reupload=force_reupload, edition_key="ru"):
        ru_title = locs.get("ru", {}).get("title", f"{meta['title']} (Русская озвучка)")
        ru_base_desc = locs.get("ru", {}).get("description", meta["description"])
        ru_desc = f"🇷🇺 Русская версия с авторским закадровым голосом.\n\n{ru_base_desc}"
        ru_srts = {"ru": srt_files["ru"]} if "ru" in srt_files else {}
        _ru_id, ru_url = upload_raw_video(
            youtube,
            video_path=ru_mp4,
            title=ru_title,
            description=ru_desc,
            privacy=privacy_editions,
            default_lang="ru",
            tags=tags + ["Майорка", "Русская озвучка"],
            category_id=cat_id,
            thumbnail_path=ru_thumb if ru_thumb.exists() else thumb_path,
            playlists=playlists,
            srt_files=ru_srts,
            recording_date_iso=rec_date_iso,
            meta_path=meta_path,
        )
        edition_urls["ru"] = ru_url
        meta["edition_urls"] = edition_urls
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        register_in_archive_index({"title": ru_title, "description": ru_desc, "chapters": meta.get("chapters", []), "project_name": meta.get("project_name", "")}, ru_url)

    primary_desc = meta["description"]
    if "ua" in edition_urls and edition_urls["ua"] not in primary_desc:
        ua_link_line = f"🔊 Повна версія з українською озвучкою: {edition_urls['ua']}\n\n"
        if "🇺🇦 УКРАЇНСЬКОЮ" in primary_desc:
            primary_desc = primary_desc.replace("🇺🇦 УКРАЇНСЬКОЮ\n", f"🇺🇦 УКРАЇНСЬКОЮ\n{ua_link_line}")
    if "ru" in edition_urls and edition_urls["ru"] not in primary_desc:
        ru_link_line = f"🔊 Полная версия с русской озвучкой: {edition_urls['ru']}\n\n"
        if "🇷🇺 ПО-РУССКИ" in primary_desc:
            primary_desc = primary_desc.replace("🇷🇺 ПО-РУССКИ\n", f"🇷🇺 ПО-РУССКИ\n{ru_link_line}")

    meta["description"] = primary_desc
    meta["localizations"] = locs
    if rec_date_iso:
        meta["recording_date"] = rec_date_iso

    effective_reuse_id = reuse_en_id or (meta.get("published_video_id") if should_skip_video_insert_on_resume(meta, force_reupload=force_reupload) else None)
    if effective_reuse_id:
        en_id = effective_reuse_id
        en_url = f"https://www.youtube.com/watch?v={en_id}"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        update_existing_video_via_api(meta_path, en_id, skip_playlists=True, youtube=youtube)
    else:
        en_id, en_url = upload_raw_video(
            youtube,
            video_path=primary_mp4,
            title=meta["title"],
            description=primary_desc,
            privacy=privacy_primary,
            default_lang="en",
            tags=tags,
            category_id=cat_id,
            thumbnail_path=thumb_path,
            playlists=playlists,
            srt_files=srt_files,
            localizations=locs,
            recording_date_iso=rec_date_iso,
            meta_path=meta_path,
        )
        register_in_archive_index(meta, en_url)

    if delete_old_editions:
        for old_vid in delete_old_editions:
            if old_vid.strip():
                try:
                    youtube.videos().delete(id=old_vid.strip()).execute()
                except Exception:
                    pass

    post_pinned_language_comment(youtube, en_id, edition_urls)
    meta["published_youtube_url"] = en_url
    meta["published_video_id"] = en_id
    meta["edition_urls"] = edition_urls
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    output_facebook_promo_after_publish(meta_path, en_url, edition_urls)
    return en_url


def output_facebook_promo_after_publish(meta_path: Path, live_url: str, edition_urls: dict[str, str] | None = None) -> None:
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        promo = build_facebook_promo(meta_path.parent, meta, live_url=live_url, edition_urls=edition_urls)
        print_promo_box(promo)
    except Exception:
        pass


def metadata_cli_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Generate Imperial YouTube metadata, ua/ru localizations & .srt files")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--mp4", required=True)
    p.add_argument("--thumb-sec", type=float, default=56.5)
    p.add_argument("--thumb-mode", choices=["preserve", "composite_ai", "frame"], default="preserve")
    p.add_argument("--thumb-text", default=None, help="3-4 word ALL-CAPS headline override (defaults to Storyboard Section 5)")
    p.add_argument("--thumb-text-ua", default=None)
    p.add_argument("--thumb-text-ru", default=None)
    p.add_argument("--thumb-hero", default=None)
    p.add_argument("--thumb-prop", default=None)
    args = p.parse_args(argv)

    generate_project_youtube_metadata(
        proj_dir=Path(args.project_dir),
        mp4_path=Path(args.mp4),
        thumb_sec=args.thumb_sec,
        thumb_mode=args.thumb_mode,
        thumb_text=args.thumb_text,
        thumb_text_ua=args.thumb_text_ua,
        thumb_text_ru=args.thumb_text_ru,
        thumb_hero=Path(args.thumb_hero).expanduser() if args.thumb_hero else None,
        thumb_prop=Path(args.thumb_prop).expanduser() if args.thumb_prop else None,
    )
    return 0


def upload_cli_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Upload or update YouTube video via YouTube Data API v3")
    p.add_argument("--metadata", required=True, help="Path to youtube_metadata.json")
    p.add_argument("--privacy", choices=["unlisted", "private", "public"], help="Override privacy status (default: unlisted)")
    p.add_argument("--option-b", action="store_true")
    p.add_argument("--reuse-en-id")
    p.add_argument("--delete-old-editions")
    p.add_argument("--update-video-id")
    p.add_argument("--skip-playlists", action="store_true")
    p.add_argument("--register-url")
    p.add_argument("--force-reupload", action="store_true", help="Force videos.insert even if published_video_id already exists")
    args = p.parse_args(argv)

    meta_path = Path(args.metadata).expanduser().resolve()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if args.register_url:
        meta["published_youtube_url"] = args.register_url
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        register_in_archive_index(meta, args.register_url)
        output_facebook_promo_after_publish(meta_path, args.register_url, meta.get("edition_urls"))
        return 0

    if args.update_video_id:
        update_existing_video_via_api(meta_path, args.update_video_id, args.skip_playlists)
        yt_url = f"https://www.youtube.com/watch?v={args.update_video_id}"
        meta["published_youtube_url"] = yt_url
        meta["published_video_id"] = args.update_video_id
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        output_facebook_promo_after_publish(meta_path, yt_url, meta.get("edition_urls"))
        return 0

    if args.option_b:
        old_eds = [x.strip() for x in args.delete_old_editions.split(",") if x.strip()] if args.delete_old_editions else None
        upload_option_b_multilingual(
            meta_path,
            privacy_primary=args.privacy or meta.get("privacy_status") or DEFAULT_YOUTUBE_PRIVACY_STATUS,
            privacy_editions=DEFAULT_YOUTUBE_PRIVACY_STATUS,
            reuse_en_id=args.reuse_en_id,
            delete_old_editions=old_eds,
            force_reupload=args.force_reupload,
        )
        return 0

    if should_skip_video_insert_on_resume(meta, force_reupload=args.force_reupload):
        vid_id = str(meta.get("published_video_id") or meta.get("youtube_video_id"))
        update_existing_video_via_api(meta_path, vid_id, args.skip_playlists)
        yt_url = f"https://www.youtube.com/watch?v={vid_id}"
        output_facebook_promo_after_publish(meta_path, yt_url, meta.get("edition_urls"))
        return 0

    single_mp4 = _resolve_video_path(meta_path, meta["video_file"])
    single_thumb = Path(meta["thumbnail_file"]) if meta.get("thumbnail_file") else None
    if single_thumb and not single_thumb.is_absolute():
        single_thumb = meta_path.parent / single_thumb

    vid_id, yt_url = upload_raw_video(
        get_youtube_service(),
        video_path=single_mp4,
        title=meta["title"],
        description=meta["description"],
        privacy=args.privacy or meta.get("privacy_status") or DEFAULT_YOUTUBE_PRIVACY_STATUS,
        default_lang="en",
        tags=meta.get("tags", []),
        category_id=meta.get("category_id", "17"),
        thumbnail_path=single_thumb,
        playlists=meta.get("playlists", []),
        srt_files=meta.get("srt_files", {}),
        localizations=meta.get("localizations", {}),
        meta_path=meta_path,
    )
    meta["published_youtube_url"] = yt_url
    meta["published_video_id"] = vid_id
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    register_in_archive_index(meta, yt_url)
    output_facebook_promo_after_publish(meta_path, yt_url, meta.get("edition_urls"))
    return 0
