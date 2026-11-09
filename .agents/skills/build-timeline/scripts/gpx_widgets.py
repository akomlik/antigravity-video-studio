#!/usr/bin/env python3
"""
gpx_widgets.py
Generates 4K UHD (3840x2160) transparent PNG overlays directly from a Garmin/Strava .gpx file:
1. Corner Route Map Widget (top-right card showing the full route loop, progress trail up to the clip's
   exact UTC timestamp, glowing current-location pin, and Imperial mile/elevation header).
2. Dynamic Telemetry HUD Overlay (top-left or bottom-left telemetry gauges for Speed MPH, Power W,
   Heart Rate BPM, and Gradient % / Elevation FT, synced 1-to-1 with each video clip's UTC timestamp).
3. AGVS Vintage Field Cards: Warm Vintage Parchment callouts and lower-thirds with strict macOS Apple typography
   and iPhone 15 Pro (6.1" display) font scaling.
"""

import datetime as dt
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


# ---------------------------------------------------------------------------
# Color Palette: Warm Mediterranean Parchment & Postage Ink
# ---------------------------------------------------------------------------
COLOR_PARCHMENT_FILL  = (244, 239, 230, 242)  # rgba(244, 239, 230, 0.95) (#F4EFE6)
COLOR_ESPRESSO_INK    = (35, 31, 29, 255)      # #231F1D (Primary titles, names, metrics)
COLOR_UMBER_INK       = (74, 63, 53, 255)      # #4A3F35 (Roles, subtitles, labels)
COLOR_BORDER_UMBER    = (92, 80, 67, 255)      # #5C5043 (Outer 3px border)
COLOR_NEATLINE        = (216, 207, 192, 255)  # #D8CFC0 (Inner 1px neatline)
COLOR_CRIMSON         = (184, 58, 42, 255)     # #B83A2A (Accent stripe, highlights)
COLOR_FOREST_GREEN    = (45, 106, 79, 255)     # #2D6A4F (Start pin, normal metrics)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def load_gpx_stream(gpx_path: Path) -> list[dict]:
    """Parses a .gpx file into a smoothed 1Hz telemetry stream with Imperial & metric units."""
    root = ET.parse(gpx_path).getroot()
    pts = []
    tot_m = 0.0

    for trkpt in root.iter():
        if not trkpt.tag.endswith("trkpt"):
            continue
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        ele, ts, hr, cad, pwr = 0.0, None, 0, 0, 0
        for c in trkpt.iter():
            tag = c.tag.split("}")[-1]
            if tag == "ele" and c.text:
                ele = float(c.text)
            elif tag == "time" and c.text:
                ts = dt.datetime.fromisoformat(c.text.replace("Z", "+00:00"))
            elif tag == "hr" and c.text:
                hr = int(float(c.text))
            elif tag == "cad" and c.text:
                cad = int(float(c.text))
            elif tag in ("power", "watts") and c.text:
                pwr = int(float(c.text))
        if ts is None:
            continue

        spd_mph = 0.0
        grad_pct = 0.0
        if pts:
            prev = pts[-1]
            d = haversine_m(prev["lat"], prev["lon"], lat, lon)
            dts = max((ts - prev["time"]).total_seconds(), 0.001)
            spd_mph = (d / dts) * 2.236936
            tot_m += d
            # Compute smoothed gradient over ~15m window
            back_idx = max(0, len(pts) - 5)
            d_win = haversine_m(pts[back_idx]["lat"], pts[back_idx]["lon"], lat, lon)
            if d_win > 5.0:
                grad_pct = ((ele - pts[back_idx]["ele"]) / d_win) * 100.0

        pts.append({
            "time": ts,
            "lat": lat,
            "lon": lon,
            "ele": ele,
            "ele_ft": int(round(ele * 3.28084)),
            "dist_mi": round(tot_m / 1609.344, 2),
            "spd_mph": round(min(spd_mph, 58.0), 1),
            "grad_pct": round(max(-25.0, min(25.0, grad_pct)), 1),
            "hr": hr,
            "cad": cad,
            "pwr": pwr,
        })
    return pts


