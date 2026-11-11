"""Warm Vintage Parchment cards, Cyrillic bold parity, emoji stripping, speech pagination, and HUD/map widgets."""

from __future__ import annotations

import datetime as dt
import math
import re
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from agvs_core.config import find_binary
from agvs_core.telemetry_gpx import (
    ACTIVITY_SPEED_THRESHOLDS,
    haversine_m,
    load_gpx_track as load_gpx_stream,
    select_primary_ride_gpx,
    should_show_telemetry_hud,
)

# ---------------------------------------------------------------------------
# Color Palette: Warm Mediterranean Parchment & Postage Ink
# ---------------------------------------------------------------------------
COLOR_PARCHMENT_FILL = (244, 239, 230, 242)   # rgba(244, 239, 230, 0.95) (#F4EFE6)
COLOR_ESPRESSO_INK = (35, 31, 29, 255)        # #231F1D (Primary titles, names, metrics)
COLOR_UMBER_INK = (74, 63, 53, 255)           # #4A3F35 (Roles, subtitles, labels)
COLOR_BORDER_UMBER = (92, 80, 67, 255)        # #5C5043 (Outer 3px border)
COLOR_NEATLINE = (216, 207, 192, 255)         # #D8CFC0 (Inner 1px neatline)
COLOR_CRIMSON = (184, 58, 42, 255)            # #B83A2A (Accent stripe, highlights)
COLOR_FOREST_GREEN = (45, 106, 79, 255)       # #2D6A4F (Start pin, normal metrics)

# Comprehensive Unicode emoji / pictograph / variation-selector / ZWJ stripper
# Preserves heavy right-wards arrow \u2794 ('➔') used in route subtitle specs.
_EMOJI_RE = re.compile(
    r"(?!\u2794)[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE00-\uFE0F\u200D\u2300-\u23FF\u2B50\u2B55]+"
)


def strip_unicode_emojis(text: str) -> str:
    """Strip all Unicode emojis, variation selectors, and ZWJ sequences for clean Pillow rendering."""
    if not text:
        return ""
    cleaned = _EMOJI_RE.sub("", str(text))
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    return cleaned.strip()


# ---------------------------------------------------------------------------
# Strict macOS Apple Font Loader (Zero Monospace, Zero Emojis, Cyrillic Bold Parity)
# ---------------------------------------------------------------------------
def load_apple_font(role: str, size: int, text: str = "") -> ImageFont.FreeTypeFont:
    """
    Load native macOS .ttc/.ttf fonts with explicit face indices for Pillow rendering.
    Automatically enforces Cyrillic stroke-weight parity (Helvetica Neue Bold / Arial Bold)
    whenever Cyrillic characters are present.
    """
    if text and re.search(r"[\u0400-\u04FF]", text):
        cyrillic_candidates: list[tuple[str, int | None]] = [
            ("/System/Library/Fonts/HelveticaNeue.ttc", 1),            # Bold
            ("/System/Library/Fonts/Supplemental/Arial Bold.ttf", None),
            ("/System/Library/Fonts/Helvetica.ttc", 1),
        ]
        for path, idx in cyrillic_candidates:
            p = Path(path)
            if p.exists():
                try:
                    if idx is not None and path.endswith(".ttc"):
                        return ImageFont.truetype(str(p), size=size, index=idx)
                    return ImageFont.truetype(str(p), size=size)
                except Exception:
                    continue

    candidates: dict[str, list[tuple[str, int | None]]] = {
        "card_title": [
            ("/System/Library/Fonts/Avenir Next.ttc", 8),             # Heavy
            ("/System/Library/Fonts/Avenir Next.ttc", 0),             # Bold
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),     # Condensed ExtraBold
        ],
        "card_subtitle": [
            ("/System/Library/Fonts/Avenir Next.ttc", 2),             # Demi Bold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 6),           # Medium
        ],
        "stamp_mono": [
            ("/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc", 2),  # Bold
            ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", None),
            ("/System/Library/Fonts/SFNSMono.ttf", None),
        ],
        "stamp_typewriter": [
            ("/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc", 2),  # Bold
            ("/System/Library/Fonts/SFNSMono.ttf", None),
        ],
        "postcard_script": [
            ("/System/Library/Fonts/Supplemental/Georgia Italic.ttf", None),
            ("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc", 1),      # Bold
            ("/System/Library/Fonts/Supplemental/Bradley Hand.ttf", None),
        ],
        "hero_title": [
            ("/System/Library/Fonts/Avenir Next.ttc", 8),             # Heavy
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),
            ("/System/Library/Fonts/HelveticaNeue.ttc", 8),           # Condensed Black
        ],
        "section_header": [
            ("/System/Library/Fonts/Avenir Next.ttc", 0),             # Bold
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 2),     # Bold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 1),           # Bold
        ],
        "body_bold": [
            ("/System/Library/Fonts/Avenir Next.ttc", 2),             # Demi Bold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 6),           # Medium
        ],
        "body_regular": [
            ("/System/Library/Fonts/HelveticaNeue.ttc", 0),           # Regular
            ("/System/Library/Fonts/Avenir Next.ttc", 7),             # Regular
        ],
    }

    for path, idx in candidates.get(role, candidates["card_subtitle"]):
        p = Path(path)
        if p.exists():
            try:
                if idx is not None and path.endswith(".ttc"):
                    return ImageFont.truetype(str(p), size=size, index=idx)
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def _load_font(size: int, bold: bool = False, text: str = "") -> ImageFont.FreeTypeFont:
    role = "card_title" if bold else "card_subtitle"
    return load_apple_font(role, size, text=text)


# ---------------------------------------------------------------------------
# Continuous-Take Multi-Sentence Speech Pagination
# ---------------------------------------------------------------------------
def _split_chunk_to_max_chars(chunk: str, max_chars: int) -> list[str]:
    if len(chunk) <= max_chars:
        return [chunk]
    # Try clause boundaries first (, ; : — –)
    clauses = [c.strip() for c in re.split(r"(?<=[,;:\u2014\u2013])\s+", chunk) if c.strip()]
    if len(clauses) > 1 and all(len(c) <= max_chars for c in clauses):
        return clauses

    # Word-level balanced split fallback
    words = chunk.split()
    out: list[str] = []
    cur = ""
    for w in words:
        cand = f"{cur} {w}".strip() if cur else w
        if len(cand) <= max_chars or not cur:
            cur = cand
        else:
            out.append(cur)
            cur = w
    if cur:
        out.append(cur)
    return out


