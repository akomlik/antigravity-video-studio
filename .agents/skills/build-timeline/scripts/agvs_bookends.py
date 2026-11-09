#!/usr/bin/env python3
"""
agvs_bookends.py — AGVS Signature Opening & Closing Bookends Generator
Aesthetic: Warm Vintage Travel (iMovie Travel Pro)

Generates 4K (3840x2160) composited bookend assets with an authentic Mediterranean
parchment aesthetic, strict macOS Apple typography, basemap tiles, and zero emojis:
1. Opening "AGVS Vintage Travel Postcard" (0:00 to 0:03.5):
   - Left Zone (X: 130..1560): Distressed rubber stamp, bold iMovie-style location headline,
     unobstructed vintage cartographic map box with CartoDB Voyager basemap tiles,
     neatline borders, degree ticks, 4-point compass rose, and Start/Summit vector pins.
   - Right Zone (X: 1650..3690): Tilted (-2.0°) Polaroid video frame with "Wish you were here! — AGVS"
     script on bottom margin and faint postmark wave watermark.
   - Bottom Band (Y: 1920..2060): Vintage travel ticket strip (Date • Title • Distance | Elevation).

2. Closing "AGVS Vintage Travel Credits & Bar Tab" (Final 4.5s):
   - Left Zone (X: 130..2020): Tilted (+1.5°) Polaroid video frame with "Another day in paradise — AGVS".
   - Right Zone (X: 2120..3690): High-contrast editorial credits (Cast, Steed lore, Camera,
     Telemetry, AGVS Studio Hero, Fuel/Sponsors).
   - Bottom Strip (Y: 1920..2060): Witty AGVS disclaimer & GitHub repo link.
"""

import argparse
import datetime as dt
import json
import math
import os
import random
import re
import subprocess
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))

# ---------------------------------------------------------------------------
# Color Palette: "Warm Mediterranean Parchment & Postage Ink"
# ---------------------------------------------------------------------------
COLOR_PARCHMENT_CENTER = (242, 236, 225)       # #F2ECE1
COLOR_PARCHMENT_EDGE   = (223, 211, 190)       # #DFD3BE
COLOR_ESPRESSO_INK     = (35, 31, 29, 255)     # #231F1D (Headlines, names, borders)
COLOR_UMBER_INK        = (92, 80, 67, 255)     # #5C5043 (Subtitles, roles, dividers)
COLOR_POSTMARK_CRIMSON = (184, 58, 42, 255)    # #B83A2A (Stamps, route line, accents)
COLOR_FOREST_GREEN     = (45, 106, 79, 255)    # #2D6A4F (Start pin)
COLOR_POLAROID_PAPER   = (252, 249, 242, 255)  # #FCF9F2
COLOR_POLAROID_BORDER  = (216, 207, 192, 255)  # #D8CFC0
COLOR_TICKET_BG        = (230, 219, 200, 255)  # #E6DBC8
COLOR_MAP_LAND         = (239, 230, 213, 255)  # #EFE6D5
COLOR_MAP_WATER        = (202, 216, 216, 255)  # #CAD8D8


