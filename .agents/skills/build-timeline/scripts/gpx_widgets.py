#!/usr/bin/env python3
"""
gpx_widgets.py
Generates 4K UHD (3840x2160) transparent PNG overlays directly from a Garmin/Strava .gpx file:
1. Corner Route Map Widget (top-right card showing the full route loop, progress trail up to the clip's
   exact UTC timestamp, glowing current-location pin, and Imperial mile/elevation header).
2. Dynamic Telemetry HUD Overlay (bottom-left or bottom-right telemetry gauges for Speed MPH, Power W,
   Heart Rate BPM, and Gradient % / Elevation FT, synced 1-to-1 with each video clip's UTC timestamp
   and dynamically triggered only when interesting telemetry thresholds are exceeded).
"""

import datetime as dt
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont


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


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/SFNSMono.ttf",
        "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf" if bold else "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/HelveticaNeue.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for c in candidates:
        if Path(c).exists():
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_corner_map_widget(
    gpx_points: list[dict],
    target_idx: int,
    scene_label: str,
    out_png: Path,
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """
    Renders a 4K transparent overlay PNG with a sleek top-right GPX Route Map card
    showing the full loop, progress trail up to target_idx, and glowing current pin.
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Card geometry (top-right corner with 72px margin)
    card_w, card_h = 680, 520
    x0 = w - card_w - 72
    y0 = 72
    x1, y1 = x0 + card_w, y0 + card_h

    # Subtle drop shadow + frosted dark glass card
    draw.rounded_rectangle([x0 - 4, y0 + 6, x1 + 4, y1 + 10], radius=32, fill=(0, 0, 0, 110))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=28, fill=(14, 19, 28, 215), outline=(255, 255, 255, 55), width=2)

    # Header bar inside card
    pt = gpx_points[min(max(target_idx, 0), len(gpx_points) - 1)]
    tot_mi = gpx_points[-1]["dist_mi"] if gpx_points else 0.0
    font_hdr = _load_font(26, bold=True)
    font_sub = _load_font(22, bold=False)

    hdr_text = f"MILE {pt['dist_mi']:.1f} / {tot_mi:.1f} MI  ·  {pt['ele_ft']} FT"
    draw.text((x0 + 30, y0 + 22), hdr_text, font=font_hdr, fill=(255, 138, 43, 255))
    draw.text((x0 + 30, y0 + 56), scene_label[:36], font=font_sub, fill=(230, 236, 245, 235))
    draw.line([(x0 + 24, y0 + 94), (x1 - 24, y0 + 94)], fill=(255, 255, 255, 35), width=2)

    # Compute lat/lon bounding box with cosine latitude aspect correction
    lats = [p["lat"] for p in gpx_points]
    lons = [p["lon"] for p in gpx_points]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    cos_lat = math.cos(math.radians((min_lat + max_lat) / 2.0))

    dx = max((max_lon - min_lon) * cos_lat, 1e-5)
    dy = max(max_lat - min_lat, 1e-5)

    pad_x, pad_y = 46, 36
    map_x0, map_y0 = x0 + pad_x, y0 + 108 + pad_y
    map_w = card_w - 2 * pad_x
    map_h = (card_h - 108) - 2 * pad_y

    scale = min(map_w / dx, map_h / dy)
    ox = map_x0 + (map_w - dx * scale) / 2.0
    oy = map_y0 + (map_h - dy * scale) / 2.0

    def to_xy(lat: float, lon: float) -> tuple[float, float]:
        px = ox + (lon - min_lon) * cos_lat * scale
        py = oy + (max_lat - lat) * scale
        return (px, py)

    # Full route loop in muted slate-blue
    full_xy = [to_xy(p["lat"], p["lon"]) for p in gpx_points[::3]]
    if len(full_xy) >= 2:
        draw.line(full_xy, fill=(130, 150, 175, 115), width=6, joint="curve")

    # Completed progress trail in vibrant Strava/Garmin orange
    done_xy = [to_xy(p["lat"], p["lon"]) for p in gpx_points[: max(target_idx + 1, 2) : 2]]
    if len(done_xy) >= 2:
        draw.line(done_xy, fill=(255, 105, 30, 245), width=9, joint="curve")

    # Start marker (green dot)
    sx, sy = to_xy(gpx_points[0]["lat"], gpx_points[0]["lon"])
    draw.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], fill=(46, 213, 115, 230), outline=(255, 255, 255, 220), width=2)

    # Current scene location pin (glowing outer ring + white/red center)
    cx, cy = to_xy(pt["lat"], pt["lon"])
    draw.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], fill=(255, 90, 30, 75))
    draw.ellipse([cx - 13, cy - 13, cx + 13, cy + 13], fill=(255, 71, 43, 255), outline=(255, 255, 255, 255), width=4)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return out_png


def render_telemetry_hud_widget(
    pt: dict,
    out_png: Path,
    highlight_reason: str = "",
    canvas_size: tuple[int, int] = (3840, 2160),
) -> Path:
    """
    Renders a 4K transparent overlay PNG with a sleek bottom-left Telemetry HUD
    showing Speed (MPH), Power (W), Heart Rate (BPM), and Gradient (%) in Imperial units.
    """
    w, h = canvas_size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img, "RGBA")

    # Top-left telemetry bar (balances top-right map widget and never collides with bottom subtitles/YouTube UI)
    hud_w, hud_h = 980, 190
    x0 = 72
    y0 = 72
    x1, y1 = x0 + hud_w, y0 + hud_h

    draw.rounded_rectangle([x0 - 4, y0 + 6, x1 + 4, y1 + 10], radius=28, fill=(0, 0, 0, 110))
    draw.rounded_rectangle([x0, y0, x1, y1], radius=24, fill=(14, 19, 28, 215), outline=(255, 255, 255, 55), width=2)

    font_val = _load_font(64, bold=True)
    font_unit = _load_font(22, bold=True)
    font_lbl = _load_font(20, bold=False)

    metrics = [
        ("SPEED", f"{pt['spd_mph']:.1f}", "MPH", (64, 210, 255, 255)),
        ("POWER", f"{pt['pwr']}", "WATTS", (255, 184, 28, 255)),
        ("HEART RATE", f"{pt['hr']}", "BPM ♥", (255, 92, 112, 255)),
        ("GRADE", f"{pt['grad_pct']:+.1f}%", f"{pt['ele_ft']} FT", (85, 239, 196, 255)),
    ]

    col_w = hud_w // 4
    for idx, (label, val, unit, accent_col) in enumerate(metrics):
        cx = x0 + idx * col_w + 30
        if idx > 0:
            draw.line([(x0 + idx * col_w, y0 + 26), (x0 + idx * col_w, y1 - 26)], fill=(255, 255, 255, 35), width=2)
        draw.text((cx, y0 + 20), label, font=font_lbl, fill=(170, 182, 200, 230))
        draw.text((cx, y0 + 50), val, font=font_val, fill=(255, 255, 255, 255))
        draw.text((cx, y0 + 132), unit, font=font_unit, fill=accent_col)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, "PNG")
    return out_png


def should_show_telemetry_hud(
    clip_name: str,
    gpx_points: list[dict] = None,
    clip_ts: dt.datetime | None = None,
    rolling_speed_mph: float | None = None,
    window_s: float = 3.0,
    speed_threshold_mph: float = 2.0,
) -> bool:
    """
    Evaluates whether the Telemetry HUD should be visible on a clip (Studio v2.1 standard):
    - Automatically False (OFF) for still photo clips (.jpg, .jpeg, .png, .heic).
    - Automatically False (OFF) for stationary scenes (speed <= 2.0 mph: cafe, counter, terrace, gates).
    - Automatically True (ON) for actual moving scenes (riding, running, hiking, moving camera: speed > 2.0 mph).
    """
    # 1. Stills are always suppressed
    if clip_name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
        return False

    # 2. If rolling speed is directly provided
    if rolling_speed_mph is not None:
        return rolling_speed_mph > speed_threshold_mph

    # 3. If GPX stream and timestamp are provided, calculate rolling speed over window
    if gpx_points and clip_ts is not None:
        pts_in_win = [p for p in gpx_points if abs((p["time"] - clip_ts).total_seconds()) <= window_s]
        if pts_in_win:
            avg_spd = sum(p["spd_mph"] for p in pts_in_win) / len(pts_in_win)
            return avg_spd > speed_threshold_mph

    return False