def paginate_speech_segments(
    text: str,
    start_s: float,
    total_dur_s: float,
    max_chars_per_page: int = 95,
) -> list[dict[str, Any]]:
    """
    Split continuous multi-sentence on-camera speech (> max_chars_per_page) into
    sequential card pages with word-proportional durations summing to total_dur_s.
    """
    clean = strip_unicode_emojis(text)
    if not clean or len(clean) <= max_chars_per_page:
        return [{"text": clean, "start_s": round(float(start_s), 2), "dur_s": round(float(total_dur_s), 2)}]

    raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?…])\s+", clean) if s.strip()]
    atomic_chunks: list[str] = []
    for sent in raw_sentences:
        atomic_chunks.extend(_split_chunk_to_max_chars(sent, max_chars_per_page))

    pages_text: list[str] = []
    cur = ""
    for ch in atomic_chunks:
        cand = f"{cur} {ch}".strip() if cur else ch
        if len(cand) <= max_chars_per_page:
            cur = cand
        else:
            if cur:
                pages_text.append(cur)
            cur = ch
    if cur:
        pages_text.append(cur)

    if len(pages_text) <= 1:
        pages_text = _split_chunk_to_max_chars(clean, max_chars_per_page)

    word_counts = [max(1, len(p.split())) for p in pages_text]
    total_words = sum(word_counts)

    pages: list[dict[str, Any]] = []
    cur_start = round(float(start_s), 2)
    allocated = 0.0
    for idx, (ptxt, wc) in enumerate(zip(pages_text, word_counts)):
        if idx == len(pages_text) - 1:
            dur = max(0.2, round(float(total_dur_s) - allocated, 2))
        else:
            dur = max(0.4, round(float(total_dur_s) * (wc / total_words), 2))
            allocated = round(allocated + dur, 2)
        pages.append({
            "text": ptxt,
            "start_s": cur_start,
            "dur_s": dur,
        })
        cur_start = round(cur_start + dur, 2)

    return pages


# ---------------------------------------------------------------------------
# Reusable AGVS Vintage Field Card Helper
# ---------------------------------------------------------------------------
def draw_vintage_card(
    canvas: Image.Image,
    box: tuple[int, int, int, int],
    accent_side: str = "left",
    radius: int = 18,
    accent_color: tuple[int, int, int, int] = COLOR_CRIMSON,
    accent_width: int | None = None,
) -> None:
    """Render the unified Warm Vintage Parchment card with soft drop shadow, neatline, and accent bar."""
    x0, y0, x1, y1 = box
    cw = max(10, x1 - x0)
    ch = max(10, y1 - y0)

    pad = 48
    s_img = Image.new("RGBA", (cw + pad * 2, ch + pad * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(s_img)
    s_draw.rounded_rectangle([pad, pad, pad + cw, pad + ch], radius=radius, fill=(25, 20, 16, 97))
    s_blur = s_img.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(s_blur, (x0 - pad + 6, y0 - pad + 10))

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=COLOR_PARCHMENT_FILL, outline=COLOR_BORDER_UMBER, width=3)
    draw.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], radius=max(4, radius - 6), outline=COLOR_NEATLINE, width=1)

    if accent_side == "left":
        aw = accent_width if accent_width is not None else 20
        draw.rounded_rectangle([x0 + 18, y0 + 16, x0 + 18 + aw, y1 - 16], radius=5, fill=accent_color)
    elif accent_side == "top":
        aw = accent_width if accent_width is not None else 16
        draw.rounded_rectangle([x0 + 24, y0 + 12, x1 - 24, y0 + 12 + aw], radius=5, fill=accent_color)


# ---------------------------------------------------------------------------
# Corner Map Widget (Imperial EN & Metric RU/UA)
# ---------------------------------------------------------------------------
def render_corner_map_widget(
    gpx_points: list[dict],
    target_idx: int,
    scene_label: str,
    out_png: Path,
    canvas_size: tuple[int, int] = (3840, 2160),
    lang: str = "en",
    return_header_text: bool = False,
) -> Path | str:
    """Render a 4K transparent overlay PNG with a Warm Vintage Parchment GPX Route Map card."""
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    card_w, card_h = 760, 560
    x0 = w - card_w - 96
    y0 = 96
    x1, y1 = x0 + card_w, y0 + card_h

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=COLOR_CRIMSON)
    draw = ImageDraw.Draw(img)

    pt = gpx_points[min(max(target_idx, 0), len(gpx_points) - 1)]
    clean_scene = strip_unicode_emojis(scene_label)[:38]

    lang_norm = (lang or "en").lower()
    if lang_norm in ("ru", "ua", "uk"):
        dist_km = float(pt.get("dist_km", float(pt.get("dist_mi", 0.0)) * 1.609344))
        last_pt = gpx_points[-1] if gpx_points else {}
        tot_km = float(last_pt.get("dist_km", float(last_pt.get("dist_mi", 0.0)) * 1.609344))
        ele_m = int(pt.get("ele_m", round(float(pt.get("ele", float(pt.get("ele_ft", 0)) * 0.3048)))))
        hdr_text = f"КМ {dist_km:.1f} / {tot_km:.1f} КМ  ·  {ele_m} М"
    else:
        tot_mi = float(gpx_points[-1]["dist_mi"]) if gpx_points else 0.0
        hdr_text = f"MILE {pt['dist_mi']:.1f} / {tot_mi:.1f} MI  ·  {pt['ele_ft']} FT"

    font_hdr = load_apple_font("card_title", 32, text=hdr_text)
    font_sub = load_apple_font("card_subtitle", 26, text=clean_scene)

    draw.text((x0 + 48, y0 + 22), hdr_text, font=font_hdr, fill=COLOR_CRIMSON)
    draw.text((x0 + 48, y0 + 64), clean_scene, font=font_sub, fill=COLOR_UMBER_INK)
    draw.line([(x0 + 42, y0 + 106), (x1 - 32, y0 + 106)], fill=COLOR_NEATLINE, width=2)

    lats = [p["lat"] for p in gpx_points]
    lons = [p["lon"] for p in gpx_points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    cos_lat = math.cos(math.radians((min_lat + max_lat) / 2.0))

    dx = max((max_lon - min_lon) * cos_lat, 1e-5)
    dy = max(max_lat - min_lat, 1e-5)

    pad_x, pad_y = 52, 40
    map_x0, map_y0 = x0 + pad_x, y0 + 120 + pad_y
    map_w = card_w - 2 * pad_x
    map_h = (card_h - 120) - 2 * pad_y

    scale = min(map_w / dx, map_h / dy)
    ox = map_x0 + (map_w - dx * scale) / 2.0
    oy = map_y0 + (map_h - dy * scale) / 2.0

    def to_xy(lat: float, lon: float) -> tuple[float, float]:
        px = ox + (lon - min_lon) * cos_lat * scale
        py = oy + (max_lat - lat) * scale
        return (px, py)

    full_xy = [to_xy(p["lat"], p["lon"]) for p in gpx_points[::3]]
    if len(full_xy) >= 2:
        draw.line(full_xy, fill=(180, 168, 150, 160), width=6, joint="curve")

    done_xy = [to_xy(p["lat"], p["lon"]) for p in gpx_points[: max(target_idx + 1, 2) : 2]]
    if len(done_xy) >= 2:
        draw.line(done_xy, fill=COLOR_CRIMSON, width=8, joint="curve")

    sx, sy = to_xy(gpx_points[0]["lat"], gpx_points[0]["lon"])
    draw.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=COLOR_FOREST_GREEN, outline=(252, 249, 242, 255), width=2)

    cx, cy = to_xy(pt["lat"], pt["lon"])
    draw.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=(184, 58, 42, 75))
    draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=COLOR_CRIMSON, outline=(252, 249, 242, 255), width=3)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    if return_header_text:
        return hdr_text
    return out_png