# ---------------------------------------------------------------------------
# Strict macOS Apple Font Loader (With TTC Face Indices & Zero Emojis)
# ---------------------------------------------------------------------------
def load_apple_font(role: str, size: int, text: str = "") -> ImageFont.FreeTypeFont:
    """
    Loads native macOS .ttc/.ttf fonts with explicit face indices.
    Bans all unicode emojis in Pillow rendering.
    Ensures Cyrillic font weight parity (Helvetica Neue Bold / Arial Bold)
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
            ("/System/Library/Fonts/SFNSMono.ttf", None),
        ],
        "hero_title": [
            ("/System/Library/Fonts/Avenir Next.ttc", 8),             # Heavy
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 4),      # Condensed ExtraBold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 8),            # Condensed Black
        ],
        "section_header": [
            ("/System/Library/Fonts/Avenir Next.ttc", 0),             # Bold
            ("/System/Library/Fonts/Supplemental/Futura.ttc", 2),      # Bold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 1),            # Bold
        ],
        "body_bold": [
            ("/System/Library/Fonts/Avenir Next.ttc", 2),             # Demi Bold
            ("/System/Library/Fonts/HelveticaNeue.ttc", 6),            # Medium
        ],
        "body_regular": [
            ("/System/Library/Fonts/HelveticaNeue.ttc", 0),            # Regular
            ("/System/Library/Fonts/Avenir Next.ttc", 7),             # Regular
        ],
        "stamp_typewriter": [
            ("/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc", 2),  # Bold
            ("/System/Library/Fonts/SFNSMono.ttf", None),
        ],
        "postcard_script": [
            ("/System/Library/Fonts/Supplemental/Georgia Italic.ttf", None),
            ("/System/Library/Fonts/Supplemental/SnellRoundhand.ttc", 1),       # Bold
            ("/System/Library/Fonts/Supplemental/Bradley Hand.ttf", None),
        ],
    }

    for path, idx in candidates.get(role, candidates["body_regular"]):
        p = Path(path)
        if p.exists():
            try:
                if idx is not None and path.endswith(".ttc"):
                    return ImageFont.truetype(str(p), size=size, index=idx)
                return ImageFont.truetype(str(p), size=size)
            except Exception:
                continue
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# Warm Mediterranean Parchment Canvas Generator
# ---------------------------------------------------------------------------
def create_warm_parchment_canvas(w: int = 3840, h: int = 2160) -> Image.Image:
    """
    Generates a 4K Mediterranean parchment canvas with smooth radial vignette
    and subtle procedural paper grain (0.04s render).
    """
    # 1. Low-resolution radial vignette
    sw, sh = 480, 270
    low_img = Image.new("RGBA", (sw, sh), (*COLOR_PARCHMENT_CENTER, 255))
    d = ImageDraw.Draw(low_img)
    cx, cy = sw / 2.0, sh / 2.0
    max_r = math.hypot(cx, cy)

    for step in range(24, 0, -1):
        r_frac = step / 24.0
        rad = max_r * r_frac
        v = r_frac * r_frac * (3 - 2 * r_frac)  # Smoothstep
        c_r = int(COLOR_PARCHMENT_CENTER[0] * (1 - v) + COLOR_PARCHMENT_EDGE[0] * v)
        c_g = int(COLOR_PARCHMENT_CENTER[1] * (1 - v) + COLOR_PARCHMENT_EDGE[1] * v)
        c_b = int(COLOR_PARCHMENT_CENTER[2] * (1 - v) + COLOR_PARCHMENT_EDGE[2] * v)
        d.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(c_r, c_g, c_b, 255))

    low_img = low_img.filter(ImageFilter.GaussianBlur(20))
    parchment = low_img.resize((w, h), resample=Image.Resampling.BICUBIC)

    # 2. Add subtle paper noise texture
    nw, nh = 960, 540
    noise_img = Image.new("RGBA", (nw, nh), (128, 128, 128, 0))
    noise_draw = ImageDraw.Draw(noise_img)
    rng = random.Random(42)
    # Scatter subtle micro-flecks
    for _ in range(12000):
        nx = rng.randint(0, nw - 1)
        ny = rng.randint(0, nh - 1)
        val = rng.randint(0, 1)
        clr = (92, 80, 67, 18) if val == 0 else (255, 255, 255, 22)
        noise_draw.point((nx, ny), fill=clr)

    noise_full = noise_img.resize((w, h), resample=Image.Resampling.BILINEAR)
    return Image.alpha_composite(parchment, noise_full)


# ---------------------------------------------------------------------------
# GPX Parsing & Cartographic Map Engine
# ---------------------------------------------------------------------------
def parse_gpx_points(gpx_path: Path) -> list[tuple[float, float, float]]:
    """Extracts (lat, lon, ele) coordinates from GPX trackpoints."""
    if not gpx_path.exists():
        return []
    try:
        tree = ET.parse(gpx_path)
        root = tree.getroot()
        ns = {"gpx": "http://www.topografix.com/GPX/1/1"}
        pts = []
        for trkpt in root.findall(".//gpx:trkpt", ns):
            lat = float(trkpt.attrib["lat"])
            lon = float(trkpt.attrib["lon"])
            ele_el = trkpt.find("gpx:ele", ns)
            ele = float(ele_el.text) if ele_el is not None else 0.0
            pts.append((lat, lon, ele))
        if not pts:
            for trkpt in root.findall(".//trkpt"):
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
                ele_el = trkpt.find("ele")
                ele = float(ele_el.text) if ele_el is not None else 0.0
                pts.append((lat, lon, ele))
        return pts
    except Exception as e:
        print(f"Note parsing {gpx_path.name}: {e}")
        return []


def latlon_to_tile(lat: float, lon: float, z: int) -> tuple[int, int]:
    lat_rad = math.radians(lat)
    n = 2.0 ** z
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile


def to_mercator_pixels(lat: float, lon: float, z: int) -> tuple[float, float]:
    lat_rad = math.radians(lat)
    n = 2.0 ** z
    x = (lon + 180.0) / 360.0 * n * 256.0
    y = (1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n * 256.0
    return x, y


def fetch_and_render_vintage_basemap(
    pts: list[tuple[float, float, float]],
    map_w: int = 1420,
    map_h: int = 1390,
    margin: float = 0.22,
    cache_dir: Path | None = None,
) -> tuple[Image.Image, list[tuple[float, float]], tuple[float, float], tuple[float, float]]:
    """
    Fetches and stitches CartoDB Voyager basemap tiles covering GPX bounding box + margin.
    Tints with warm vintage parchment tone and overlays graticule grid lines.
    Returns (map_img, projected_route_points, start_px, summit_px).
    """
    if cache_dir is None:
        cache_dir = STUDIO_ROOT / ".cache/map_tiles"
    cache_dir.mkdir(parents=True, exist_ok=True)

    if pts:
        lats = [p[0] for p in pts]
        lons = [p[1] for p in pts]
        min_lat, max_lat = min(lats), max(lats)
        min_lon, max_lon = min(lons), max(lons)
        summit_pt = max(pts, key=lambda p: p[2])
    else:
        # Fallback to Pollença / Tramuntana box
        min_lat, max_lat = 39.75, 39.95
        min_lon, max_lon = 2.80, 3.15
        summit_pt = (39.866, 2.936, 503)

    lat_span = max(max_lat - min_lat, 0.04)
    lon_span = max(max_lon - min_lon, 0.04)
    b_min_lat = min_lat - margin * lat_span
    b_max_lat = max_lat + margin * lat_span
    b_min_lon = min_lon - margin * lon_span
    b_max_lon = max_lon + margin * lon_span

    zoom = 12 if max(lat_span, lon_span) < 0.35 else 11

    # Mercator tile bounds
    tx0, ty0 = latlon_to_tile(b_max_lat, b_min_lon, zoom)
    tx1, ty1 = latlon_to_tile(b_min_lat, b_max_lon, zoom)
    tx0 = max(0, tx0 - 1)
    tx1 = tx1 + 1
    ty0 = max(0, ty0 - 1)
    ty1 = ty1 + 1

    cols = tx1 - tx0 + 1
    rows = ty1 - ty0 + 1

    stitched = Image.new("RGBA", (cols * 256, rows * 256), (*COLOR_MAP_LAND[:3], 255))
    tile_fetched = False

    for ix, x in enumerate(range(tx0, tx1 + 1)):
        for iy, y in enumerate(range(ty0, ty1 + 1)):
            tile_file = cache_dir / f"esri_topo_{zoom}_{x}_{y}.jpg"
            if not tile_file.exists():
                url = f"https://server.arcgisonline.com/ArcGIS/rest/services/World_Topo_Map/MapServer/tile/{zoom}/{y}/{x}"
                req = urllib.request.Request(url, headers={"User-Agent": "AntigravityVideoStudio/2.0"})
                try:
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        tile_file.write_bytes(resp.read())
                except Exception:
                    pass
            if tile_file.exists():
                try:
                    t_img = Image.open(tile_file).convert("RGBA")
                    stitched.paste(t_img, (ix * 256, iy * 256))
                    tile_fetched = True
                except Exception:
                    pass

    # Mercator bounding box in stitched pixel space
    def to_stitch_px(lat, lon):
        px, py = to_mercator_pixels(lat, lon, zoom)
        return px - tx0 * 256.0, py - ty0 * 256.0

    crop_x0, crop_y0 = to_stitch_px(b_max_lat, b_min_lon)
    crop_x1, crop_y1 = to_stitch_px(b_min_lat, b_max_lon)
    cw = crop_x1 - crop_x0
    ch = crop_y1 - crop_y0

    target_aspect = map_w / map_h
    cur_aspect = cw / max(ch, 1.0)
    if cur_aspect > target_aspect:
        new_ch = cw / target_aspect
        diff = new_ch - ch
        crop_y0 -= diff / 2.0
        crop_y1 += diff / 2.0
    else:
        new_cw = ch * target_aspect
        diff = new_cw - cw
        crop_x0 -= diff / 2.0
        crop_x1 += diff / 2.0

    cw = crop_x1 - crop_x0
    ch = crop_y1 - crop_y0

    # Crop and scale basemap
    if tile_fetched:
        crop_box = (int(max(0, crop_x0)), int(max(0, crop_y0)), int(min(stitched.width, crop_x1)), int(min(stitched.height, crop_y1)))
        cropped_map = stitched.crop(crop_box).resize((map_w, map_h), resample=Image.Resampling.BICUBIC)
        # Apply warm vintage parchment grading
        parchment_tint = Image.new("RGB", (map_w, map_h), (244, 236, 222))
        map_rgb = ImageChops.multiply(cropped_map.convert("RGB"), parchment_tint)
        map_img = map_rgb.convert("RGBA")
    else:
        # Offline antique chart fallback
        map_img = Image.new("RGBA", (map_w, map_h), (*COLOR_MAP_LAND[:3], 255))
        d_off = ImageDraw.Draw(map_img)
        # Draw stylized Mediterranean bay
        d_off.polygon([(map_w * 0.55, 0), (map_w, 0), (map_w, map_h * 0.45), (map_w * 0.65, map_h * 0.35)], fill=(*COLOR_MAP_WATER[:3], 255))
        d_off.polygon([(map_w * 0.70, map_h * 0.40), (map_w, map_h * 0.35), (map_w, map_h), (map_w * 0.85, map_h)], fill=(*COLOR_MAP_WATER[:3], 255))

    # Project GPX points to map box coordinates
    projected = []
    for p in pts:
        px, py = to_stitch_px(p[0], p[1])
        mx = (px - crop_x0) / cw * map_w
        my = (py - crop_y0) / ch * map_h
        projected.append((mx, my))

    start_px = projected[0] if projected else (map_w * 0.72, map_h * 0.78)
    summit_raw = to_stitch_px(summit_pt[0], summit_pt[1])
    summit_px = ((summit_raw[0] - crop_x0) / cw * map_w, (summit_raw[1] - crop_y0) / ch * map_h)

    # Overlay subtle lat/lon graticule lines
    d_map = ImageDraw.Draw(map_img)
    font_grat = load_apple_font("body_regular", 18)
    lat_step = 0.05
    start_lat_grid = math.floor(b_min_lat / lat_step) * lat_step
    while start_lat_grid <= b_max_lat:
        _, gy = to_stitch_px(start_lat_grid, b_min_lon)
        g_my = (gy - crop_y0) / ch * map_h
        if 20 <= g_my <= map_h - 20:
            d_map.line([(18, g_my), (map_w - 18, g_my)], fill=(180, 168, 150, 75), width=1)
            d_map.text((24, g_my - 20), f"{start_lat_grid:.2f}° N", font=font_grat, fill=(130, 118, 102, 170))
        start_lat_grid += lat_step

    lon_step = 0.05
    start_lon_grid = math.floor(b_min_lon / lon_step) * lon_step
    while start_lon_grid <= b_max_lon:
        gx, _ = to_stitch_px(b_max_lat, start_lon_grid)
        g_mx = (gx - crop_x0) / cw * map_w
        if 20 <= g_mx <= map_w - 20:
            d_map.line([(g_mx, 18), (g_mx, map_h - 18)], fill=(180, 168, 150, 75), width=1)
            d_map.text((g_mx + 6, map_h - 38), f"{start_lon_grid:.2f}° E", font=font_grat, fill=(130, 118, 102, 170))
        start_lon_grid += lon_step

    return map_img, projected, start_px, summit_px


def draw_cartographic_neatline(draw: ImageDraw.ImageDraw, w: int, h: int):
    """Draws an antique double border with alternating black/cream degree ticks."""
    bw = 8
    tick_len = 24
    # Top and bottom ticks
    for x in range(0, w, tick_len):
        idx = (x // tick_len) % 2
        c = (35, 31, 29, 255) if idx == 0 else (252, 249, 242, 255)
        draw.rectangle([x, 0, min(x + tick_len, w), bw], fill=c)
        draw.rectangle([x, h - bw, min(x + tick_len, w), h], fill=c)
    # Left and right ticks
    for y in range(0, h, tick_len):
        idx = (y // tick_len) % 2
        c = (35, 31, 29, 255) if idx == 0 else (252, 249, 242, 255)
        draw.rectangle([0, y, bw, min(y + tick_len, h)], fill=c)
        draw.rectangle([w - bw, y, w, min(y + tick_len, h)], fill=c)

    # Outer edge line
    draw.rectangle([0, 0, w - 1, h - 1], outline=(35, 31, 29, 255), width=2)
    # Inner neatline
    draw.rectangle([14, 14, w - 15, h - 15], outline=(92, 80, 67, 255), width=2)


def draw_compass_rose(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 42):
    """Draws a minimal 4-point vintage cartographic compass rose with an elegant N pointer."""
    # North point
    draw.polygon([(cx, cy - r), (cx + 9, cy - 8), (cx, cy)], fill=(184, 58, 42, 255))
    draw.polygon([(cx, cy - r), (cx - 9, cy - 8), (cx, cy)], fill=(92, 80, 67, 255))
    # South point
    draw.polygon([(cx, cy + r), (cx + 9, cy + 8), (cx, cy)], fill=(184, 58, 42, 255))
    draw.polygon([(cx, cy + r), (cx - 9, cy + 8), (cx, cy)], fill=(92, 80, 67, 255))
    # East point
    draw.polygon([(cx + r, cy), (cx + 8, cy + 9), (cx, cy)], fill=(184, 58, 42, 255))
    draw.polygon([(cx + r, cy), (cx + 8, cy - 9), (cx, cy)], fill=(92, 80, 67, 255))
    # West point
    draw.polygon([(cx - r, cy), (cx - 8, cy - 9), (cx, cy)], fill=(184, 58, 42, 255))
    draw.polygon([(cx - r, cy), (cx - 8, cy + 9), (cx, cy)], fill=(92, 80, 67, 255))
    # Center pivot
    draw.ellipse([cx - 4, cy - 4, cx + 4, cy + 4], fill=(35, 31, 29, 255))
    # "N" label
    f_n = load_apple_font("body_bold", 22)
    bbox = draw.textbbox((0, 0), "N", font=f_n)
    nw = bbox[2] - bbox[0]
    draw.text((cx - nw // 2, cy - r - 26), "N", font=f_n, fill=(184, 58, 42, 255))


def draw_postmark_watermark(draw: ImageDraw.ImageDraw, cx: int, cy: int):
    """Draws a faint circular postmark cancellation watermark with wavy lines."""
    crimson_faint = (184, 58, 42, 90)
    # Double ring
    draw.ellipse([cx - 46, cy - 46, cx + 46, cy + 46], outline=crimson_faint, width=3)
    draw.ellipse([cx - 38, cy - 38, cx + 38, cy + 38], outline=crimson_faint, width=1)
    f_stamp = load_apple_font("stamp_typewriter", 13)
    draw.text((cx - 28, cy - 14), "MALLORCA", font=f_stamp, fill=crimson_faint)
    draw.text((cx - 22, cy + 2), "AGVS '26", font=f_stamp, fill=crimson_faint)
    # Wavy cancellation lines extending to the left
    for offset_y in [-18, 0, 18]:
        pts = []
        for x in range(cx - 210, cx - 46):
            y = cy + offset_y + int(4.5 * math.sin(x * 0.14))
            pts.append((x, y))
        draw.line(pts, fill=crimson_faint, width=2)


# ---------------------------------------------------------------------------
# Project Storyboard Metadata Extraction
# ---------------------------------------------------------------------------
def extract_project_bookends_spec(project_dir: Path) -> dict:
    """Extracts all required metadata and tuning knobs from Storyboard.md."""
    spec = {
        "enabled": True,
        "intro_duration_s": 3.5,
        "outro_duration_s": 4.5,
        "studio_motto": "Gravity Reduction Module: FAILED (Climbing Anyway)",
        "location_badge": "MALLORCA // BONAIRE ➔ COLL DE FEMENIA & MORTITX",
        "place_name": "MALLORCA",
        "route_subtitle": "BONAIRE  ➔  COLL DE FEMENIA & MORTITX",
        "cast_credits": [
            "Mark — Mecánico Campeón & 60th Birthday Honoree",
            "Bruce & Lisa — Thursday Ride Ghosts (Plan B Instigators)",
            "Uphill Trail Runners — The 146 bpm Sprint Catalysts",
            "Nina — Bodega del Sol First-Night Dinner Partner",
        ],
        "steed_credit": 'Mint Trek Madone 7 (Personal build on 2016 Craigslist frame · Stationed on island as "Mallorca Bike" since June 2022)',
        "main_hero": "Antigravity Video Studio (AGVS v2.0)",
        "github_repo": "github.com/akomlik/antigravity-video-studio",
        "fuel_sponsors": "Pro Cycle Cafe VIP Card • Antonio's Bodega del Sol • 0x Alcohol",
        "date_str": "2026-11-05",
        "short_title": "SOLO COLL DE FEMENIA ON ZERO-T",
        "distance_mi": 35.2,
        "elevation_ft": 1650,
        "gpx_file": None,
    }

    storyboard_path = project_dir / "Storyboard.md"
    manifest_path = project_dir / "project_manifest.json"

    # GPX resolution
    if manifest_path.exists():
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            if m.get("gpx_file"):
                cand = project_dir / m["gpx_file"]
                if not cand.exists():
                    raw_folder = m.get("raw_media_folder", "")
                    cand = Path("~/Movies").expanduser() / raw_folder / m["gpx_file"]
                if cand.exists():
                    spec["gpx_file"] = cand
        except Exception:
            pass

    if not spec["gpx_file"]:
        gpxs = list(project_dir.glob("*.gpx"))
        if not gpxs:
            raw_cand = Path("~/Movies/2026").expanduser() / project_dir.name
            if raw_cand.exists():
                gpxs = list(raw_cand.glob("*.gpx"))
        if gpxs:
            spec["gpx_file"] = gpxs[0]

    # Storyboard parsing
    if storyboard_path.exists():
        text = storyboard_path.read_text(encoding="utf-8")
        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", project_dir.name)
        if m_date:
            spec["date_str"] = m_date.group(1)

        m_title = re.search(r"\*\s*\*\*Primary.*?\*\*:?\s*`?([^`\n]+)`?", text)
        if m_title:
            raw_t = m_title.group(1).strip()
            cleaned_t = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[·•-]\s*", "", raw_t)
            if " · " in cleaned_t:
                cleaned_t = cleaned_t.split(" · ")[-1].strip()
            spec["short_title"] = cleaned_t.upper()

        m_dist = re.search(r"([\d.]+)\s*mi\b", text, re.IGNORECASE)
        if m_dist:
            spec["distance_mi"] = float(m_dist.group(1))
        m_ele = re.search(r"([\d,]+)\s*ft\s*ascent", text, re.IGNORECASE)
        if m_ele:
            spec["elevation_ft"] = int(m_ele.group(1).replace(",", ""))

        if spec["elevation_ft"] >= 1500:
            spec["studio_motto"] = "Gravity Reduction Module: FAILED (Climbing Anyway)"
        elif spec["distance_mi"] <= 25:
            spec["studio_motto"] = "Powered by Espresso, Pastries & 0.2s FFmpeg Remux"
        else:
            spec["studio_motto"] = "No Riders Were Dropped in the Making of This Film (Mostly)"

        if "agvs_bookends:" in text:
            try:
                m_block = re.search(r"agvs_bookends:\s*\n((?:\s+.*\n)+)", text)
                if m_block:
                    block_lines = m_block.group(1).splitlines()
                    for bl in block_lines:
                        bl = bl.strip()
                        if bl.startswith("enabled:"):
                            spec["enabled"] = "true" in bl.lower()
                        elif bl.startswith("intro_duration_s:"):
                            spec["intro_duration_s"] = float(bl.split(":")[1].strip())
                        elif bl.startswith("outro_duration_s:"):
                            spec["outro_duration_s"] = float(bl.split(":")[1].strip())
                        elif bl.startswith("studio_motto:"):
                            spec["studio_motto"] = bl.split(":", 1)[1].strip().strip("\"'")
                        elif bl.startswith("location_badge:"):
                            spec["location_badge"] = bl.split(":", 1)[1].strip().strip("\"'")
                        elif bl.startswith("place_name:"):
                            spec["place_name"] = bl.split(":", 1)[1].strip().strip("\"'")
                        elif bl.startswith("route_subtitle:"):
                            spec["route_subtitle"] = bl.split(":", 1)[1].strip().strip("\"'")
                        elif bl.startswith("steed_credit:"):
                            val = bl.split(":", 1)[1].strip()
                            if (val.startswith("'") and val.endswith("'")) or (val.startswith('"') and val.endswith('"')):
                                val = val[1:-1]
                            spec["steed_credit"] = val.replace('\\"', '"')
                        elif bl.startswith("main_hero:"):
                            spec["main_hero"] = bl.split(":", 1)[1].strip().strip("\"'")
                        elif bl.startswith("github_repo:"):
                            spec["github_repo"] = bl.split(":", 1)[1].strip().strip("\"'")
                        elif bl.startswith("fuel_sponsors:"):
                            spec["fuel_sponsors"] = bl.split(":", 1)[1].strip().strip("\"'")
            except Exception as e:
                print(f"Note parsing agvs_bookends block: {e}")

    # Derived place name and route subtitle if not explicit
    if "location_badge" in spec and " ➔ " in spec["location_badge"]:
        parts = spec["location_badge"].split(" ➔ ")
        if "//" in parts[0]:
            subparts = parts[0].split("//")
            spec["place_name"] = subparts[0].strip()
            spec["route_subtitle"] = f"{subparts[1].strip()}  ➔  {parts[1].strip()}"

    return spec


# ---------------------------------------------------------------------------
# Canvas Generator 1: Opening "AGVS Vintage Travel Postcard" (0:00 to 0:03.5)
# ---------------------------------------------------------------------------
def render_intro_canvas_4k(spec: dict, out_png: Path) -> Path:
    """
    Renders the split-stage 4K Opening Postcard Canvas (X: 130..1560 left zone,
    X: 1650..3690 right tilted Polaroid zone).
    """
    w, h = 3840, 2160
    canvas = create_warm_parchment_canvas(w, h)

    # 1. Pre-render Realistic Soft Drop Shadow for Right Polaroid Zone (rotated -2.0°)
    # Polaroid dimensions: 1864 x 1184, center: cx=2670, cy=1025
    pw, ph = 1864, 1184
    shadow_card = Image.new("RGBA", (pw, ph), (35, 31, 29, 130))
    shadow_card_rot = shadow_card.rotate(-2.0, resample=Image.Resampling.BICUBIC, expand=True)
    sw, sh = shadow_card_rot.size
    sx = int(2670 - sw / 2 + 18)
    sy = int(1025 - sh / 2 + 24)

    shadow_mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_mask.paste(shadow_card_rot, (sx, sy), shadow_card_rot)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(36))
    canvas = Image.alpha_composite(canvas, shadow_mask)

    draw = ImageDraw.Draw(canvas)

    # 2. Left Zone: Top Vintage Distressed Rubber Stamp (X: 130, Y: 110)
    f_stamp = load_apple_font("stamp_typewriter", 38)
    f_motto = load_apple_font("card_subtitle", 36, text=spec.get("studio_motto", ""))

    stamp_w, stamp_h = 1120, 144
    stamp_img = Image.new("RGBA", (stamp_w, stamp_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(stamp_img)
    sd.rounded_rectangle([2, 2, stamp_w - 3, stamp_h - 3], radius=6, outline=COLOR_POSTMARK_CRIMSON, width=4)
    sd.rounded_rectangle([8, 8, stamp_w - 9, stamp_h - 9], radius=4, outline=COLOR_POSTMARK_CRIMSON, width=2)
    sd.text((28, 18), "AGVS // ANTIGRAVITY VIDEO STUDIO", font=f_stamp, fill=COLOR_POSTMARK_CRIMSON)
    sd.text((30, 78), spec.get("studio_motto", "").upper(), font=f_motto, fill=COLOR_ESPRESSO_INK)

    stamp_rot = stamp_img.rotate(-1.5, resample=Image.Resampling.BICUBIC, expand=True)
    canvas.paste(stamp_rot, (130, 95), stamp_rot)

    # 3. Left Zone: iMovie-Style Location Headline (X: 130, Y: 250)
    place_name = spec.get("place_name", "MALLORCA").upper()
    route_sub = spec.get("route_subtitle", "BONAIRE -> COLL DE FEMENIA & MORTITX").upper()
    f_hero = load_apple_font("hero_title", 96, text=place_name)
    f_sub = load_apple_font("section_header", 34, text=route_sub)

    draw.text((130, 240), place_name, font=f_hero, fill=COLOR_ESPRESSO_INK)

    # Clean subtitle with vector arrow (guaranteed zero missing-glyph boxes)
    arrow_seps = [" ➔ ", " -> ", " → ", " -- ", " - "]
    sep_used = None
    for s in arrow_seps:
        if s in route_sub:
            sep_used = s
            break

    if sep_used:
        p1, p2 = route_sub.split(sep_used, 1)
        p1, p2 = p1.strip(), p2.strip()
        b1 = draw.textbbox((134, 362), p1, font=f_sub)
        draw.text((134, 362), p1, font=f_sub, fill=COLOR_POSTMARK_CRIMSON)
        ax = b1[2] + 16
        ay = 362 + (b1[3] - b1[1]) // 2
        draw.line([(ax, ay), (ax + 24, ay)], fill=COLOR_POSTMARK_CRIMSON, width=4)
        draw.polygon([(ax + 20, ay - 6), (ax + 30, ay), (ax + 20, ay + 6)], fill=COLOR_POSTMARK_CRIMSON)
        draw.text((ax + 44, 362), p2, font=f_sub, fill=COLOR_POSTMARK_CRIMSON)
    else:
        clean_sub = route_sub.replace("➔", "->").replace("→", "->")
        draw.text((134, 362), clean_sub, font=f_sub, fill=COLOR_POSTMARK_CRIMSON)

    # 4. Left Zone: Framed Cartographic Basemap Box (X: 130..1550, Y: 440..1830)
    map_box_x = 130
    map_box_y = 440
    map_w = 1420
    map_h = 1390

    gpx_path = spec.get("gpx_file")
    pts = parse_gpx_points(gpx_path) if gpx_path else []
    basemap_img, projected_pts, start_px, summit_px = fetch_and_render_vintage_basemap(pts, map_w, map_h)

    # Draw GPX route trace on basemap image
    b_draw = ImageDraw.Draw(basemap_img)
    if len(projected_pts) >= 2:
        # 12px cream casing
        b_draw.line(projected_pts, fill=(252, 249, 242, 240), width=12, joint="curve")
        # 6px postmark crimson inner line
        b_draw.line(projected_pts, fill=COLOR_POSTMARK_CRIMSON, width=6, joint="curve")

    # Start Pin (Forest Green with 20px radius)
    spx, spy = int(start_px[0]), int(start_px[1])
    b_draw.ellipse([spx - 20, spy - 20, spx + 20, spy + 20], fill=COLOR_FOREST_GREEN, outline=(252, 249, 242, 255), width=4)
    b_draw.ellipse([spx - 7, spy - 7, spx + 7, spy + 7], fill=(252, 249, 242, 255))
    # Start pill label (48pt Avenir Next Bold)
    st_label = "СТАРТ: БОНАЙРЕ" if spec.get("lang") == "ru" else "START: BONAIRE"
    f_pill = load_apple_font("section_header", 48, text=st_label)
    s_bbox = b_draw.textbbox((0, 0), st_label, font=f_pill)
    sw = s_bbox[2] - s_bbox[0] + 36
    sh = s_bbox[3] - s_bbox[1] + 24
    slx = min(map_w - sw - 20, max(20, spx - sw // 2))
    sly = min(map_h - sh - 20, max(20, spy - 48 - sh))
    b_draw.rounded_rectangle([slx, sly, slx + sw, sly + sh], radius=12, fill=COLOR_POLAROID_PAPER, outline=COLOR_POSTMARK_CRIMSON, width=3)
    b_draw.text((slx + 18, sly + 12), st_label, font=f_pill, fill=COLOR_ESPRESSO_INK)

    # Summit Pin (Postmark Crimson with 20px radius)
    sum_px = int(summit_px[0]), int(summit_px[1])
    b_draw.ellipse([sum_px[0] - 20, sum_px[1] - 20, sum_px[0] + 20, sum_px[1] + 20], fill=COLOR_POSTMARK_CRIMSON, outline=(252, 249, 242, 255), width=4)
    b_draw.ellipse([sum_px[0] - 7, sum_px[1] - 7, sum_px[0] + 7, sum_px[1] + 7], fill=(252, 249, 242, 255))
    # Summit pill label (48pt Avenir Next Bold)
    sum_label = "РАЗВОРОТ: МОРТИЧ" if spec.get("lang") == "ru" else "TURNAROUND: MORTITX"
    f_pill_sum = load_apple_font("section_header", 48, text=sum_label)
    sm_bbox = b_draw.textbbox((0, 0), sum_label, font=f_pill_sum)
    smw = sm_bbox[2] - sm_bbox[0] + 36
    smh = sm_bbox[3] - sm_bbox[1] + 24
    smlx = min(map_w - smw - 20, max(20, sum_px[0] - smw // 2))
    smly = min(map_h - smh - 20, max(20, sum_px[1] + 32))
    b_draw.rounded_rectangle([smlx, smly, smlx + smw, smly + smh], radius=12, fill=COLOR_POLAROID_PAPER, outline=COLOR_POSTMARK_CRIMSON, width=3)
    b_draw.text((smlx + 18, smly + 12), sum_label, font=f_pill_sum, fill=COLOR_ESPRESSO_INK)

    # Compass rose in top-right of map box
    draw_compass_rose(b_draw, cx=map_w - 75, cy=85, r=42)

    # Cartographic neatline border
    draw_cartographic_neatline(b_draw, map_w, map_h)

    # Paste framed map onto canvas with a subtle drop shadow
    map_shadow = Image.new("RGBA", (map_w + 32, map_h + 32), (0, 0, 0, 0))
    ms_draw = ImageDraw.Draw(map_shadow)
    ms_draw.rectangle([16, 16, map_w + 16, map_h + 16], fill=(35, 31, 29, 90))
    map_shadow = map_shadow.filter(ImageFilter.GaussianBlur(16))
    canvas.paste(map_shadow, (map_box_x - 8, map_box_y - 8), map_shadow)
    canvas.paste(basemap_img, (map_box_x, map_box_y))

    # 5. Bottom Travel Ticket Strip (Y: 1920 to 2060, X: 130 to 3690)
    tx0, ty0 = 130, 1920
    tx1, ty1 = 3690, 2060
    draw.rectangle([tx0, ty0, tx1, ty1], fill=COLOR_TICKET_BG)
    draw.line([(tx0, ty0), (tx1, ty0)], fill=COLOR_UMBER_INK, width=3)
    draw.line([(tx0, ty1), (tx1, ty1)], fill=COLOR_UMBER_INK, width=3)

    if spec.get("lang") == "ru":
        dist_km = round(spec.get('distance_mi', 35.2) * 1.60934, 1)
        ele_m = int(round(spec.get('elevation_ft', 1650) * 0.3048))
        ticket_str = f"ДАТА: {spec.get('date_str', '2026-11-05')}     •     {spec.get('short_title', 'ОДИНОЧНЫЙ КОЛЬ ДЕ ФЕМЕНИЯ НА ZERO-T')}     •     {dist_km} КМ  |  {ele_m} М ПОДЪЕМ"
    else:
        dist_val = f"{spec.get('distance_mi', 35.2):.1f}"
        ele_val = f"{spec.get('elevation_ft', 1650):,}"
        ticket_str = f"DATE: {spec.get('date_str', '2026-11-05')}     •     {spec.get('short_title', 'SOLO COLL DE FEMENIA ON ZERO-T')}     •     {dist_val} MI  |  {ele_val} FT CLIMBING"

    f_ticket = load_apple_font("stamp_typewriter", 46, text=ticket_str)
    t_bbox = draw.textbbox((0, 0), ticket_str, font=f_ticket)
    tw = t_bbox[2] - t_bbox[0]
    tx_pos = tx0 + (tx1 - tx0 - tw) // 2
    ty_pos = ty0 + (ty1 - ty0 - (t_bbox[3] - t_bbox[1])) // 2 - 2
    draw.text((tx_pos, ty_pos), ticket_str, font=f_ticket, fill=COLOR_ESPRESSO_INK)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    print(f"Generated 4K Opening Bookend Canvas -> {out_png}")
    return out_png


# ---------------------------------------------------------------------------
# Canvas Generator 2: Closing "AGVS Vintage Travel Credits & Bar Tab"
# ---------------------------------------------------------------------------
def render_outro_canvas_4k(spec: dict, out_png: Path) -> Path:
    """
    Renders the 4K Closing Bookend Canvas with Warm Mediterranean Parchment,
    pre-rendered soft drop shadow for the left Polaroid frame, and high-contrast
    editorial credits card on the right.
    """
    w, h = 3840, 2160
    canvas = create_warm_parchment_canvas(w, h)

    # 1. Pre-render Realistic Soft Drop Shadow for Left Polaroid (rotated +1.5°)
    # Left Polaroid: 1664 x 1072, center: cx=1075, cy=1030
    pw, ph = 1664, 1072
    shadow_card = Image.new("RGBA", (pw, ph), (35, 31, 29, 130))
    shadow_card_rot = shadow_card.rotate(1.5, resample=Image.Resampling.BICUBIC, expand=True)
    sw, sh = shadow_card_rot.size
    sx = int(1075 - sw / 2 + 18)
    sy = int(1030 - sh / 2 + 24)

    shadow_mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shadow_mask.paste(shadow_card_rot, (sx, sy), shadow_card_rot)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(36))
    canvas = Image.alpha_composite(canvas, shadow_mask)

    draw = ImageDraw.Draw(canvas)

    # 2. Right Zone: Big Scannable Editorial Credits (X: 2120 to 3690, Y: 180 to 1840)
    rx0, ry0 = 2120, 180
    rw, rh = 1570, 1660
    rx1, ry1 = rx0 + rw, ry0 + rh

    # Inset credits container with subtle paper border
    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=14, fill=COLOR_POLAROID_PAPER, outline=COLOR_POLAROID_BORDER, width=2)

    # Header (62pt Heavy, 36pt Bold)
    f_h1 = load_apple_font("hero_title", 62)
    f_h2 = load_apple_font("section_header", 36)
    draw.text((rx0 + 56, ry0 + 44), "CREATED BY ALEXANDER KOMLIK", font=f_h1, fill=COLOR_ESPRESSO_INK)
    draw.text((rx0 + 58, ry0 + 124), "AN ANTIGRAVITY VIDEO STUDIO PRODUCTION", font=f_h2, fill=COLOR_POSTMARK_CRIMSON)

    # Contact Pill Badge (38pt stamp_mono)
    f_contact = load_apple_font("stamp_mono", 38)
    contact_str = "@akomlik   •   github.com/akomlik/antigravity-video-studio"
    cb = draw.textbbox((0, 0), contact_str, font=f_contact)
    cw = cb[2] - cb[0]
    px0 = rx0 + 56
    py0 = ry0 + 184
    px1 = rx1 - 56
    py1 = py0 + 64
    draw.rounded_rectangle([px0, py0, px1, py1], radius=12, fill=COLOR_TICKET_BG, outline=COLOR_UMBER_INK, width=2)
    draw.text((px0 + (px1 - px0 - cw) // 2, py0 + 12), contact_str, font=f_contact, fill=COLOR_ESPRESSO_INK)

    # Horizontal divider rule with centered diamond ornament
    div_y = py1 + 28
    draw.line([(rx0 + 48, div_y), (rx1 - 48, div_y)], fill=COLOR_UMBER_INK, width=3)
    dcx = (rx0 + rx1) // 2
    draw.polygon([(dcx, div_y - 8), (dcx + 8, div_y), (dcx, div_y + 8), (dcx - 8, div_y)], fill=COLOR_POSTMARK_CRIMSON)

    is_ru = spec.get("lang") == "ru"
    cast_title = "АКТЕРЫ И ВДОХНОВЕНИЕ" if is_ru else "THE PELOTON & CAST"
    steed_title = "ТЕХНИКА И ТЕЛЕМЕТРИЯ" if is_ru else "MACHINERY & TELEMETRY"
    fuel_title = "ПИТАНИЕ И ЭНЕРГИЯ" if is_ru else "FUEL & CATERING"

    f_cat = load_apple_font("section_header", 52, text=cast_title + steed_title + fuel_title)
    f_item = load_apple_font("body_bold", 50, text=spec.get("steed_credit", "") + (spec.get("cast_credits", [""])[0]))

    def draw_wrapped_line(x: int, y: int, text: str, font, fill, max_w: int = rw - 130, line_h: int = 58) -> int:
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            cand = f"{cur} {w}".strip() if cur else w
            bb = font.getbbox(cand)
            if bb[2] - bb[0] <= max_w:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = f"  {w}"
        if cur:
            lines.append(cur)
        for l in lines:
            draw.text((x, y), l, font=font, fill=fill)
            y += line_h
        return y

    cur_y = div_y + 36

    # 1. THE PELOTON & CAST
    draw.text((rx0 + 56, cur_y), cast_title, font=f_cat, fill=COLOR_POSTMARK_CRIMSON)
    cur_y += 62
    for c in spec.get("cast_credits", [])[:4]:
        cur_y = draw_wrapped_line(rx0 + 76, cur_y, f"• {c}", f_item, COLOR_ESPRESSO_INK, line_h=58)
    cur_y += 32

    # 2. MACHINERY & TELEMETRY
    draw.text((rx0 + 56, cur_y), steed_title, font=f_cat, fill=COLOR_POSTMARK_CRIMSON)
    cur_y += 62
    steed_str = f"• {spec.get('steed_credit')}"
    cur_y = draw_wrapped_line(rx0 + 76, cur_y, steed_str, f_item, COLOR_ESPRESSO_INK, line_h=58)
    tech_line1 = "• Очки BleeqUP Ranger AI (100% живые повороты головы) • iPhone 15 Pro" if is_ru else "• BleeqUP Ranger AI Glasses (100% Organic Head-Turns) • iPhone 15 Pro"
    tech_line2 = "• Garmin Edge 840 • my_digital_brain.md • AGVS Engine v2.0" if is_ru else "• Garmin Edge 840 • my_digital_brain.md • AGVS Engine v2.0"
    cur_y = draw_wrapped_line(rx0 + 76, cur_y, tech_line1, f_item, COLOR_ESPRESSO_INK, line_h=58)
    cur_y = draw_wrapped_line(rx0 + 76, cur_y, tech_line2, f_item, COLOR_ESPRESSO_INK, line_h=58)
    cur_y += 32

    # 3. FUEL & CATERING
    draw.text((rx0 + 56, cur_y), fuel_title, font=f_cat, fill=COLOR_POSTMARK_CRIMSON)
    cur_y += 62
    cur_y = draw_wrapped_line(rx0 + 76, cur_y, f"• {spec.get('fuel_sponsors')}", f_item, COLOR_ESPRESSO_INK, line_h=58)

    # 3. Bottom Stamp Strip (Y: 1920 to 2060, X: 130 to 3690)
    tx0, ty0 = 130, 1920
    tx1, ty1 = 3690, 2060
    draw.rectangle([tx0, ty0, tx1, ty1], fill=COLOR_TICKET_BG)
    draw.line([(tx0, ty0), (tx1, ty0)], fill=COLOR_UMBER_INK, width=3)
    draw.line([(tx0, ty1), (tx1, ty1)], fill=COLOR_UMBER_INK, width=3)

    foot_line1 = "0% ГРАВИТАЦИИ ТОЛЬКО НА СПУСКАХ   •   НИ ОДНА КВОТА ARGON НЕ ПОСТРАДАЛА" if is_ru else "0% GRAVITY GUARANTEED ON DESCENTS ONLY   •   NO ARGON QUOTAS WERE HARMED"
    repo_url = spec.get("github_repo", "github.com/akomlik/antigravity-video-studio")
    foot_line2 = f"СТУДИЙНЫЙ ДВИЖОК AGVS   •   {repo_url.upper()}" if is_ru else f"AGVS STUDIO ENGINE   •   {repo_url.upper()}"

    f_strip = load_apple_font("stamp_mono", 40, text=foot_line1 + foot_line2)
    fb1 = draw.textbbox((0, 0), foot_line1, font=f_strip)
    tw1 = fb1[2] - fb1[0]
    draw.text((tx0 + (tx1 - tx0 - tw1) // 2, ty0 + 26), foot_line1, font=f_strip, fill=COLOR_ESPRESSO_INK)

    fb2 = draw.textbbox((0, 0), foot_line2, font=f_strip)
    tw2 = fb2[2] - fb2[0]
    draw.text((tx0 + (tx1 - tx0 - tw2) // 2, ty0 + 78), foot_line2, font=f_strip, fill=COLOR_POSTMARK_CRIMSON)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    print(f"Generated 4K Closing Bookend Canvas -> {out_png}")
    return out_png


# ---------------------------------------------------------------------------
# Polaroid Video Frame Overlay Generator
# ---------------------------------------------------------------------------
def render_polaroid_border_png(
    width: int,
    height: int,
    video_w: int,
    video_h: int,
    margin_top: int = 32,
    margin_side: int = 32,
    margin_bottom: int = 140,
    script_text: str | None = None,
    out_png: Path | None = None,
) -> Path:
    """
    Creates a warm Polaroid paper frame with transparent center for video,
    script caption on bottom margin, and faint postmark wave watermark.
    """
    img = Image.new("RGBA", (width, height), COLOR_POLAROID_PAPER)
    d = ImageDraw.Draw(img)

    # 2px outer paper edge
    d.rectangle([0, 0, width - 1, height - 1], outline=COLOR_POLAROID_BORDER, width=2)

    # Cut out the inner video window
    d.rectangle([margin_side, margin_top, margin_side + video_w, margin_top + video_h], fill=(0, 0, 0, 0))

    # Bottom margin script text (52pt)
    if script_text:
        f_script = load_apple_font("postcard_script", 52)
        bbox = d.textbbox((0, 0), script_text, font=f_script)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = margin_side + 40
        ty = height - margin_bottom + (margin_bottom - th) // 2 - 6
        d.text((tx, ty), script_text, font=f_script, fill=COLOR_ESPRESSO_INK)

    # Postmark cancellation wave watermark in right corner of bottom chin
    cx = width - margin_side - 80
    cy = height - margin_bottom // 2
    draw_postmark_watermark(d, cx, cy)

    if out_png:
        out_png.parent.mkdir(parents=True, exist_ok=True)
        img.save(out_png)
    return out_png


# ---------------------------------------------------------------------------
# Video Compositing Engine (FFmpeg)
# ---------------------------------------------------------------------------
def composite_intro_bookend_mp4(
    canvas_png: Path,
    first_clip_path: Path,
    out_mp4: Path,
    duration_s: float = 3.5,
    clip_start_s: float = 0.0,
) -> Path:
    """
    Composites opening 3.5s of first clip inside a -2.0° tilted Polaroid frame
    over the 4K canvas in Right Zone (X: 1650..3690).
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    vw, vh = 1800, 1012
    margin_top = 32
    margin_side = 32
    margin_bottom = 140
    pw = vw + margin_side * 2   # 1864
    ph = vh + margin_top + margin_bottom  # 1184

    is_ru = "_RU" in out_mp4.name or "_ru" in out_mp4.name
    border_png = out_mp4.parent / ("polaroid_intro_border_ru.png" if is_ru else "polaroid_intro_border.png")
    script_txt = '«Жаль, что вас здесь нет! — AGVS»' if is_ru else '"Wish you were here! — AGVS"'
    render_polaroid_border_png(
        width=pw,
        height=ph,
        video_w=vw,
        video_h=vh,
        margin_top=margin_top,
        margin_side=margin_side,
        margin_bottom=margin_bottom,
        script_text=script_txt,
        out_png=border_png,
    )

    # Position in Right Zone: center is cx=2670, cy=1025
    pos_x = int(2670 - pw / 2)  # 1738
    pos_y = int(1025 - ph / 2)  # 433

    filtergraph = (
        f"[1:v]trim=start={clip_start_s}:duration={duration_s},setpts=PTS-STARTPTS,"
        f"scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},"
        f"pad={pw}:{ph}:{margin_side}:{margin_top}:color=0x00000000[v_padded];"
        f"[v_padded][2:v]overlay=0:0:format=auto[card];"
        f"[card]rotate=-2.0*PI/180:c=none:ow=rotw(-2.0*PI/180):oh=roth(-2.0*PI/180):bilinear=1[card_rot];"
        f"[0:v][card_rot]overlay={pos_x}:{pos_y}:format=auto[v_out];"
        f"[1:a]atrim=start={clip_start_s}:duration={duration_s},asetpts=PTS-STARTPTS,volume=0.0dB[a_out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration_s), "-i", str(canvas_png),
        "-ss", str(clip_start_s), "-t", str(duration_s), "-i", str(first_clip_path),
        "-i", str(border_png),
        "-filter_complex", filtergraph,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-c:v", "h264_videotoolbox",
        "-b:v", "38M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_mp4)
    ]

    print(f"Rendering Opening Postcard Bookend ({duration_s}s) -> {out_mp4.name}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Hardware encoding failed, falling back to libx264: {res.stderr[-200:]}")
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration_s), "-i", str(canvas_png),
            "-ss", str(clip_start_s), "-t", str(duration_s), "-i", str(first_clip_path),
            "-i", str(border_png),
            "-filter_complex", filtergraph,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_mp4)
        ]
        res = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg compositing failed: {res.stderr[-400:]}")

    print(f"Opening Bookend Video ready: {out_mp4} ({round(out_mp4.stat().st_size / 1024 / 1024, 1)} MB)")
    return out_mp4