# ---------------------------------------------------------------------------
# Strict macOS Apple Font Loader (Zero Monospace, Zero Emojis)
# ---------------------------------------------------------------------------
def load_apple_font(role: str, size: int, text: str = "") -> ImageFont.FreeTypeFont:
    """
    Loads native macOS .ttc/.ttf fonts with explicit face indices for Pillow rendering.
    Enforces bold Apple editorial typography and bans all unicode emojis.
    Automatically ensures Cyrillic font weight parity (Helvetica Neue Bold / Arial Bold)
    when Cyrillic characters are detected.
    """
    # Cyrillic Font Weight Parity
    if text and re.search(r"[\u0400-\u04FF]", text):
        cyrillic_candidates = [
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

    candidates = {
        "card_title": [
            ("/System/Library/Fonts/Avenir Next.ttc", 8),             # Heavy
            ("/System/Library/Fonts/Avenir Next.ttc", 0),             # Bold
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),      # Condensed ExtraBold
        ],
        "card_subtitle": [
            ("/System/Library/Fonts/Avenir Next.ttc", 2),             # Demi Bold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 6),            # Medium
        ],
        "stamp_mono": [
            ("/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc", 2),  # Bold
            ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf", None),
        ],
        "postcard_script": [
            ("/System/Library/Fonts/Supplemental/Georgia Italic.ttf", None),
            ("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc", 1),       # Bold
        ],
        "hero_title": [
            ("/System/Library/Fonts/Avenir Next.ttc", 8),             # Heavy
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),
        ],
        "section_header": [
            ("/System/Library/Fonts/Avenir Next.ttc", 0),             # Bold
        ],
        "body_regular": [
            ("/System/Library/Fonts/HelveticaNeue.ttc", 0),            # Regular
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
    """Backwards-compatible wrapper routing to strict Apple font faces."""
    role = "card_title" if bold else "card_subtitle"
    return load_apple_font(role, size, text=text)


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
    """
    Renders the unified Warm Vintage Parchment card on `canvas` with:
    - Soft 28px Gaussian blur drop shadow rgba(25, 20, 16, 0.38) offset (+6px, +10px).
    - Card fill: Warm aged parchment rgba(244, 239, 230, 0.95) (#F4EFE6).
    - Outer border: 3px solid Umber Ink #5C5043 (radius=18).
    - Inner neatline: 1px inset border #D8CFC0 (8px inside outer border).
    - Accent stripe: 20px solid Crimson #B83A2A on left edge (or 16px on top edge).
    """
    x0, y0, x1, y1 = box
    cw = max(10, x1 - x0)
    ch = max(10, y1 - y0)

    # 1. Fast local drop shadow (Gaussian blur on card-sized sub-image)
    pad = 48
    s_img = Image.new("RGBA", (cw + pad * 2, ch + pad * 2), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(s_img)
    s_draw.rounded_rectangle([pad, pad, pad + cw, pad + ch], radius=radius, fill=(25, 20, 16, 97))
    s_blur = s_img.filter(ImageFilter.GaussianBlur(14))
    canvas.alpha_composite(s_blur, (x0 - pad + 6, y0 - pad + 10))

    # 2. Card base and neatline
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=COLOR_PARCHMENT_FILL, outline=COLOR_BORDER_UMBER, width=3)
    draw.rounded_rectangle([x0 + 8, y0 + 8, x1 - 8, y1 - 8], radius=max(4, radius - 6), outline=COLOR_NEATLINE, width=1)

    # 3. Accent stripe (20px left, 16px top default)
    if accent_side == "left":
        aw = accent_width if accent_width is not None else 20
        draw.rounded_rectangle([x0 + 18, y0 + 16, x0 + 18 + aw, y1 - 16], radius=5, fill=accent_color)
    elif accent_side == "top":
        aw = accent_width if accent_width is not None else 16
        draw.rounded_rectangle([x0 + 24, y0 + 12, x1 - 24, y0 + 12 + aw], radius=5, fill=accent_color)


# ---------------------------------------------------------------------------
# Corner Map Widget
# ---------------------------------------------------------------------------
def render_corner_map_widget(
    gpx_points: list[dict],
    target_idx: int,
    scene_label: str,
    out_png: Path,
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """
    Renders a 4K transparent overlay PNG with a Warm Vintage Parchment GPX Route Map card
    showing the full loop, progress trail up to target_idx, and glowing current pin.
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    card_w, card_h = 760, 560
    x0 = w - card_w - 96
    y0 = 96
    x1, y1 = x0 + card_w, y0 + card_h

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=COLOR_CRIMSON)
    draw = ImageDraw.Draw(img)

    # Header bar inside card
    pt = gpx_points[min(max(target_idx, 0), len(gpx_points) - 1)]
    tot_mi = gpx_points[-1]["dist_mi"] if gpx_points else 0.0
    font_hdr = load_apple_font("card_title", 32)
    font_sub = load_apple_font("card_subtitle", 26)

    hdr_text = f"MILE {pt['dist_mi']:.1f} / {tot_mi:.1f} MI  ·  {pt['ele_ft']} FT"
    draw.text((x0 + 48, y0 + 22), hdr_text, font=font_hdr, fill=COLOR_CRIMSON)
    draw.text((x0 + 48, y0 + 64), scene_label[:38], font=font_sub, fill=COLOR_UMBER_INK)
    draw.line([(x0 + 42, y0 + 106), (x1 - 32, y0 + 106)], fill=COLOR_NEATLINE, width=2)

    # Compute lat/lon bounding box with cosine latitude aspect correction
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

    # Full route loop in muted umber casing
    full_xy = [to_xy(p["lat"], p["lon"]) for p in gpx_points[::3]]
    if len(full_xy) >= 2:
        draw.line(full_xy, fill=(180, 168, 150, 160), width=6, joint="curve")

    # Completed progress trail in vibrant Crimson
    done_xy = [to_xy(p["lat"], p["lon"]) for p in gpx_points[: max(target_idx + 1, 2) : 2]]
    if len(done_xy) >= 2:
        draw.line(done_xy, fill=COLOR_CRIMSON, width=8, joint="curve")

    # Start marker (green dot)
    sx, sy = to_xy(gpx_points[0]["lat"], gpx_points[0]["lon"])
    draw.ellipse([sx - 9, sy - 9, sx + 9, sy + 9], fill=COLOR_FOREST_GREEN, outline=(252, 249, 242, 255), width=2)

    # Current scene location pin
    cx, cy = to_xy(pt["lat"], pt["lon"])
    draw.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=(184, 58, 42, 75))
    draw.ellipse([cx - 14, cy - 14, cx + 14, cy + 14], fill=COLOR_CRIMSON, outline=(252, 249, 242, 255), width=3)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


# ---------------------------------------------------------------------------
# Telemetry HUD Widget (Warm Vintage Parchment & Scaled iPhone 15 Pro 4K Fonts)
# ---------------------------------------------------------------------------
def render_telemetry_hud_widget(
    pt: dict,
    out_png: Path,
    highlight_reason: str = "",
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """
    Renders a 4K transparent overlay PNG with a Warm Vintage Parchment Telemetry HUD
    at top-left (X: 96, Y: 96) showing Speed MPH, Power W, Heart Rate BPM, and Grade % in Imperial units.
    - Values in 72pt Avenir Next Heavy.
    - Units in 32pt Avenir Next Bold.
    - Labels in 26pt Avenir Next Demi Bold.
    - Zero emojis.
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    hud_w, hud_h = 1380, 240
    x0, y0 = 96, 96
    x1, y1 = x0 + hud_w, y0 + hud_h

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=COLOR_CRIMSON)
    draw = ImageDraw.Draw(img)

    font_val = load_apple_font("hero_title", 72)
    font_unit = load_apple_font("section_header", 32)
    font_lbl = load_apple_font("card_subtitle", 26)

    metrics = [
        ("SPEED", f"{pt['spd_mph']:.1f}", "MPH", COLOR_CRIMSON),
        ("POWER", f"{pt['pwr']}", "WATTS", COLOR_CRIMSON),
        ("HEART RATE", f"{pt['hr']}", "BPM", COLOR_CRIMSON),
        ("GRADE", f"{pt['grad_pct']:+.1f}%", f"{pt['ele_ft']} FT", COLOR_FOREST_GREEN),
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
    """Renders a 1 Hz series of 4K transparent Telemetry HUD PNGs."""
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
# Character Callout Badge (Warm Vintage Parchment & iPhone 15 Pro 4K Scaling)
# ---------------------------------------------------------------------------
def render_character_callout_badge(
    name_line: str,
    role_line: str,
    out_png: Path,
    position: str = "bottom_left",
    accent_color: tuple[int, int, int, int] = COLOR_CRIMSON,
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """
    Renders a 4K transparent overlay PNG with a Warm Vintage Parchment Character Card (+40% Mobile Weight):
    - Line 1: 84pt card_title (Avenir Next Bold/Heavy or Helvetica Neue Bold for Cyrillic) in Deep Espresso #231F1D (with @akomlik in Crimson).
    - Line 2: 60pt card_subtitle (Avenir Next Demi Bold) in Warm Umber #4A3F35.
    - Dimensions: Width 2200..2900px, Height 250px (320px if Line 2 wraps).
    - Accent: 20px solid crimson stripe on left edge.
    - Positions:
        'bottom_left': X: 96, Y: 1710 (or Y: 1640 if wrapped)
        'top_left':    X: 96, Y: 96
        'bottom_right': X: w - card_w - 96, Y: 1710
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    # Clean emojis if any crept in
    clean_name = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", name_line).strip()
    clean_role = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", role_line).strip()

    font_name = load_apple_font("card_title", 84, text=clean_name)
    font_role = load_apple_font("card_subtitle", 60, text=clean_role)

    # Measure text dimensions
    dummy = Image.new("RGBA", (100, 100))
    d_measure = ImageDraw.Draw(dummy)

    nb = d_measure.textbbox((0, 0), clean_name, font=font_name)
    rb = d_measure.textbbox((0, 0), clean_role, font=font_role)
    name_w = nb[2] - nb[0]
    role_w = rb[2] - rb[0]

    # Evaluate wrapping for Line 2 if it exceeds comfortable single-line width
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

    # Placement coordinates
    if position == "bottom_right":
        x0 = w - card_w - 96
        y0 = 1640 if is_wrapped else 1710
    elif position == "top_left":
        x0 = 96
        y0 = 96
    else:  # bottom_left
        x0 = 96
        y0 = 1640 if is_wrapped else 1710

    x1, y1 = x0 + card_w, y0 + card_h

    # Render card with 20px accent stripe
    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=20, accent_color=accent_color, accent_width=20)
    draw = ImageDraw.Draw(img)

    # Draw Line 1 with @akomlik highlighted in crimson if present
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

    # Draw Line 2 (one or two wrapped lines)
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
    """
    Renders a prominent retro/archival memory card on Warm Vintage Parchment (+40% Mobile Weight):
    - Bold Date/Event indicator pill in 36pt Avenir Next Bold.
    - Title in 84pt Avenir Next Bold/Heavy (#231F1D).
    - Contextual detail line in 60pt Avenir Next Demi Bold (#4A3F35).
    - Dimensions: Width 2200..2900px, Height 310px.
    - Accent: 20px solid crimson stripe on left edge.
    - Zero emojis.
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    clean_date = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", date_event_line).strip()
    clean_title = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", title_line).strip()
    clean_detail = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", detail_line).strip()

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
    else:  # top_left
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


def render_translation_subtitle_card(
    spoken_text: str,
    english_translation: str = None,
    out_png: Path = None,
    canvas_size: tuple[int, int] = (3840, 2160),
    translation_text: str = None,
    card_width: int | None = None,
    card_height: int | None = None,
) -> Path:
    """
    Renders bilingual on-camera speech translations as a centered Vintage Telegram / Field Note Card:
    - Dynamic Language Hierarchy ("Translation Is Always Primary"):
      - Spoken line: 60pt Demi Bold in Postmark Crimson #B83A2A with quotes.
      - Translation line: 76pt Heavy/Bold in Deep Espresso #231F1D (wrapped if needed) with Cyrillic font parity.
      - If spoken is EN: Top line is Spoken EN ("..."), Bottom line is Russian Translation (76pt Bold Espresso).
      - If spoken is RU: Top line is Spoken RU («...»), Bottom line is English Translation (76pt Bold Espresso).
    - Dimensions: Width clamped to 2600..3000px, 16px solid Crimson top accent bar, 42px vertical padding.
    - Centered horizontally at Y: 1710 (or Y: 1640 when wrapped).
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    clean_spoken = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", spoken_text).strip()
    raw_trans = translation_text if translation_text is not None else (english_translation or "")
    clean_trans = re.sub(r"[🚀📍📅🎬🚴⛰️⚠️♥📊]", "", raw_trans).strip()

    # Strip existing quotes from translation so it renders as clean bold editorial text
    if clean_trans.startswith(("«", '"', "“", "'")) and clean_trans.endswith(("»", '"', "”", "'")):
        clean_trans = clean_trans[1:-1].strip()

    # Detect spoken language and apply standard quotation marks
    spoken_is_cyrillic = bool(re.search(r"[\u0400-\u04FF]", clean_spoken))
    if spoken_is_cyrillic:
        if not (clean_spoken.startswith("«") and clean_spoken.endswith("»")):
            clean_spoken = clean_spoken.strip('\'"')
            clean_spoken = f"«{clean_spoken}»"
    else:
        if not (clean_spoken.startswith('"') and clean_spoken.endswith('"')):
            clean_spoken = clean_spoken.strip('\'"«»')
            clean_spoken = f'"{clean_spoken}"'

    # Font styles
    # Top Line: Spoken at 60pt Demi Bold in Crimson
    # Bottom Line: Translation at 76pt Heavy/Bold in Deep Espresso (with Cyrillic font parity)
    f_spoken = load_apple_font("card_subtitle", 60, text=clean_spoken)
    f_trans = load_apple_font("card_title", 76, text=clean_trans)

    dummy = Image.new("RGBA", (100, 100))
    d_measure = ImageDraw.Draw(dummy)

    b1 = d_measure.textbbox((0, 0), clean_spoken, font=f_spoken)
    w1 = b1[2] - b1[0]

    max_card_w = 3000
    min_card_w = 2600
    max_text_w = max_card_w - 180

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

    t1_x = x0 + (card_w - w1) // 2
    draw.text((t1_x, y0 + 42), clean_spoken, font=f_spoken, fill=COLOR_CRIMSON)

    cur_trans_y = y0 + 124
    for line in trans_lines:
        lb = d_measure.textbbox((0, 0), line, font=f_trans)
        lw = lb[2] - lb[0]
        lx = x0 + (card_w - lw) // 2
        draw.text((lx, cur_trans_y), line, font=f_trans, fill=COLOR_ESPRESSO_INK)
        cur_trans_y += 88

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


def render_strava_comparison_vintage_card(
    out_png: Path,
    header_text: str = "STRAVA LONGITUDINAL COMPARISON · COLL DE FEMENIA",
    subheader_text: str = "Same 195W Climbing Effort · Accelerated Aging Tax on Zero Testosterone (ADT)",
    badge1_text: str = "2024 NORMAL-T:  195 W  @  118 BPM",
    badge2_text: str = "2026 ZERO-T:  191 W  @  141 BPM (+23 BPM TAX)",
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """
    Renders a Strava Longitudinal Comparison Card on Warm Vintage Parchment (+40% Mobile Weight):
    - 64pt Avenir Next Bold/Heavy header in #231F1D.
    - 46pt Avenir Next Demi Bold subheader in #4A3F35.
    - Forest Green (#2D6A4F) badge 1 and Postmark Crimson (#B83A2A) badge 2 in 54pt text.
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))

    f_hdr = load_apple_font("hero_title", 64, text=header_text)
    f_sub = load_apple_font("card_subtitle", 46, text=subheader_text)
    f_badge = load_apple_font("section_header", 54, text=badge1_text + badge2_text)

    cw, ch = 2800, 370
    x0, y0 = 96, 96
    x1, y1 = x0 + cw, y0 + ch

    draw_vintage_card(img, (x0, y0, x1, y1), accent_side="left", radius=22, accent_color=COLOR_CRIMSON, accent_width=20)
    draw = ImageDraw.Draw(img)

    draw.text((x0 + 64, y0 + 32), header_text, font=f_hdr, fill=COLOR_ESPRESSO_INK)
    draw.text((x0 + 66, y0 + 112), subheader_text, font=f_sub, fill=COLOR_UMBER_INK)

    dummy = Image.new("RGBA", (100, 100))
    d_m = ImageDraw.Draw(dummy)

    by = y0 + 196
    b_1 = d_m.textbbox((0, 0), badge1_text, font=f_badge)
    bw1 = b_1[2] - b_1[0] + 54
    draw.rounded_rectangle([x0 + 64, by, x0 + 64 + bw1, by + 88], radius=14, fill=COLOR_FOREST_GREEN)
    draw.text((x0 + 91, by + 16), badge1_text, font=f_badge, fill=(252, 249, 242, 255))

    bx2 = x0 + 64 + bw1 + 36
    b_2 = d_m.textbbox((0, 0), badge2_text, font=f_badge)
    bw2 = b_2[2] - b_2[0] + 54
    draw.rounded_rectangle([bx2, by, bx2 + bw2, by + 88], radius=14, fill=COLOR_CRIMSON)
    draw.text((bx2 + 27, by + 16), badge2_text, font=f_badge, fill=(252, 249, 242, 255))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG", compress_level=1)
    return out_png


def render_declarative_overlays(
    overlays_spec: list[dict],
    overlays_dir: Path,
    raw_dir: Path | None = None,
    skip_render: bool = False,
) -> list[dict]:
    """
    Universal declarative overlay renderer and timeline expander.
    Reads `overlays` array from `timeline_spec.json`, renders all 4K RGBA PNGs,
    and expands any `live_telemetry_hud` / `telemetry_hud` entries into 1Hz live-updating
    HUD items on track `V3` (with smooth fade-in on the first second, 100% solid hold
    across internal 1s boundaries so the card never blinks, and fade-out on the last second).
    """
    overlays_dir.mkdir(parents=True, exist_ok=True)
    live_hud_dir = overlays_dir / "live_hud"
    live_hud_dir.mkdir(parents=True, exist_ok=True)

    gpx_cache: dict[str, list[dict]] = {}

    def get_gpx(gpx_name: str) -> list[dict]:
        if not raw_dir or not gpx_name:
            return []
        if gpx_name not in gpx_cache:
            gp = raw_dir / gpx_name
            gpx_cache[gpx_name] = load_gpx_stream(gp) if gp.exists() else []
        return gpx_cache[gpx_name]

    expanded_items: list[dict] = []
    for ov in overlays_spec:
        kind = ov.get("kind", "character_badge")
        accent_name = (ov.get("accent") or "crimson").lower()
        accent_col = COLOR_FOREST_GREEN if "green" in accent_name else COLOR_CRIMSON
        pos = ov.get("position", "bottom_left")

        if kind in ("live_telemetry_hud", "telemetry_hud"):
            start_s = float(ov["start_s"])
            dur_s = float(ov["dur_s"])
            step_s = float(ov.get("step_s", 1.0))
            pts = get_gpx(ov.get("gpx_file", ""))
            gpx_start_idx = int(ov.get("gpx_start_idx", len(pts) // 4 if pts else 0))
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

                rel_fname = f"live_hud/hud_{int(round(tl_s * 10)):04d}.png"
                out_png = overlays_dir / rel_fname
                if not skip_render:
                    render_telemetry_hud_widget(pt, out_png)

                expanded_items.append({
                    "file": rel_fname,
                    "start_s": tl_s,
                    "dur_s": cur_dur,
                    "track": ov.get("track", "V4"),
                    "fade_in_s": 0.25 if s_idx == 0 else 0.0,
                    "fade_out_s": 0.30 if s_idx == n_steps - 1 else 0.0,
                    "desc": ov.get("desc", f"Live Telemetry HUD @ {tl_s:.1f}s"),
                })
            continue

        if kind == "translation_subtitle" and "pages" in ov:
            pages = ov["pages"]
            n_pages = len(pages)
            for p_idx, page in enumerate(pages):
                page_file = page.get("file", f"{ov.get('file_prefix', 'sub')}_{p_idx+1:02d}.png")
                page_start = float(page["start_s"])
                page_dur = float(page["dur_s"])
                page_spoken = page.get("spoken", "")
                page_trans = page.get("translation") or page.get("russian") or page.get("english", "")
                page_png = overlays_dir / page_file
                if not skip_render:
                    render_translation_subtitle_card(
                        spoken_text=page_spoken,
                        translation_text=page_trans,
                        english_translation=page.get("english"),
                        out_png=page_png,
                    )
                expanded_items.append({
                    "file": page_file,
                    "start_s": page_start,
                    "dur_s": page_dur,
                    "track": page.get("track", ov.get("track", "V3")),
                    "fade_in_s": float(page.get("fade_in_s", 0.25 if p_idx == 0 else 0.0)),
                    "fade_out_s": float(page.get("fade_out_s", 0.30 if p_idx == n_pages - 1 else 0.0)),
                    "desc": page.get("desc", f"Bilingual Subtitle Page {p_idx+1}"),
                })
            continue

        out_png = overlays_dir / ov["file"]
        if not skip_render:
            if kind == "character_badge":
                render_character_callout_badge(
                    ov["title"],
                    ov["subtitle"],
                    out_png,
                    position=pos,
                    accent_color=accent_col,
                )
            elif kind == "flashback_badge":
                render_flashback_memory_badge(
                    ov["date_event"],
                    ov["title"],
                    ov["detail"],
                    out_png,
                    position=pos,
                    accent_color=accent_col,
                )
            elif kind == "translation_subtitle":
                trans = ov.get("translation") or ov.get("russian") or ov.get("english", "")
                render_translation_subtitle_card(
                    spoken_text=ov.get("spoken", ""),
                    translation_text=trans,
                    english_translation=ov.get("english"),
                    out_png=out_png,
                )
            elif kind == "strava_comparison":
                render_strava_comparison_vintage_card(
                    out_png,
                    header_text=ov.get("header", "STRAVA LONGITUDINAL COMPARISON · COLL DE FEMENIA"),
                    subheader_text=ov.get("subheader", "Same 195W Climbing Effort · Accelerated Aging Tax on Zero Testosterone (ADT)"),
                    badge1_text=ov.get("badge1", "2024 NORMAL-T:  195 W  @  118 BPM"),
                    badge2_text=ov.get("badge2", "2026 ZERO-T:  191 W  @  141 BPM (+23 BPM TAX)"),
                )
            elif kind == "corner_map":
                pts = get_gpx(ov.get("gpx_file", ""))
                if pts:
                    t_idx = int(ov.get("target_idx", len(pts) // 3))
                    render_corner_map_widget(pts, t_idx, ov.get("scene_label", "Route Progress"), out_png)

        expanded_items.append({
            "file": ov["file"],
            "start_s": float(ov["start_s"]),
            "dur_s": float(ov["dur_s"]),
            "track": ov.get("track", "V3" if kind == "translation_subtitle" else "V2"),
            "fade_in_s": float(ov.get("fade_in_s", 0.25)),
            "fade_out_s": float(ov.get("fade_out_s", 0.30)),
            "desc": ov.get("desc", ov["file"]),
        })

    # Contiguous Subtitle Pass on track V3:
    # If two consecutive subtitle cards on track V3 are contiguous (gap <= 0.08s)
    # or slightly overlapping, clamp the earlier duration so they touch perfectly,
    # and zero out the fade-out on the earlier card and the fade-in on the second card.
    # This guarantees the parchment box holds stationary with no awkward dip to black!
    v3_subs = [it for it in expanded_items if it.get("track") == "V3"]
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

    return expanded_items


ACTIVITY_SPEED_THRESHOLDS = {
    "cycling_ride": 2.0,
    "cycling": 2.0,
    "ride": 2.0,
    "run": 1.5,
    "running": 1.5,
    "hike_outdoor": 0.8,
    "hike": 0.8,
    "hiking": 0.8,
    "walk": 0.8,
    "walking": 0.8,
}


def should_show_telemetry_hud(
    clip_name: str,
    gpx_points: list[dict] = None,
    clip_ts: dt.datetime | None = None,
    rolling_speed_mph: float | None = None,
    activity_type: str = "cycling_ride",
    mode: str = "auto",
    window_s: float = 3.0,
    speed_threshold_mph: float | None = None,
) -> bool:
    """Evaluates whether the Telemetry HUD should be visible on a clip."""
    if clip_name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
        return False

    mode_clean = (mode or "auto").strip().lower()
    if mode_clean == "off":
        return False
    if mode_clean == "always":
        return True

    if speed_threshold_mph is None:
        act_key = (activity_type or "cycling_ride").strip().lower()
        speed_threshold_mph = ACTIVITY_SPEED_THRESHOLDS.get(act_key, 2.0)

    if rolling_speed_mph is not None:
        return rolling_speed_mph > speed_threshold_mph

    if gpx_points and clip_ts is not None:
        pts_in_win = [p for p in gpx_points if abs((p["time"] - clip_ts).total_seconds()) <= window_s]
        if pts_in_win:
            avg_spd = sum(p["spd_mph"] for p in pts_in_win) / len(pts_in_win)
            return avg_spd > speed_threshold_mph

    return False