# ---------------------------------------------------------------------------
# Telemetry HUD Widget
# ---------------------------------------------------------------------------
def render_telemetry_hud_widget(
    pt: dict,
    out_png: Path,
    highlight_reason: str = "",
    canvas_size: tuple[int, int] = (3840, 2160),
    units: str = "imperial",
    lang: str = "en",
) -> Path:
    """Render a 4K transparent overlay PNG with a Warm Vintage Parchment Telemetry HUD."""
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    hud_w, hud_h = 1380, 240
    x0, y0 = 96, 96
    x1, y1 = x0 + hud_w, y0 + hud_h

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=COLOR_CRIMSON)
    draw = ImageDraw.Draw(img)

    font_val = load_apple_font("hero_title", 72)

    if units == "metric":
        spd_kmh = pt.get("spd_kmh", pt.get("spd_mph", 0.0) * 1.609344)
        ele_m = pt.get("ele_m", int(round(pt.get("ele_ft", 0) * 0.3048)))
        font_unit = load_apple_font("section_header", 32, text="КМ/Ч ВАТТ УД/МИН М КМ/ГОД УД/ХВ")
        font_lbl = load_apple_font("card_subtitle", 26, text="СКОРОСТЬ МОЩНОСТЬ ПУЛЬС УКЛОН ШВИДКІСТЬ ПОТУЖНІСТЬ УХИЛ")
        if lang in ("ua", "uk"):
            metrics = [
                ("ШВИДКІСТЬ", f"{spd_kmh:.1f}", "КМ/ГОД", COLOR_CRIMSON),
                ("ПОТУЖНІСТЬ", str(pt.get("pwr", 0)), "ВАТТ", COLOR_CRIMSON),
                ("ПУЛЬС", str(pt.get("hr", 0)), "УД/ХВ", COLOR_CRIMSON),
                ("УХИЛ", f"{pt.get('grad_pct', 0.0):+.1f}%", f"{ele_m} М", COLOR_FOREST_GREEN),
            ]
        elif lang == "ru":
            metrics = [
                ("СКОРОСТЬ", f"{spd_kmh:.1f}", "КМ/Ч", COLOR_CRIMSON),
                ("МОЩНОСТЬ", str(pt.get("pwr", 0)), "ВАТТ", COLOR_CRIMSON),
                ("ПУЛЬС", str(pt.get("hr", 0)), "УД/МИН", COLOR_CRIMSON),
                ("УКЛОН", f"{pt.get('grad_pct', 0.0):+.1f}%", f"{ele_m} М", COLOR_FOREST_GREEN),
            ]
        else:
            metrics = [
                ("SPEED", f"{spd_kmh:.1f}", "KM/H", COLOR_CRIMSON),
                ("POWER", str(pt.get("pwr", 0)), "WATTS", COLOR_CRIMSON),
                ("HEART RATE", str(pt.get("hr", 0)), "BPM", COLOR_CRIMSON),
                ("GRADE", f"{pt.get('grad_pct', 0.0):+.1f}%", f"{ele_m} M", COLOR_FOREST_GREEN),
            ]
    else:
        font_unit = load_apple_font("section_header", 32)
        font_lbl = load_apple_font("card_subtitle", 26)
        metrics = [
            ("SPEED", f"{pt.get('spd_mph', 0.0):.1f}", "MPH", COLOR_CRIMSON),
            ("POWER", str(pt.get("pwr", 0)), "WATTS", COLOR_CRIMSON),
            ("HEART RATE", str(pt.get("hr", 0)), "BPM", COLOR_CRIMSON),
            ("GRADE", f"{pt.get('grad_pct', 0.0):+.1f}%", f"{pt.get('ele_ft', 0)} FT", COLOR_FOREST_GREEN),
        ]

    col_w = (hud_w - 44) // 4
    for idx, (label, val, unit, accent_col) in enumerate(metrics):
        cx = x0 + 44 + idx * col_w + 24
        if idx > 0:
            draw.line([(x0 + 44 + idx * col_w, y0 + 26), (x0 + 44 + idx * col_w, y1 - 26)], fill=COLOR_NEATLINE, width=2)
        draw.text((cx, y0 + 24), label, font=font_lbl, fill=COLOR_UMBER_INK)
        draw.text((cx, y0 + 64), val, font=font_val, fill=COLOR_ESPRESSO_INK)
        draw.text((cx, y0 + 160), unit, font=font_unit, fill=accent_col)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


def render_live_telemetry_hud_series(
    gpx_points: list[dict],
    start_idx: int,
    timeline_start_s: float,
    dur_s: float,
    out_dir: Path,
    step_s: float = 1.0,
    canvas_size: tuple[int, int] = (3840, 2160),
) -> list[tuple[str, float, float]]:
    """Render a 1 Hz series of 4K transparent Telemetry HUD PNGs."""
    out_dir.mkdir(parents=True, exist_ok=True)
    entries: list[tuple[str, float, float]] = []
    t = 0.0
    sec_step = 0
    while t < dur_s - 1e-4:
        cur_dur = min(step_s, round(dur_s - t, 2))
        tl_s = round(timeline_start_s + t, 2)
        idx = min(max(start_idx + sec_step, 0), len(gpx_points) - 1)
        pt = gpx_points[idx]
        fname = f"hud_{int(round(tl_s * 10)):04d}.png"
        out_png = out_dir / fname
        render_telemetry_hud_widget(pt, out_png, canvas_size=canvas_size)
        entries.append((f"{out_dir.name}/{fname}", tl_s, cur_dur))
        t = round(t + cur_dur, 2)
        sec_step += max(1, int(round(step_s)))
    return entries


# ---------------------------------------------------------------------------
# Character Callout & Flashback Badges
# ---------------------------------------------------------------------------
def render_character_callout_badge(
    name_line: str,
    role_line: str,
    out_png: Path,
    position: str = "bottom_left",
    accent_color: tuple[int, int, int, int] = COLOR_CRIMSON,
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """Render a 4K transparent overlay PNG with a Warm Vintage Parchment Character Card."""
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    clean_name = strip_unicode_emojis(name_line)
    clean_role = strip_unicode_emojis(role_line)

    font_name = load_apple_font("card_title", 84, text=clean_name)
    font_role = load_apple_font("card_subtitle", 60, text=clean_role)

    dummy = Image.new("RGBA", (100, 100))
    d_measure = ImageDraw.Draw(dummy)

    nb = d_measure.textbbox((0, 0), clean_name, font=font_name)
    rb = d_measure.textbbox((0, 0), clean_role, font=font_role)
    name_w = nb[2] - nb[0]
    role_w = rb[2] - rb[0]

    role_lines = [clean_role]
    card_w = max(2200, min(2900, max(name_w, role_w) + 160))
    max_text_w = card_w - 160

    if role_w > max_text_w:
        words = clean_role.split()
        wrapped = []
        cur = ""
        for word in words:
            cand = f"{cur} {word}".strip() if cur else word
            cb = d_measure.textbbox((0, 0), cand, font=font_role)
            if cb[2] - cb[0] <= max_text_w:
                cur = cand
            else:
                if cur:
                    wrapped.append(cur)
                cur = word
        if cur:
            wrapped.append(cur)
        role_lines = wrapped

    is_wrapped = len(role_lines) > 1
    card_h = 320 if is_wrapped else 250

    if position == "bottom_right":
        x0 = w - card_w - 96
        y0 = 1640 if is_wrapped else 1710
    elif position == "top_left":
        x0 = 96
        y0 = 96
    else:
        x0 = 96
        y0 = 1640 if is_wrapped else 1710

    x1, y1 = x0 + card_w, y0 + card_h

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=20, accent_color=accent_color, accent_width=20)
    draw = ImageDraw.Draw(img)

    text_x = x0 + 64
    line1_y = y0 + 36
    if "@akomlik" in clean_name:
        parts = clean_name.split("@akomlik")
        cur_x = text_x
        if parts[0]:
            draw.text((cur_x, line1_y), parts[0], font=font_name, fill=COLOR_ESPRESSO_INK)
            cur_x += d_measure.textbbox((0, 0), parts[0], font=font_name)[2]
        draw.text((cur_x, line1_y), "@akomlik", font=font_name, fill=COLOR_CRIMSON)
        cur_x += d_measure.textbbox((0, 0), "@akomlik", font=font_name)[2]
        if len(parts) > 1 and parts[1]:
            draw.text((cur_x, line1_y), parts[1], font=font_name, fill=COLOR_ESPRESSO_INK)
    else:
        draw.text((text_x, line1_y), clean_name, font=font_name, fill=COLOR_ESPRESSO_INK)

    line2_y = line1_y + 94
    for rl in role_lines:
        draw.text((text_x, line2_y), rl, font=font_role, fill=COLOR_UMBER_INK)
        line2_y += 66

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