def composite_outro_bookend_mp4(
    canvas_png: Path,
    last_clip_path: Path,
    out_mp4: Path,
    duration_s: float = 4.5,
    clip_start_s: float = 0.0,
) -> Path:
    """
    Composites final 4.5s of timeline inside a +1.5° tilted Polaroid frame
    over the 4K canvas in Left Zone (X: 130..2020).
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    vw, vh = 1600, 900
    margin_top = 32
    margin_side = 32
    margin_bottom = 140
    pw = vw + margin_side * 2   # 1664
    ph = vh + margin_top + margin_bottom  # 1072

    is_ru = "_RU" in out_mp4.name or "_ru" in out_mp4.name
    border_png = out_mp4.parent / ("polaroid_outro_border_ru.png" if is_ru else "polaroid_outro_border.png")
    script_txt = '«Еще один день в раю — AGVS»' if is_ru else '"Another day in paradise — AGVS"'
    render_polaroid_border_png(
        width=pw,
        height=ph,
        video_w=vw,
        video_h=vh,
        margin_top=margin_top,
        margin_side=margin_side,
        margin_bottom=margin_bottom,
        script_text=script_txt,
        out_png=border_png,
    )

    # Position in Left Zone: center is cx=1075, cy=1030
    pos_x = int(1075 - pw / 2)  # 243
    pos_y = int(1030 - ph / 2)  # 494

    filtergraph = (
        f"[1:v]trim=start={clip_start_s}:duration={duration_s},setpts=PTS-STARTPTS,"
        f"scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},"
        f"pad={pw}:{ph}:{margin_side}:{margin_top}:color=0x00000000[v_padded];"
        f"[v_padded][2:v]overlay=0:0:format=auto[card];"
        f"[card]rotate=1.5*PI/180:c=none:ow=rotw(1.5*PI/180):oh=roth(1.5*PI/180):bilinear=1[card_rot];"
        f"[0:v][card_rot]overlay={pos_x}:{pos_y}:format=auto[v_out];"
        f"[1:a]atrim=start={clip_start_s}:duration={duration_s},asetpts=PTS-STARTPTS,volume=0.0dB[a_out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-t", str(duration_s), "-i", str(canvas_png),
        "-ss", str(clip_start_s), "-t", str(duration_s), "-i", str(last_clip_path),
        "-i", str(border_png),
        "-filter_complex", filtergraph,
        "-map", "[v_out]",
        "-map", "[a_out]",
        "-c:v", "h264_videotoolbox",
        "-b:v", "38M",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(out_mp4)
    ]

    print(f"Rendering Closing Credits Bookend ({duration_s}s) -> {out_mp4.name}...")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Hardware encoding failed, falling back to libx264: {res.stderr[-200:]}")
        cmd_fallback = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", str(duration_s), "-i", str(canvas_png),
            "-ss", str(clip_start_s), "-t", str(duration_s), "-i", str(last_clip_path),
            "-i", str(border_png),
            "-filter_complex", filtergraph,
            "-map", "[v_out]",
            "-map", "[a_out]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            str(out_mp4)
        ]
        res = subprocess.run(cmd_fallback, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg compositing failed: {res.stderr[-400:]}")

    print(f"Closing Bookend Video ready: {out_mp4} ({round(out_mp4.stat().st_size / 1024 / 1024, 1)} MB)")
    return out_mp4


# ---------------------------------------------------------------------------
# High-Level Studio Pipeline Integration
# ---------------------------------------------------------------------------
def generate_project_bookends(
    project_dir: Path,
    out_dir: Path | None = None,
    first_clip: Path | None = None,
    last_clip: Path | None = None,
) -> tuple[Path, Path]:
    """Generates both 4K bookend video clips for a project."""
    project_dir = Path(project_dir).expanduser().resolve()
    if out_dir is None:
        out_dir = project_dir / "overlays"
    out_dir.mkdir(parents=True, exist_ok=True)

    spec = extract_project_bookends_spec(project_dir)

    # 1. Render Canvases (EN)
    intro_canvas = out_dir / "bookend_intro_canvas_4K.png"
    outro_canvas = out_dir / "bookend_outro_canvas_4K.png"

    render_intro_canvas_4k(spec, intro_canvas)
    render_outro_canvas_4k(spec, outro_canvas)

    # 1b. Render Canvases (RU)
    spec_ru = dict(spec)
    spec_ru["lang"] = "ru"
    spec_ru["place_name"] = spec.get("place_name_ru", "МАЛЬОРКА")
    spec_ru["route_subtitle"] = spec.get("route_subtitle_ru", "БОНАЙРЕ ➔ КОЛЬ ДЕ ФЕМЕНИЯ И МОРТИЧ")
    spec_ru["studio_motto"] = spec.get("studio_motto_ru", "МОДУЛЬ СНИЖЕНИЯ ГРАВИТАЦИИ: ОТКАЗ (ВСЁ РАВНО ЕДЕМ)")
    spec_ru["short_title"] = spec.get("short_title_ru", "ОДИНОЧНЫЙ КОЛЬ ДЕ ФЕМЕНИЯ НА ZERO-T")
    spec_ru["cast_credits"] = spec.get("cast_credits_ru", [
        "Марк — Mecánico Campeón и юбиляр 60-летия PCH",
        "Брюс и Лиза — Призраки четверга (вдохновители плана Б)",
        "Бегуны в гору — Катализаторы пульса 146 уд/мин",
        "Нина — Партнер по ужину в Bodega del Sol",
    ])
    spec_ru["steed_credit"] = spec.get("steed_credit_ru", "Trek Madone 7 (Сборка на раме с Craigslist 2016 · На острове с июня 2022)")
    spec_ru["fuel_sponsors"] = spec.get("fuel_sponsors_ru", "Вода с солями из Pollença • Bodega del Sol • 0x Алкоголь")
    intro_canvas_ru = out_dir / "bookend_intro_canvas_4K_RU.png"
    outro_canvas_ru = out_dir / "bookend_outro_canvas_4K_RU.png"
    render_intro_canvas_4k(spec_ru, intro_canvas_ru)
    render_outro_canvas_4k(spec_ru, outro_canvas_ru)

    # 2. Locate Source Clips
    intro_clip = None
    manifest_p = project_dir / "project_manifest.json"
    raw_dir = None
    if manifest_p.exists():
        try:
            m = json.loads(manifest_p.read_text(encoding="utf-8"))
            raw_folder = m.get("raw_media_folder", "")
            if raw_folder:
                raw_dir = Path("~/Movies").expanduser() / raw_folder
        except Exception:
            pass
    if raw_dir is None or not raw_dir.exists():
        raw_dir = Path("~/Movies/2026").expanduser() / project_dir.name
        if not raw_dir.exists():
            raw_dir = project_dir

    # First video clip for opening
    if first_clip and Path(first_clip).exists():
        intro_clip = Path(first_clip)
    else:
        for cand_name in ("VIDEO_1793866633305.MP4", "VIDEO_1793867334082.MP4", "IMG_8782.MOV"):
            cand = raw_dir / cand_name
            if cand.exists():
                intro_clip = cand
                break
    if not intro_clip:
        vids = sorted(list(raw_dir.glob("*.MP4")) + list(raw_dir.glob("*.MOV")))
        if vids:
            intro_clip = vids[0]
        else:
            raise FileNotFoundError(f"No video files found in {raw_dir}")

    # Last video clip for finale
    outro_clip = None
    if last_clip and Path(last_clip).exists():
        lc = Path(last_clip)
        if lc.suffix.lower() in (".mov", ".mp4", ".m4v"):
            outro_clip = lc
        else:
            print(f"Notice: last_clip {lc.name} is a still photo; searching for contiguous video outro clip...")

    if not outro_clip:
        for cand_name in ("IMG_8801_rotated.MOV", "IMG_8801.MOV", "IMG_8796.MOV", "VIDEO_1793873573670.MP4"):
            cand = raw_dir / cand_name
            if cand.exists():
                outro_clip = cand
                break
    if not outro_clip:
        outro_clip = intro_clip

    # 3. Composite Video Bookends (EN)
    intro_mp4 = out_dir / "bookend_intro_4K.mp4"
    outro_mp4 = out_dir / "bookend_outro_4K.mp4"

    composite_intro_bookend_mp4(
        canvas_png=intro_canvas,
        first_clip_path=intro_clip,
        out_mp4=intro_mp4,
        duration_s=spec.get("intro_duration_s", 3.5),
        clip_start_s=0.0,
    )

    composite_outro_bookend_mp4(
        canvas_png=outro_canvas,
        last_clip_path=outro_clip,
        out_mp4=outro_mp4,
        duration_s=spec.get("outro_duration_s", 4.5),
        clip_start_s=2.0,
    )

    # 3b. Composite Video Bookends (RU)
    intro_mp4_ru = out_dir / "bookend_intro_4K_RU.mp4"
    outro_mp4_ru = out_dir / "bookend_outro_4K_RU.mp4"

    composite_intro_bookend_mp4(
        canvas_png=intro_canvas_ru,
        first_clip_path=intro_clip,
        out_mp4=intro_mp4_ru,
        duration_s=spec.get("intro_duration_s", 3.5),
        clip_start_s=0.0,
    )

    composite_outro_bookend_mp4(
        canvas_png=outro_canvas_ru,
        last_clip_path=outro_clip,
        out_mp4=outro_mp4_ru,
        duration_s=spec.get("outro_duration_s", 4.5),
        clip_start_s=2.0,
    )

    return intro_mp4, outro_mp4


def main():
    parser = argparse.ArgumentParser(description="Generate signature AGVS bookends (Warm Vintage Travel)")
    parser.add_argument("project_dir", type=str, nargs="?", default=None, help="Path to project directory")
    parser.add_argument("--project-dir", dest="project_dir_opt", type=str, default=None, help="Path to project directory")
    parser.add_argument("--out-dir", type=str, default=None, help="Output overlays directory")
    parser.add_argument("--first-clip", type=str, default=None, help="First video clip for opening")
    parser.add_argument("--last-clip", type=str, default=None, help="Last video clip for outro")
    args = parser.parse_args()

    pdir_str = args.project_dir_opt or args.project_dir
    if not pdir_str:
        parser.error("project_dir is required")

    pdir = Path(pdir_str).expanduser().resolve()
    outd = Path(args.out_dir).expanduser().resolve() if args.out_dir else None
    first_c = Path(args.first_clip).expanduser().resolve() if args.first_clip else None
    last_c = Path(args.last_clip).expanduser().resolve() if args.last_clip else None

    intro_mp4, outro_mp4 = generate_project_bookends(pdir, outd, first_clip=first_c, last_clip=last_c)
    print("\n✅ AGVS Bookends successfully generated:")
    print(f"  Intro: {intro_mp4}")
    print(f"  Outro: {outro_mp4}")


if __name__ == "__main__":
    main()
