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
    Uses Gemini 3 Pro Image (`gemini-3-pro-image-preview`) when GEMINI_API_KEY is available.
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
            model="gemini-3-pro-image-preview",
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
            model="gemini-3-pro-image-preview",
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

    if "Nina_Pollenca_Loop" in project_name:
        title_primary = "Saved by Nina's Sharp Eyes! Escorting to Zumba & 21.5 mi Pollença Loop"
        title_alt_1 = "2026-11-02 · Escorting Nina to Zumba & Pollença Loop (21.5 mi)"
        title_alt_2 = "Mallorca Morning Ride: Bellevue Zumba Drop-Off, Missing Brake Pad & Badia de Pollença (21.5 mi)"
        playlists = ["Mallorca", "2026 Mallorca Cycling"]

        summary_lines = [
            "Morning rollout from Port d'Alcúdia below Puig de Sant Martí, escorting Nina on bikes past Ranxo Ses Roques to her outdoor Zumba court at the Bellevue complex.",
            "",
            "Right as I rolled up to the tennis court gate, Nina's sharp eyes saved my ride—she spotted my blue Reynolds front brake pad lying on the ground after it had fallen out! I popped the pad back into the Dura-Ace caliper by hand, rode past Pro Cycle Hire in Port de Pollença (closed for winter), and cruised gently south along the Badia de Pollença coast before picking up a celebratory Eroski haul in my San Jose Bicycle Club musette and fixing the brake properly at home.",
        ]
        ride_stats = [
            "📍 Location: Port d'Alcúdia · Bellevue · Port de Pollença · Badia de Pollença, Mallorca",
            "🚴‍♂️ Distance: 21.5 mi (34.5 km) | Moving Time: 1h 45m | Elevation Gain: 531 ft (162 m)",
            "📅 Date: November 2, 2026",
        ]
        chapters_en = [
            (0.0, "Escorting Nina to Zumba & Pollença Loop (21.5 mi)"),
            (11.5, "Passing the horses at Ranxo Ses Roques"),
            (24.1, "Arriving at the Bellevue tennis courts — Nina's outdoor Zumba stage"),
            (36.6, "Rolling up behind Nina — she spots my missing front brake pad on the ground!"),
            (49.8, "Pushed pad back in by hand, coastal spin & SJBC Eroski haul"),
        ]
        localizations = {
            "ua": {
                "title": "2026-11-02 · Проводжаю Ніну на Зумбу та велоколо через Поєнсу (21.5 милі / 34.5 км)",
                "description": (
                    "Ранковий виїзд із Порт-д'Алькудія біля підніжжя Пуч-де-Сант-Марті — проводжаю Ніну на велосипедах повз ранчо Ranxo Ses Roques до її відкритого майданчика для Зумби в комплексі Bellevue.\n\n"
                    "Щойно я під'їхав до воріт тенісного корту, гостре око Ніни врятувало мою поїздку: вона помітила на землі мою праву передню гальмівну колодку, яка щойно випала! Я вставив колодку назад у супорт вручну, проїхав повз велопрокат Pro Cycle Hire у Порт-де-Поєнса (зачинений на зиму) та обережно прокотився вздовж узбережжя затоки Бадія-де-Поєнса, а на зворотному шляху заїхав у Eroski зі своєю торбинкою San Jose Bicycle Club і вдома надійно полагодив гальма.\n\n"
                    "⏱️ ЕПІЗОДИ\n"
                    "00:00 Виїзд із Ніною на Зумбу та коло через Поєнсу (21.5 милі / 34.5 км)\n"
                    "00:12 Проїжджаємо повз коней біля Ranxo Ses Roques\n"
                    "00:24 Тенісні корти Bellevue — відкрита сцена Ніни для Зумби\n"
                    "00:37 Ніна помічає на землі мою передню гальмівну колодку!\n"
                    "00:50 Колодка на місці, узбережжя Бадія-де-Поєнса та покупки з Eroski"
                ),
            },
            "ru": {
                "title": "2026-11-02 · Провожаю Нину на Зумбу и велокруг через Пойенсу (21.5 мили / 34.5 км)",
                "description": (
                    "Утренний выезд из Порт-д'Алькудия у подножия Пуч-де-Сант-Марти — провожаю Нину на велосипедах мимо ранчо Ranxo Ses Roques к её открытой площадке для Зумбы в комплексе Bellevue.\n\n"
                    "Как только я подъехал к воротам теннисного корта, зоркий глаз Нины спас мою поездку: она заметила на земле мою правую переднюю тормозную колодку, которая только что выпала! Я вставил колодку обратно в суппорт вручную, проехал мимо велопроката Pro Cycle Hire в Порт-де-Пойенса (закрытого на зиму) и спокойно прокатился вдоль побережья залива Бадия-де-Пойенса, а по дороге домой заехал в Eroski со своей сумкой San Jose Bicycle Club и дома основательно починил тормоза.\n\n"
                    "⏱️ ЭПИЗОДЫ\n"
                    "00:00 Выезд с Ниной на Зумбу и круг через Пойенсу (21.5 мили / 34.5 км)\n"
                    "00:12 Проезжаем мимо лошадей у Ranxo Ses Roques\n"
                    "00:24 Теннисные корты Bellevue — открытая сцена Нины для Зумбы\n"
                    "00:37 Нина замечает на земле мою выпавшую тормозную колодку!\n"
                    "00:50 Колодка на месте, побережье Бадия-де-Пойенса и трофеи из Eroski"
                ),
            },
        }
        srt_en = [
            (1.8, 7.2, "Morning ride from Port d'Alcúdia below Puig de Sant Martí,"),
            (7.2, 13.0, "escorting Nina past the horses at Ranxo Ses Roques to her outdoor Zumba court at Bellevue."),
            (24.1, 31.4, "Arriving at the Bellevue tennis courts — Nina ready on her outdoor Zumba stage."),
            (31.4, 36.6, "Monday's Zumba session in full swing on the Bellevue court!"),
            (36.6, 40.8, 'Nina: "I\'ll go set up the table." — "See you soon, sweetheart, when are you heading back?"'),
            (40.8, 44.3, 'Nina: "I also want to stop for mushrooms on the way." — "Okay, see you!"'),
            (44.3, 49.8, 'Nina: "Something fell!" — "What fell?" — "Right there—that blue brake pad of yours fell out!"'),
            (50.0, 55.2, "Nina's sharp eyes at the gate saved my ride! I popped my fallen brake pad back in by hand,"),
            (55.2, 60.5, "cruised around Pollença Bay, and grabbed an Eroski haul on the way home."),
        ]
        srt_ua = [
            (1.8, 7.2, "Ранковий виїзд із Порт-д'Алькудія біля Пуч-де-Сант-Марті —"),
            (7.2, 13.0, "проводжаю Ніну повз коней у Ranxo Ses Roques до її відкритого корту для Зумби в Bellevue."),
            (24.1, 31.4, "Приїхали до тенісних кортів Bellevue — Ніна готова до заняття."),
            (31.4, 36.6, "Понеділкова Зумба у розпалі на корті Bellevue!"),
            (36.6, 40.8, "Ніна: «Піду готувати стіл.» — «Ну все, ластівко, коли ти назад?»"),
            (40.8, 44.3, "Ніна: «Ще хочу по гриби заїхати.» — «А, ну добре. Окей, давай!»"),
            (44.3, 49.8, "Ніна: «Щось упало!» — «Що впало?» — «Он там! Це твоє впало синє!»"),
            (50.0, 55.2, "Гостре око Ніни врятувало поїздку! Я вставив гальмівну колодку вручну,"),
            (55.2, 60.5, "прокотився вздовж затоки Поєнса і заїхав у Eroski дорогою додому."),
        ]
        srt_ru = [
            (1.8, 7.2, "Утренний выезд из Порт-д'Алькудия у Пуч-де-Сант-Марти —"),
            (7.2, 13.0, "провожаю Нину мимо лошадей у Ranxo Ses Roques к её открытому корту для Зумбы в Bellevue."),
            (24.1, 31.4, "Приехали к теннисным кортам Bellevue — Нина готова к занятию."),
            (31.4, 36.6, "Понедельничная Зумба в самом разгаре на корте Bellevue!"),
            (36.6, 40.8, "Нина: «Ну ладно, пойду поставлю стол.» — «Ну всё, ласточка, когда ты обратно?»"),
            (40.8, 44.3, "Нина: «Ещё хочу за грибами заехать.» — «А, ну ладно. Окей, давай!»"),
            (44.3, 49.8, "Нина: «Что-то упало!» — «Что упало?» — «Вон! Это твоё упало синее!»"),
            (50.0, 55.2, "Зоркий глаз Нины спас поездку! Я вставил тормозную колодку вручную,"),
            (55.2, 60.5, "прокатился вдоль залива Пойенса и заехал в Eroski по дороге домой."),
        ]
        narration_scripts = {
            "en": {
                "part1": "Morning ride from Port d'Alcúdia below Puig de Sant Martí, escorting Nina past the horses at Ranxo Ses Roques to her outdoor Zumba court at Bellevue.",
                "part2": "Nina's sharp eyes at the gate saved my ride! I popped my fallen brake pad back in by hand, cruised around Pollença Bay, and grabbed an Eroski haul on the way home.",
            },
            "ua": {
                "part1": "Ранковий виїзд із Порт-д'Алькудія біля Пуч-де-Сант-Марті — проводжаю Ніну повз коней у Ranxo Ses Roques до її відкритого корту для Зумби в Bellevue.",
                "part2": "Гостре око Ніни врятувало поїздку! Я вставив гальмівну колодку вручну, прокотився вздовж затоки Поєнса і заїхав у Eroski дорогою додому.",
            },
            "ru": {
                "part1": "Утренний выезд из Порт-д'Алькудия у Пуч-де-Сант-Марти — провожаю Нину мимо лошадей у Ranxo Ses Roques к её открытому корту для Зумбы в Bellevue.",
                "part2": "Зоркий глаз Нины спас поездку! Я вставил тормозную колодку вручную, прокатился вдоль залива Пойенса и заехал в Eroski по дороге домой.",
            },
        }
        tags = [
            "Mallorca cycling", "Port d'Alcudia", "Port de Pollenca", "Badia de Pollenca",
            "Bellevue Alcudia", "Zumba Mallorca", "San Jose Bicycle Club", "SJBC",
            "Pro Cycle Hire Mallorca", "Pro Cycle Cafe", "cycling vlog", "disc brake pad",
            "Insta360", "Spain cycling",
        ]
        hashtags = "#MallorcaCycling #PortDePollenca #PortDAlcudia #SanJoseBicycleClub #CyclingVlog"
    else:
        clean_name = project_name.replace("_", " ")
        title_primary = clean_name
        title_alt_1 = f"{clean_name} | Mallorca Cycling & Adventure"
        title_alt_2 = f"{clean_name} — Highlights & Story"
        playlists = ["Mallorca", "2026 Mallorca Cycling"]
        summary_lines = [f"Highlights and story from {clean_name}."]
        ride_stats = [f"📅 Project: {project_name}"]
        chapters_en = chapters
        localizations = {}
        srt_en, srt_ua, srt_ru = [], [], []
        narration_scripts = {}
        tags = ["Mallorca", "Cycling", "Adventure", "Insta360", "San Jose Bicycle Club"]
        hashtags = "#Mallorca #Cycling #Adventure"

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

    thumb_path = proj_dir / "thumbnail.jpg"
    if args.thumb_mode == "preserve" and thumb_path.exists():
        thumb_ok = True
    elif args.thumb_mode == "composite_ai":
        hero_p = Path(args.thumb_hero).expanduser() if args.thumb_hero else None
        prop_p = Path(args.thumb_prop).expanduser() if args.thumb_prop else None
        thumb_ok = generate_composite_thumbnail(thumb_path, args.thumb_text, hero_p, prop_p)
        if not thumb_ok:
            thumb_ok = extract_thumbnail(mp4_path, thumb_path, args.thumb_sec)
    else:
        thumb_ok = extract_thumbnail(mp4_path, thumb_path, args.thumb_sec)

    thumb_ua_path = proj_dir / "thumbnail_ua.jpg"
    thumb_ru_path = proj_dir / "thumbnail_ru.jpg"
    if thumb_ok and not thumb_ua_path.exists() and args.thumb_text_ua:
        localize_existing_thumbnail(thumb_path, thumb_ua_path, "Ukrainian", args.thumb_text, args.thumb_text_ua)
    if thumb_ok and not thumb_ru_path.exists() and args.thumb_text_ru:
        localize_existing_thumbnail(thumb_path, thumb_ru_path, "Russian", args.thumb_text, args.thumb_text_ru)

    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", project_name)
    recording_date_iso = f"{m_date.group(1)}T00:00:00.000Z" if m_date else None

    metadata = {
        "project_name": project_name,
        "recording_date": recording_date_iso,
        "video_file": mp4_path.name,
        "thumbnail_file": thumb_path.name if thumb_ok else None,
        "thumbnail_timestamp_sec": args.thumb_sec,
        "title": title_primary,
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