def render_flashback_memory_badge(
    date_event_line: str,
    title_line: str,
    detail_line: str,
    out_png: Path,
    position: str = "top_left",
    accent_color: tuple[int, int, int, int] = COLOR_CRIMSON,
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """Render a retro/archival memory card on Warm Vintage Parchment."""
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    clean_date = strip_unicode_emojis(date_event_line)
    clean_title = strip_unicode_emojis(title_line)
    clean_detail = strip_unicode_emojis(detail_line)

    f_pill = load_apple_font("section_header", 36, text=clean_date)
    f_title = load_apple_font("card_title", 84, text=clean_title)
    f_sub = load_apple_font("card_subtitle", 60, text=clean_detail)

    dummy = Image.new("RGBA", (100, 100))
    d_measure = ImageDraw.Draw(dummy)

    pb = d_measure.textbbox((0, 0), clean_date, font=f_pill)
    tb = d_measure.textbbox((0, 0), clean_title, font=f_title)
    db = d_measure.textbbox((0, 0), clean_detail, font=f_sub)

    pill_w = pb[2] - pb[0] + 44
    content_w = max(pill_w, tb[2] - tb[0], db[2] - db[0])
    card_w = max(2200, min(2900, content_w + 160))
    card_h = 310

    if position == "bottom_left":
        x0 = 96
        y0 = 1640
    elif position == "top_right":
        x0 = w - card_w - 96
        y0 = 96
    else:
        x0 = 96
        y0 = 96

    x1, y1 = x0 + card_w, y0 + card_h

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=accent_color, accent_width=20)
    draw = ImageDraw.Draw(img)

    px0 = x0 + 64
    py0 = y0 + 26
    draw.rounded_rectangle([px0, py0, px0 + pill_w, py0 + 48], radius=10, fill=accent_color)
    draw.text((px0 + 22, py0 + 6), clean_date, font=f_pill, fill=(252, 249, 242, 255))

    draw.text((x0 + 64, y0 + 94), clean_title, font=f_title, fill=COLOR_ESPRESSO_INK)
    draw.text((x0 + 64, y0 + 198), clean_detail, font=f_sub, fill=COLOR_UMBER_INK)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


# ---------------------------------------------------------------------------
# Speech Translation Card ("Translation Is Always Primary")
# ---------------------------------------------------------------------------
def render_translation_subtitle_card(
    spoken_text: str = "",
    english_translation: str | None = None,
    out_png: Path | None = None,
    canvas_size: tuple[int, int] = (3840, 2160),
    translation_text: str | None = None,
    card_width: int | None = None,
    card_height: int | None = None,
    single_language: bool = True,
    target_lang: str = "ru",
    return_layout_meta: bool = False,
) -> Path | dict[str, Any]:
    """
    Render on-camera speech translation as a centered Warm Vintage Parchment Card.
    - single_language=True: renders only the target-language translation in 76pt Bold Espresso.
    - single_language=False: enforces 'Translation Is Always Primary' — renders primary translation
      (76pt Bold Espresso) ABOVE the smaller dimmer spoken original (56pt Umber/Crimson).
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    raw_trans = translation_text if translation_text is not None else (english_translation or spoken_text or "")
    clean_trans = strip_unicode_emojis(raw_trans)

    if clean_trans.startswith(("«", '"', "“", "'")) and clean_trans.endswith(("»", '"', "”", "'")):
        clean_trans = clean_trans[1:-1].strip()

    is_cyrillic = bool(re.search(r"[\u0400-\u04FF]", clean_trans))
    if target_lang in ("ru", "ua", "uk") or is_cyrillic:
        clean_trans = f"«{clean_trans}»"
    else:
        clean_trans = f'"{clean_trans}"'

    dummy = Image.new("RGBA", (100, 100))
    d_measure = ImageDraw.Draw(dummy)

    max_card_w = 3000
    min_card_w = 2400
    max_text_w = max_card_w - 200

    translation_font_pt = 76
    spoken_font_pt = 0
    translation_y = 0
    spoken_y: int | None = None

    if single_language:
        f_trans = load_apple_font("card_title", translation_font_pt, text=clean_trans)
        words = clean_trans.split()
        trans_lines = []
        cur = ""
        for word in words:
            cand = f"{cur} {word}".strip() if cur else word
            cb = d_measure.textbbox((0, 0), cand, font=f_trans)
            if cb[2] - cb[0] <= max_text_w:
                cur = cand
            else:
                if cur:
                    trans_lines.append(cur)
                cur = word
        if cur:
            trans_lines.append(cur)

        longest_trans_w = max(
            (d_measure.textbbox((0, 0), line, font=f_trans)[2] - d_measure.textbbox((0, 0), line, font=f_trans)[0])
            for line in trans_lines
        ) if trans_lines else 0

        calc_w = max(min_card_w, min(max_card_w, longest_trans_w + 220))
        card_w = max(calc_w, card_width) if card_width else calc_w

        is_wrapped = len(trans_lines) > 1
        calc_h = 280 if is_wrapped else 200
        card_h = max(calc_h, card_height) if card_height else calc_h

        x0 = (w - card_w) // 2
        y0 = 1680 if is_wrapped else 1750
        x1, y1 = x0 + card_w, y0 + card_h

        draw_vintage_card(img, (x0, y0, x1, y1), accent_side="top", radius=20, accent_color=COLOR_CRIMSON, accent_width=16)
        draw = ImageDraw.Draw(img)

        line_h = 88
        if is_wrapped:
            start_y = y0 + 44
        else:
            first_bbox = d_measure.textbbox((0, 0), trans_lines[0], font=f_trans) if trans_lines else (0, 0, 0, 50)
            text_h = first_bbox[3] - first_bbox[1]
            start_y = y0 + (card_h - text_h) // 2 - 4

        translation_y = start_y
        for idx, line in enumerate(trans_lines):
            lb = d_measure.textbbox((0, 0), line, font=f_trans)
            lw = lb[2] - lb[0]
            lx = x0 + (card_w - lw) // 2
            ly = start_y + idx * line_h
            draw.text((lx, ly), line, font=f_trans, fill=COLOR_ESPRESSO_INK)
    else:
        # Bilingual stacked format: Primary Translation ABOVE dimmer Spoken Original
        spoken_font_pt = 56
        clean_spoken = strip_unicode_emojis(spoken_text)
        spoken_is_cyrillic = bool(re.search(r"[\u0400-\u04FF]", clean_spoken))
        if spoken_is_cyrillic:
            if not (clean_spoken.startswith("«") and clean_spoken.endswith("»")):
                clean_spoken = clean_spoken.strip('\'"')
                clean_spoken = f"«{clean_spoken}»"
        else:
            if not (clean_spoken.startswith('"') and clean_spoken.endswith('"')):
                clean_spoken = clean_spoken.strip('\'"«»')
                clean_spoken = f'"{clean_spoken}"'

        f_trans = load_apple_font("card_title", translation_font_pt, text=clean_trans)
        f_spoken = load_apple_font("card_subtitle", spoken_font_pt, text=clean_spoken)

        b1 = d_measure.textbbox((0, 0), clean_spoken, font=f_spoken)
        w1 = b1[2] - b1[0]

        words = clean_trans.split()
        trans_lines = []
        cur = ""
        for word in words:
            cand = f"{cur} {word}".strip() if cur else word
            cb = d_measure.textbbox((0, 0), cand, font=f_trans)
            if cb[2] - cb[0] <= max_text_w:
                cur = cand
            else:
                if cur:
                    trans_lines.append(cur)
                cur = word
        if cur:
            trans_lines.append(cur)

        longest_trans_w = max(
            (d_measure.textbbox((0, 0), line, font=f_trans)[2] - d_measure.textbbox((0, 0), line, font=f_trans)[0])
            for line in trans_lines
        ) if trans_lines else 0
        content_w = max(w1, longest_trans_w)
        calc_w = max(min_card_w, min(max_card_w, content_w + 180))
        card_w = max(calc_w, card_width) if card_width else calc_w

        is_wrapped = len(trans_lines) > 1
        calc_h = 350 if is_wrapped else 260
        card_h = max(calc_h, card_height) if card_height else calc_h

        x0 = (w - card_w) // 2
        y0 = 1640 if is_wrapped else 1710
        x1, y1 = x0 + card_w, y0 + card_h

        draw_vintage_card(img, (x0, y0, x1, y1), accent_side="top", radius=20, accent_color=COLOR_CRIMSON, accent_width=16)
        draw = ImageDraw.Draw(img)

        translation_y = y0 + 38
        cur_trans_y = translation_y
        for line in trans_lines:
            lb = d_measure.textbbox((0, 0), line, font=f_trans)
            lw = lb[2] - lb[0]
            lx = x0 + (card_w - lw) // 2
            draw.text((lx, cur_trans_y), line, font=f_trans, fill=COLOR_ESPRESSO_INK)
            cur_trans_y += 86

        spoken_y = cur_trans_y + 10
        t1_x = x0 + (card_w - w1) // 2
        draw.text((t1_x, spoken_y), clean_spoken, font=f_spoken, fill=COLOR_UMBER_INK)

    if out_png:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_png, "PNG", compress_level=1)

    if return_layout_meta:
        return {
            "out_png": out_png,
            "card_box": (x0, y0, x1, y1),
            "translation_y": translation_y,
            "spoken_y": spoken_y,
            "translation_font_pt": translation_font_pt,
            "spoken_font_pt": spoken_font_pt,
            "single_language": single_language,
        }
    return out_png


def render_strava_comparison_vintage_card(
    out_png: Path,
    header_text: str = "STRAVA LONGITUDINAL COMPARISON · COLL DE FEMENIA",
    subheader_text: str = "Same 195W Climbing Effort · Accelerated Aging Tax on Zero Testosterone (ADT)",
    badge1_text: str = "2024 NORMAL-T:  195 W  @  118 BPM",
    badge2_text: str = "2026 ZERO-T:  191 W  @  141 BPM (+23 BPM TAX)",
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """Render a Strava Longitudinal Comparison Card on Warm Vintage Parchment."""
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    header_text = strip_unicode_emojis(header_text)
    subheader_text = strip_unicode_emojis(subheader_text)
    badge1_text = strip_unicode_emojis(badge1_text)
    badge2_text = strip_unicode_emojis(badge2_text)

    f_hdr = load_apple_font("hero_title", 64, text=header_text)
    f_sub = load_apple_font("card_subtitle", 46, text=subheader_text)
    f_badge = load_apple_font("section_header", 54, text=badge1_text + badge2_text)

    dummy = Image.new("RGBA", (100, 100))
    d_m = ImageDraw.Draw(dummy)

    hb = d_m.textbbox((0, 0), header_text, font=f_hdr)
    hw = hb[2] - hb[0]
    sb = d_m.textbbox((0, 0), subheader_text, font=f_sub)
    sw = sb[2] - sb[0]

    b_1 = d_m.textbbox((0, 0), badge1_text, font=f_badge)
    bw1 = b_1[2] - b_1[0] + 54
    b_2 = d_m.textbbox((0, 0), badge2_text, font=f_badge)
    bw2 = b_2[2] - b_2[0] + 54

    content_w = max(hw, sw, 64 + bw1 + 36 + bw2) + 140
    cw = max(2800, min(3400, content_w))
    ch = 370
    x0, y0 = 96, 96
    x1, y1 = x0 + cw, y0 + ch

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=COLOR_CRIMSON, accent_width=20)
    draw = ImageDraw.Draw(img)

    draw.text((x0 + 64, y0 + 32), header_text, font=f_hdr, fill=COLOR_ESPRESSO_INK)
    draw.text((x0 + 66, y0 + 112), subheader_text, font=f_sub, fill=COLOR_UMBER_INK)

    by = y0 + 196
    draw.rounded_rectangle([x0 + 64, by, x0 + 64 + bw1, by + 88], radius=14, fill=COLOR_FOREST_GREEN)
    draw.text((x0 + 91, by + 16), badge1_text, font=f_badge, fill=(252, 249, 242, 255))

    bx2 = x0 + 64 + bw1 + 36
    draw.rounded_rectangle([bx2, by, bx2 + bw2, by + 88], radius=14, fill=COLOR_CRIMSON)
    draw.text((bx2 + 27, by + 16), badge2_text, font=f_badge, fill=(252, 249, 242, 255))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


def _expand_auto_paginated_sub_items(ov: dict) -> list[dict]:
    """Expand single-item translation_subtitle overlays exceeding max_chars_per_page into sequential pages."""
    if "pages" in ov:
        return list(ov["pages"])

    max_chars = int(ov.get("max_chars_per_page", 95))
    spoken = ov.get("spoken", "")
    spoken_is_cyr = bool(re.search(r"[\u0400-\u04FF]", spoken))
    spoken_lang = ov.get("spoken_lang", "ru" if spoken_is_cyr else "en")

    primary_text = (
        (ov.get("russian") or ov.get("translation", ""))
        if spoken_lang == "en"
        else (ov.get("english") or ov.get("translation", ""))
    )
    if len(strip_unicode_emojis(primary_text)) <= max_chars:
        return [ov]

    start_s = float(ov["start_s"])
    total_dur_s = float(ov["dur_s"])
    base_stem = Path(ov.get("file", "sub.png")).stem
    pages = paginate_speech_segments(primary_text, start_s=start_s, total_dur_s=total_dur_s, max_chars_per_page=max_chars)
    if len(pages) <= 1:
        return [ov]

    # If secondary language also exists (e.g. spoken_lang == "es"), paginate or slice proportionally
    secondary_ru = ov.get("russian") or ov.get("translation_ru") or ""
    ru_pages = (
        paginate_speech_segments(secondary_ru, start_s=start_s, total_dur_s=total_dur_s, max_chars_per_page=max_chars)
        if secondary_ru and spoken_lang not in ("en", "ru")
        else []
    )

    expanded: list[dict] = []
    for idx, pg in enumerate(pages):
        item = dict(ov)
        item["file"] = f"{base_stem}_p{idx + 1:02d}.png"
        item["start_s"] = pg["start_s"]
        item["dur_s"] = pg["dur_s"]
        if spoken_lang == "en":
            item["russian"] = pg["text"]
            item["translation"] = pg["text"]
        elif spoken_lang == "ru":
            item["english"] = pg["text"]
            item["translation"] = pg["text"]
        else:
            item["english"] = pg["text"]
            item["translation"] = pg["text"]
            if ru_pages:
                item["russian"] = ru_pages[min(idx, len(ru_pages) - 1)]["text"]
        expanded.append(item)
    return expanded


def render_declarative_overlays(
    overlays_spec: list[dict],
    overlays_dir: Path,
    raw_dir: Path | None = None,
    skip_render: bool = False,
    edition: str | None = None,
    cuts_spec: list[dict] | None = None,
    hud_mode: str = "auto",
) -> dict[str, list[dict]] | list[dict]:
    """Render declarative 4K RGBA overlay PNGs and expand edition-specific timeline item lists."""
    overlays_dir.mkdir(parents=True, exist_ok=True)
    live_hud_dir = overlays_dir / "live_hud"
    live_hud_dir.mkdir(parents=True, exist_ok=True)
    live_hud_ru_dir = overlays_dir / "live_hud_ru"
    live_hud_ru_dir.mkdir(parents=True, exist_ok=True)

    ffprobe_bin = find_binary("ffprobe") or "ffprobe"
    gpx_cache: dict[str, list[dict]] = {}

    def get_gpx(gpx_name: str) -> list[dict]:
        if not raw_dir or not gpx_name:
            return []
        if gpx_name not in gpx_cache:
            gp = raw_dir / gpx_name
            gpx_cache[gpx_name] = load_gpx_stream(gp) if gp.exists() else []
        return gpx_cache[gpx_name]

    auto_gpx_pts: list[dict] = []
    any_cut_hud_override = any(c.get("hud") is True for c in (cuts_spec or []))
    if raw_dir and raw_dir.exists() and cuts_spec and ((hud_mode or "auto").lower() != "off" or any_cut_hud_override):
        primary_gpx, _ = select_primary_ride_gpx(raw_dir)
        if primary_gpx:
            auto_gpx_pts = get_gpx(primary_gpx.name)

    expanded_items_en: list[dict] = []
    expanded_items_ru: list[dict] = []

    top_left_windows = [
        (float(ov["start_s"]), float(ov["start_s"]) + float(ov["dur_s"]))
        for ov in (overlays_spec or [])
        if ov.get("position") == "top_left" and ov.get("kind") not in ("live_telemetry_hud", "telemetry_hud")
    ]
    if auto_gpx_pts and cuts_spec:
        tl_cursor = 0.0
        for cut in cuts_spec:
            dur_s = float(cut["dur"])
            cut_start_s = round(tl_cursor, 2)
            tl_cursor = round(tl_cursor + dur_s, 2)

            src = str(cut.get("source", ""))
            eff_hud_mode = "auto" if cut.get("hud") is True else hud_mode
            if (
                cut.get("is_still")
                or cut.get("hud") is False
                or src.startswith(("bookend_", "ai_", "pollentia_spotlight", "foguero_palace_spotlight"))
                or not should_show_telemetry_hud(src, rolling_speed_mph=99.0, mode=eff_hud_mode)
            ):
                continue

            cp = raw_dir / src if raw_dir else None
            if not cp or not cp.exists():
                continue

            ct = None
            try:
                cmd = [
                    ffprobe_bin, "-v", "error",
                    "-show_entries", "format_tags=creation_time",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(cp),
                ]
                out_ct = subprocess.check_output(cmd).decode().strip()
                if out_ct:
                    ct = dt.datetime.fromisoformat(out_ct.replace("Z", "+00:00"))
            except Exception:
                pass
            if ct is None:
                continue

            src_in = float(cut.get("src_in", 0.0))
            t = 0.0
            step_s = 1.0
            while t < dur_s - 1e-4:
                cur_dur = min(step_s, round(dur_s - t, 2))
                step_tl_s = round(cut_start_s + t, 2)
                sec_ts = ct + dt.timedelta(seconds=src_in + t)
                t = round(t + cur_dur, 2)

                if any(step_tl_s < w_end and (step_tl_s + cur_dur) > w_start for w_start, w_end in top_left_windows):
                    continue

                best_pt = None
                best_diff = 999999.0
                for p in auto_gpx_pts:
                    diff = abs((p["time"] - sec_ts).total_seconds())
                    if diff < best_diff:
                        best_diff = diff
                        best_pt = p

                if best_pt is None or best_diff > 3.0:
                    continue
                if not should_show_telemetry_hud(src, rolling_speed_mph=best_pt["spd_mph"], mode=eff_hud_mode):
                    continue

                pt = dict(best_pt)
                rel_fname_en = f"live_hud/hud_{int(round(step_tl_s * 10)):04d}.png"
                out_png_en = overlays_dir / rel_fname_en
                if not skip_render:
                    render_telemetry_hud_widget(pt, out_png_en, units="imperial", lang="en")
                expanded_items_en.append({
                    "file": rel_fname_en,
                    "start_s": step_tl_s,
                    "dur_s": cur_dur,
                    "track": "V4",
                    "fade_in_s": 0.0,
                    "fade_out_s": 0.0,
                    "desc": f"Live Telemetry HUD @ {step_tl_s:.1f}s ({src})",
                })

                rel_fname_ru = f"live_hud_ru/hud_{int(round(step_tl_s * 10)):04d}.png"
                out_png_ru = overlays_dir / rel_fname_ru
                if not skip_render:
                    render_telemetry_hud_widget(pt, out_png_ru, units="metric", lang="ru")
                expanded_items_ru.append({
                    "file": rel_fname_ru,
                    "start_s": step_tl_s,
                    "dur_s": cur_dur,
                    "track": "V4",
                    "fade_in_s": 0.0,
                    "fade_out_s": 0.0,
                    "desc": f"Live Telemetry HUD @ {step_tl_s:.1f}s (Metric, {src})",
                })

    for ov in overlays_spec:
        kind = ov.get("kind", "character_badge")
        accent_name = (ov.get("accent") or "crimson").lower()
        accent_col = COLOR_FOREST_GREEN if "green" in accent_name else COLOR_CRIMSON
        pos = ov.get("position", "bottom_left")

        if kind == "static_png" and Path(ov.get("file", "")).name.lower().startswith("hud_"):
            continue

        if kind in ("live_telemetry_hud", "telemetry_hud"):
            if auto_gpx_pts and cuts_spec:
                continue
            start_s = float(ov["start_s"])
            dur_s = float(ov["dur_s"])
            step_s = float(ov.get("step_s", 1.0))
            pts = get_gpx(ov.get("gpx_file", ""))
            gpx_start_idx = ov.get("gpx_start_idx")
            if gpx_start_idx is None:
                clip_file = ov.get("clip_file") or ov.get("clip")
                if clip_file and raw_dir and pts:
                    cp = raw_dir / clip_file
                    if cp.exists():
                        try:
                            cmd = [
                                ffprobe_bin, "-v", "error",
                                "-show_entries", "format_tags=creation_time",
                                "-of", "default=noprint_wrappers=1:nokey=1",
                                str(cp),
                            ]
                            out_ct = subprocess.check_output(cmd).decode().strip()
                            if out_ct:
                                ct = dt.datetime.fromisoformat(out_ct.replace("Z", "+00:00"))
                                clip_start_time = ct + dt.timedelta(seconds=float(ov.get("src_in", 0.0)))
                                best_idx = 0
                                best_diff = 999999.0
                                for i, p in enumerate(pts):
                                    diff = abs((p["time"] - clip_start_time).total_seconds())
                                    if diff < best_diff:
                                        best_diff = diff
                                        best_idx = i
                                gpx_start_idx = best_idx
                        except Exception:
                            pass
            if gpx_start_idx is None:
                gpx_start_idx = len(pts) // 4 if pts else 0
            else:
                gpx_start_idx = int(gpx_start_idx)
            prof = ov.get("metrics_profile") or {}

            steps = []
            t = 0.0
            sec_idx = 0
            while t < dur_s - 1e-4:
                cur_dur = min(step_s, round(dur_s - t, 2))
                tl_s = round(start_s + t, 2)
                steps.append((sec_idx, tl_s, cur_dur))
                t = round(t + cur_dur, 2)
                sec_idx += 1

            n_steps = len(steps)
            for s_idx, tl_s, cur_dur in steps:
                if pts:
                    pt = dict(pts[min(max(gpx_start_idx + s_idx, 0), len(pts) - 1)])
                else:
                    pt = {
                        "spd_mph": float(ov.get("spd_mph", 15.5)),
                        "pwr": int(ov.get("pwr", 185)),
                        "hr": int(ov.get("hr", 138)),
                        "grad_pct": float(ov.get("grad_pct", 5.2)),
                        "ele_ft": int(ov.get("ele_ft", 850)),
                    }
                    if not prof:
                        jitter_w = (-4, 3, 7, -2, 5, -6, 2, 4)[s_idx % 8]
                        jitter_spd = (-0.2, 0.1, 0.3, 0.0, -0.1, 0.2, -0.2, 0.1)[s_idx % 8]
                        jitter_hr = (0, 0, 1, 1, 0, -1, 0, 1)[s_idx % 8]
                        pt["pwr"] = max(0, int(pt["pwr"] + jitter_w))
                        pt["spd_mph"] = max(0.0, round(pt["spd_mph"] + jitter_spd, 1))
                        pt["hr"] = max(60, int(pt["hr"] + jitter_hr))

                for key in ("spd_mph", "pwr", "hr", "grad_pct", "ele_ft"):
                    if key in prof and isinstance(prof[key], list) and prof[key]:
                        val = prof[key][min(s_idx, len(prof[key]) - 1)]
                        pt[key] = int(val) if key in ("pwr", "hr", "ele_ft") else float(val)

                rel_fname_en = f"live_hud/hud_{int(round(tl_s * 10)):04d}.png"
                out_png_en = overlays_dir / rel_fname_en
                if not skip_render:
                    render_telemetry_hud_widget(pt, out_png_en, units="imperial", lang="en")

                expanded_items_en.append({
                    "file": rel_fname_en,
                    "start_s": tl_s,
                    "dur_s": cur_dur,
                    "track": ov.get("track", "V4"),
                    "fade_in_s": 0.25 if s_idx == 0 else 0.0,
                    "fade_out_s": 0.30 if s_idx == n_steps - 1 else 0.0,
                    "desc": ov.get("desc", f"Live Telemetry HUD @ {tl_s:.1f}s"),
                })

                rel_fname_ru = f"live_hud_ru/hud_{int(round(tl_s * 10)):04d}.png"
                out_png_ru = overlays_dir / rel_fname_ru
                if not skip_render:
                    render_telemetry_hud_widget(pt, out_png_ru, units="metric", lang="ru")

                expanded_items_ru.append({
                    "file": rel_fname_ru,
                    "start_s": tl_s,
                    "dur_s": cur_dur,
                    "track": ov.get("track", "V4"),
                    "fade_in_s": 0.25 if s_idx == 0 else 0.0,
                    "fade_out_s": 0.30 if s_idx == n_steps - 1 else 0.0,
                    "desc": ov.get("desc", f"Live Telemetry HUD @ {tl_s:.1f}s (Metric)"),
                })
            continue

        if kind == "translation_subtitle":
            sub_items = _expand_auto_paginated_sub_items(ov)
            n_sub = len(sub_items)
            for p_idx, s_item in enumerate(sub_items):
                base_name = Path(s_item.get("file", ov.get("file", f"sub_{p_idx+1:02d}.png"))).stem
                start_s = float(s_item["start_s"])
                dur_s = float(s_item["dur_s"])
                spoken = s_item.get("spoken", "")
                spoken_is_cyr = bool(re.search(r"[\u0400-\u04FF]", spoken))
                spoken_lang = s_item.get("spoken_lang", "ru" if spoken_is_cyr else "en")
                fade_in = float(s_item.get("fade_in_s", 0.25 if p_idx == 0 else 0.0))
                fade_out = float(s_item.get("fade_out_s", 0.30 if p_idx == n_sub - 1 else 0.0))

                if spoken_lang == "en":
                    trans_ru = s_item.get("russian") or s_item.get("translation", "")
                    fname_ru = f"{base_name}_ru.png" if not base_name.endswith("_ru") else f"{base_name}.png"
                    if not skip_render:
                        render_translation_subtitle_card(
                            translation_text=trans_ru,
                            out_png=overlays_dir / fname_ru,
                            single_language=True,
                            target_lang="ru",
                        )
                    expanded_items_ru.append({
                        "file": fname_ru,
                        "start_s": start_s,
                        "dur_s": dur_s,
                        "track": s_item.get("track", ov.get("track", "V3")),
                        "fade_in_s": fade_in,
                        "fade_out_s": fade_out,
                        "desc": s_item.get("desc", f"RU Translation Subtitle: {trans_ru[:30]}"),
                    })
                elif spoken_lang == "ru":
                    trans_en = s_item.get("english") or s_item.get("translation", "")
                    fname_en = f"{base_name}_en.png" if not base_name.endswith("_en") else f"{base_name}.png"
                    if not skip_render:
                        render_translation_subtitle_card(
                            translation_text=trans_en,
                            out_png=overlays_dir / fname_en,
                            single_language=True,
                            target_lang="en",
                        )
                    expanded_items_en.append({
                        "file": fname_en,
                        "start_s": start_s,
                        "dur_s": dur_s,
                        "track": s_item.get("track", ov.get("track", "V3")),
                        "fade_in_s": fade_in,
                        "fade_out_s": fade_out,
                        "desc": s_item.get("desc", f"EN Translation Subtitle: {trans_en[:30]}"),
                    })
                else:
                    trans_en = s_item.get("english") or s_item.get("translation", "")
                    trans_ru = s_item.get("russian") or s_item.get("translation_ru") or trans_en
                    if trans_en:
                        fname_en = f"{base_name}_en.png" if not base_name.endswith("_en") else f"{base_name}.png"
                        if not skip_render:
                            render_translation_subtitle_card(
                                translation_text=trans_en,
                                out_png=overlays_dir / fname_en,
                                single_language=True,
                                target_lang="en",
                            )
                        expanded_items_en.append({
                            "file": fname_en,
                            "start_s": start_s,
                            "dur_s": dur_s,
                            "track": s_item.get("track", ov.get("track", "V3")),
                            "fade_in_s": fade_in,
                            "fade_out_s": fade_out,
                            "desc": s_item.get("desc", f"EN Translation Subtitle: {trans_en[:30]}"),
                        })
                    if trans_ru:
                        fname_ru = f"{base_name}_ru.png" if not base_name.endswith("_ru") else f"{base_name}.png"
                        if not skip_render:
                            render_translation_subtitle_card(
                                translation_text=trans_ru,
                                out_png=overlays_dir / fname_ru,
                                single_language=True,
                                target_lang="ru",
                            )
                        expanded_items_ru.append({
                            "file": fname_ru,
                            "start_s": start_s,
                            "dur_s": dur_s,
                            "track": s_item.get("track", ov.get("track", "V3")),
                            "fade_in_s": fade_in,
                            "fade_out_s": fade_out,
                            "desc": s_item.get("desc", f"RU Translation Subtitle: {trans_ru[:30]}"),
                        })
            continue

        file_en = ov["file"]
        stem = Path(file_en).stem
        ext = Path(file_en).suffix
        file_ru = f"{stem}_ru{ext}"
        out_png_en = overlays_dir / file_en
        out_png_ru = overlays_dir / file_ru

        has_ru_text = any(k.endswith("_ru") for k in ov.keys()) or kind == "corner_map"

        if not skip_render:
            if kind in ("character_badge", "context_card", "stat_callout"):
                render_character_callout_badge(
                    ov["title"],
                    ov["subtitle"],
                    out_png_en,
                    position=pos,
                    accent_color=accent_col,
                )
                title_ru = ov.get("title_ru") or ov["title"]
                sub_ru = ov.get("subtitle_ru") or ov["subtitle"]
                render_character_callout_badge(
                    title_ru,
                    sub_ru,
                    out_png_ru,
                    position=pos,
                    accent_color=accent_col,
                )
            elif kind == "flashback_badge":
                render_flashback_memory_badge(
                    ov["date_event"],
                    ov["title"],
                    ov["detail"],
                    out_png_en,
                    position=pos,
                    accent_color=accent_col,
                )
                date_ru = ov.get("date_event_ru") or ov["date_event"]
                title_ru = ov.get("title_ru") or ov["title"]
                detail_ru = ov.get("detail_ru") or ov["detail"]
                render_flashback_memory_badge(
                    date_ru,
                    title_ru,
                    detail_ru,
                    out_png_ru,
                    position=pos,
                    accent_color=accent_col,
                )
            elif kind == "strava_comparison":
                hdr_en = ov.get("header", "STRAVA LONGITUDINAL COMPARISON · COLL DE FEMENIA")
                sub_en = ov.get("subheader", "Same 195W Climbing Effort · Accelerated Aging Tax on Zero Testosterone (ADT)")
                b1_en = ov.get("badge1", "2024 NORMAL-T:  195 W  @  118 BPM")
                b2_en = ov.get("badge2", "2026 ZERO-T:  191 W  @  141 BPM (+23 BPM TAX)")
                render_strava_comparison_vintage_card(
                    out_png_en,
                    header_text=hdr_en,
                    subheader_text=sub_en,
                    badge1_text=b1_en,
                    badge2_text=b2_en,
                )
                hdr_ru = ov.get("header_ru") or hdr_en
                sub_ru = ov.get("subheader_ru") or sub_en
                b1_ru = ov.get("badge1_ru") or b1_en
                b2_ru = ov.get("badge2_ru") or b2_en
                render_strava_comparison_vintage_card(
                    out_png_ru,
                    header_text=hdr_ru,
                    subheader_text=sub_ru,
                    badge1_text=b1_ru,
                    badge2_text=b2_ru,
                )
            elif kind == "corner_map":
                pts = get_gpx(ov.get("gpx_file", ""))
                if pts:
                    t_idx = int(ov.get("target_idx", len(pts) // 3))
                    render_corner_map_widget(pts, t_idx, ov.get("scene_label", "Route Progress"), out_png_en, lang="en")
                    render_corner_map_widget(pts, t_idx, ov.get("scene_label_ru", "Маршрут"), out_png_ru, lang="ru")

        item_en = {
            "file": file_en,
            "start_s": float(ov["start_s"]),
            "dur_s": float(ov["dur_s"]),
            "track": ov.get("track", "V2"),
            "fade_in_s": float(ov.get("fade_in_s", 0.25)),
            "fade_out_s": float(ov.get("fade_out_s", 0.30)),
            "desc": ov.get("desc", file_en),
        }
        item_ru = {
            "file": file_ru if (has_ru_text or (overlays_dir / file_ru).exists()) else file_en,
            "start_s": float(ov["start_s"]),
            "dur_s": float(ov["dur_s"]),
            "track": ov.get("track", "V2"),
            "fade_in_s": float(ov.get("fade_in_s", 0.25)),
            "fade_out_s": float(ov.get("fade_out_s", 0.30)),
            "desc": ov.get("desc_ru") or ov.get("desc", file_ru),
        }
        expanded_items_en.append(item_en)
        expanded_items_ru.append(item_ru)

    for item_list in (expanded_items_en, expanded_items_ru):
        v3_subs = [it for it in item_list if it.get("track") == "V3"]
        v3_subs.sort(key=lambda x: x["start_s"])
        for idx in range(len(v3_subs) - 1):
            c1, c2 = v3_subs[idx], v3_subs[idx + 1]
            c1_end = c1["start_s"] + c1["dur_s"]
            if c1_end > c2["start_s"]:
                c1["dur_s"] = round(c2["start_s"] - c1["start_s"], 2)
                c1_end = c1["start_s"] + c1["dur_s"]
            if abs(c1_end - c2["start_s"]) <= 0.08:
                c1["fade_out_s"] = 0.0
                c2["fade_in_s"] = 0.0

        v4_huds = [it for it in item_list if it.get("track") == "V4"]
        v4_huds.sort(key=lambda x: x["start_s"])
        for idx, h_item in enumerate(v4_huds):
            if idx == 0:
                h_item["fade_in_s"] = 0.25
            if idx == len(v4_huds) - 1:
                h_item["fade_out_s"] = 0.30
        for idx in range(len(v4_huds) - 1):
            c1, c2 = v4_huds[idx], v4_huds[idx + 1]
            c1_end = c1["start_s"] + c1["dur_s"]
            if c1_end > c2["start_s"]:
                c1["dur_s"] = round(c2["start_s"] - c1["start_s"], 2)
                c1_end = c1["start_s"] + c1["dur_s"]
            if abs(c1_end - c2["start_s"]) <= 0.15:
                c1["fade_out_s"] = 0.0
                c2["fade_in_s"] = 0.0
            else:
                c1["fade_out_s"] = 0.30
                c2["fade_in_s"] = 0.25

    if edition == "en":
        return expanded_items_en
    elif edition == "ru":
        return expanded_items_ru
    return {"en": expanded_items_en, "ru": expanded_items_ru}
