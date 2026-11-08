#!/usr/bin/env python3
"""
agvs_bookends.py — AGVS Signature Opening & Closing Bookends Generator

Generates signature 4K (3840x2160) composited bookend assets for Antigravity Video Studio:
1. Opening "AGVS Pre-Flight Postcard":
   - 4K themed topographic canvas (deep-slate route trace from .gpx or blurred hero photo)
   - Distressed aerospace rubber-stamp badge: 🚀 AGVS // ANTIGRAVITY VIDEO STUDIO
   - Dynamic witty tagline based on ride stats / Storyboard motto
   - Bottom ticket-stub manifest bar with Date, Title, Distance & Elevation
   - First 3.5s of opening clip composited inside a -2.0° tilted white postcard frame
     (70% scale, centered-right, with realistic soft drop shadow)
   - Live camera audio on A1 preserved

2. Closing "AGVS Post-Ride Bar Tab & Credits":
   - Final 4.5s of the timeline composited on the left inside a +1.5° tilted white postcard frame
     (58% scale) with "Wish you were here! — AGVS" script on the bottom chin
   - Right side: sleek "AGVS Production Receipt / Credits Card"
     (Created by Alexander Komlik, Crew, Steed, Camera, Telemetry, Memory Bank, Fuel/Sponsors, and witty footer)
   - Live camera audio and A2 music tail preserved
"""

import argparse
import datetime as dt
import json
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))


# ---------------------------------------------------------------------------
# Font Loading Helpers
# ---------------------------------------------------------------------------

def _load_font(family: str, size: int) -> ImageFont.FreeTypeFont:
    """Loads fonts safely with fallbacks."""
    font_paths = {
        "title": [
            "/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf",
            "/System/Library/Fonts/Supplemental/Futura.ttc",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/SFNS.ttf",
        ],
        "mono": [
            "/System/Library/Fonts/SFNSMono.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ],
        "script": [
            "/System/Library/Fonts/Supplemental/SignPainter.ttc",
            "/System/Library/Fonts/Supplemental/Bradley Hand.ttf",
            "/System/Library/Fonts/Supplemental/SnellRoundhand.ttc",
        ],
        "receipt": [
            "/System/Library/Fonts/Supplemental/AmericanTypewriter.ttc",
            "/System/Library/Fonts/SFNSMono.ttf",
            "/System/Library/Fonts/Supplemental/Courier New.ttf",
        ],
        "sans": [
            "/System/Library/Fonts/SFNS.ttf",
            "/System/Library/Fonts/HelveticaNeue.ttc",
            "/System/Library/Fonts/Supplemental/Arial.ttf",
        ],
    }

    candidates = font_paths.get(family, font_paths["sans"])
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


# ---------------------------------------------------------------------------
# GPX Parsing & Canvas Drawing
# ---------------------------------------------------------------------------

def parse_gpx_points(gpx_path: Path) -> list[tuple[float, float]]:
    """Extracts raw (lat, lon) coordinates from a .gpx file."""
    if not gpx_path or not gpx_path.exists():
        return []
    try:
        root = ET.parse(gpx_path).getroot()
        pts = []
        for trkpt in root.iter():
            if trkpt.tag.endswith("trkpt"):
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
                pts.append((lat, lon))
        return pts
    except Exception as e:
        print(f"Warning: Failed to parse GPX {gpx_path}: {e}")
        return []


def draw_gpx_route_on_canvas(
    draw: ImageDraw.ImageDraw,
    pts: list[tuple[float, float]],
    box: tuple[int, int, int, int],  # (x0, y0, x1, y1)
    route_color: tuple[int, int, int, int] = (0, 229, 255, 240),
    glow_color: tuple[int, int, int, int] = (0, 180, 216, 70),
):
    """Plots the GPX route trace onto a designated bounding box on the 4K canvas."""
    if not pts or len(pts) < 2:
        return

    # Downsample points if huge
    step = max(1, len(pts) // 2500)
    sampled = pts[::step]

    lats = [p[0] for p in sampled]
    lons = [p[1] for p in sampled]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)

    span_lat = max(max_lat - min_lat, 1e-6)
    span_lon = max(max_lon - min_lon, 1e-6)

    bx0, by0, bx1, by1 = box
    bw = bx1 - bx0
    bh = by1 - by0

    # Fit aspect ratio
    # 1 deg lat ~= 111 km, 1 deg lon ~= 111 * cos(lat) km
    mid_lat = (min_lat + max_lat) / 2.0
    lon_scale = math.cos(math.radians(mid_lat))
    geo_w = span_lon * lon_scale
    geo_h = span_lat

    scale = min(bw / geo_w, bh / geo_h)
    draw_w = geo_w * scale
    draw_h = geo_h * scale

    off_x = bx0 + (bw - draw_w) / 2.0
    off_y = by0 + (bh - draw_h) / 2.0

    canvas_pts = []
    for lat, lon in sampled:
        x = off_x + ((lon - min_lon) * lon_scale) * scale
        y = off_y + (max_lat - lat) * scale  # Invert lat for canvas Y
        canvas_pts.append((x, y))

    # 1. Subtle wide glow
    for width, alpha in [(16, 25), (10, 50), (6, 120)]:
        gc = (glow_color[0], glow_color[1], glow_color[2], alpha)
        for i in range(len(canvas_pts) - 1):
            draw.line([canvas_pts[i], canvas_pts[i + 1]], fill=gc, width=width)

    # 2. Crisp main route line
    for i in range(len(canvas_pts) - 1):
        draw.line([canvas_pts[i], canvas_pts[i + 1]], fill=route_color, width=4)

    # 3. Waypoint Pins: Start & Peak / Summit
    if canvas_pts:
        # Start Pin
        sx, sy = canvas_pts[0]
        draw.ellipse([sx - 14, sy - 14, sx + 14, sy + 14], fill=(255, 61, 0, 90))
        draw.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], fill=(255, 61, 0, 255), outline=(255, 255, 255, 255), width=2)
        font_pin = _load_font("mono", 24)
        draw.text((sx + 16, sy - 14), "📍 START", font=font_pin, fill=(255, 87, 34, 255))

        # Peak / Turnaround Pin (highest elevation / westernmost mountain peak)
        # Find westernmost or northernmost point as peak
        min_x_idx = min(range(len(canvas_pts)), key=lambda i: canvas_pts[i][0])
        px, py = canvas_pts[min_x_idx]
        draw.ellipse([px - 14, py - 14, px + 14, py + 14], fill=(0, 229, 255, 90))
        draw.ellipse([px - 8, py - 8, px + 8, py + 8], fill=(0, 229, 255, 255), outline=(255, 255, 255, 255), width=2)
        draw.text((px + 16, py - 14), "⛰️ SUMMIT", font=font_pin, fill=(0, 229, 255, 255))


# ---------------------------------------------------------------------------
# Storyboard Metadata Extraction
# ---------------------------------------------------------------------------

def extract_project_bookends_spec(project_dir: Path) -> dict:
    """Extracts all required metadata and bookend tuning knobs from Storyboard.md & project_manifest.json."""
    spec = {
        "enabled": True,
        "intro_duration_s": 3.5,
        "outro_duration_s": 4.5,
        "studio_motto": "Gravity Reduction Module: FAILED (Climbing Anyway)",
        "location_badge": "MALLORCA // BONAIRE ➔ COLL DE FEMENIA",
        "cast_credits": [
            "Mark — Mecánico Campeón & 60th Birthday Honoree",
            "Bruce & Lisa — Thursday Ride Ghosts (Plan B Instigators)",
            "Uphill Trail Runners — The 146 bpm Sprint Catalysts",
            "Nina — Bodega del Sol First-Night Dinner Partner",
        ],
        "steed_credit": "Mint Trek Madone 7 (Personal Build · Used Craigslist Frame, Class of '16)",
        "main_hero": "Antigravity Video Studio (AGVS v2.0)",
        "github_repo": "github.com/akomlik/antigravity-video-studio",
        "fuel_sponsors": "Pro Cycle Cafe VIP Card • Antonio's Bodega del Sol • 0x Alcohol",
        "date_str": "2026-11-05",
        "short_title": "Solo Coll de Femenia on Zero-T",
        "distance_mi": 35.2,
        "elevation_ft": 1650,
        "gpx_file": None,
        "hero_image": None,
    }

    storyboard_path = project_dir / "Storyboard.md"
    manifest_path = project_dir / "project_manifest.json"

    # 1. Project Manifest
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

    # Search for GPX if not set
    if not spec["gpx_file"]:
        gpxs = list(project_dir.glob("*.gpx"))
        if not gpxs:
            # Check raw media folder in Movies
            raw_cand = Path("~/Movies/2026").expanduser() / project_dir.name
            if raw_cand.exists():
                gpxs = list(raw_cand.glob("*.gpx"))
        if gpxs:
            spec["gpx_file"] = gpxs[0]

    # 2. Storyboard Parsing
    if storyboard_path.exists():
        text = storyboard_path.read_text(encoding="utf-8")

        # Parse date from project name or header
        m_date = re.search(r"(\d{4}-\d{2}-\d{2})", project_dir.name)
        if m_date:
            spec["date_str"] = m_date.group(1)

        # Parse Primary Title
        m_title = re.search(r"\*\s*\*\*Primary.*?\*\*:?\s*`?([^`\n]+)`?", text)
        if m_title:
            raw_t = m_title.group(1).strip()
            # Clean short title: remove YYYY-MM-DD prefix and uppercase noise
            cleaned_t = re.sub(r"^\d{4}-\d{2}-\d{2}\s*[·•-]\s*", "", raw_t)
            if " · " in cleaned_t:
                cleaned_t = cleaned_t.split(" · ")[-1].strip()
            spec["short_title"] = cleaned_t

        # Parse Stats (mi, ft)
        m_dist = re.search(r"([\d.]+)\s*mi\b", text, re.IGNORECASE)
        if m_dist:
            spec["distance_mi"] = float(m_dist.group(1))
        m_ele = re.search(r"([\d,]+)\s*ft\s*ascent", text, re.IGNORECASE)
        if m_ele:
            spec["elevation_ft"] = int(m_ele.group(1).replace(",", ""))

        # Dynamic motto based on ride stats
        if spec["elevation_ft"] >= 1500:
            spec["studio_motto"] = "Gravity Reduction Module: FAILED (Climbing Anyway)"
        elif spec["distance_mi"] <= 25:
            spec["studio_motto"] = "Powered by Espresso, Pastries & 0.2s FFmpeg Remux"
        else:
            spec["studio_motto"] = "No Riders Were Dropped in the Making of This Film (Mostly)"

        # Parse Section 5 YAML if agvs_bookends is present
        if "agvs_bookends:" in text:
            try:
                # Extract agvs_bookends block
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
                print(f"Note: Error parsing agvs_bookends block: {e}")

    # Check for hero image
    for hname in ("hero_drinking_8791.jpg", "hero_selfie_8783.jpg", "thumbnail.jpg", "IMG_8783.jpg"):
        c = project_dir / hname
        if c.exists():
            spec["hero_image"] = c
            break

    return spec


# ---------------------------------------------------------------------------
# Canvas Renderers (4K PNG)
# ---------------------------------------------------------------------------

def render_intro_canvas_4k(spec: dict, out_png: Path) -> Path:
    """Renders the 4K (3840x2160) AGVS Pre-Flight Postcard background canvas."""
    w, h = 3840, 2160
    canvas = Image.new("RGBA", (w, h), (16, 21, 28, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Subtle Background Grid & Coordinate Marks
    grid_color = (28, 36, 48, 160)
    for gx in range(120, w - 120, 240):
        draw.line([(gx, 120), (gx, h - 220)], fill=grid_color, width=1)
    for gy in range(180, h - 200, 240):
        draw.line([(120, gy), (w - 120, gy)], fill=grid_color, width=1)

    # 2. Draw Route Map on the Left (confined cleanly to x: 120 to 1180 so it never overlaps postcard)
    gpx_path = spec.get("gpx_file")
    if gpx_path and Path(gpx_path).exists():
        pts = parse_gpx_points(Path(gpx_path))
        if pts:
            draw_gpx_route_on_canvas(draw, pts, (120, 520, 1180, 1860))
    elif spec.get("hero_image") and Path(spec["hero_image"]).exists():
        # Blurred background fallback
        hero = Image.open(spec["hero_image"]).convert("RGBA").resize((w, h))
        hero_blurred = hero.filter(ImageFilter.GaussianBlur(50))
        # Darken
        dark_tint = Image.new("RGBA", (w, h), (14, 18, 24, 210))
        canvas = Image.alpha_composite(hero_blurred, dark_tint)
        draw = ImageDraw.Draw(canvas)

    # 3. Pre-render Realistic Soft Drop Shadow for the Tilted Postcard Frame
    # Postcard center: x ~ 2380, y ~ 1030, size ~ 2760 x 1608, tilted -2.0 deg
    shadow_mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_mask)

    # Postcard geometry
    card_w, card_h = 2752, 1608
    card_shadow = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 190))
    # Rotate shadow
    card_shadow_rot = card_shadow.rotate(-2.0, resample=Image.BICUBIC, expand=True)
    # Paste onto shadow mask with offset
    sw, sh = card_shadow_rot.size
    sx = int(2380 - sw / 2 + 28)
    sy = int(1030 - sh / 2 + 36)
    shadow_mask.paste(card_shadow_rot, (sx, sy), card_shadow_rot)
    # Blur shadow
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(38))
    canvas = Image.alpha_composite(canvas, shadow_mask)
    draw = ImageDraw.Draw(canvas)

    # 4. Top-Left AGVS Aerospace Rubber-Stamp Badge
    bx0, by0 = 120, 130
    font_badge = _load_font("title", 54)
    badge_text = "🚀 AGVS // ANTIGRAVITY VIDEO STUDIO"
    tb = draw.textbbox((0, 0), badge_text, font=font_badge)
    bw, bh = tb[2] - tb[0] + 48, tb[3] - tb[1] + 24

    # Aerospace bracket outline
    draw.rounded_rectangle([bx0, by0, bx0 + bw, by0 + bh], radius=8, outline=(0, 229, 255, 230), width=3)
    # Corner brackets accent
    draw.line([(bx0 - 6, by0 - 6), (bx0 + 20, by0 - 6)], fill=(0, 229, 255, 255), width=4)
    draw.line([(bx0 - 6, by0 - 6), (bx0 - 6, by0 + 20)], fill=(0, 229, 255, 255), width=4)
    draw.line([(bx0 + bw + 6, by0 - 6), (bx0 + bw - 20, by0 - 6)], fill=(0, 229, 255, 255), width=4)
    draw.line([(bx0 + bw + 6, by0 - 6), (bx0 + bw + 6, by0 + 20)], fill=(0, 229, 255, 255), width=4)
    draw.text((bx0 + 24, by0 + 10), badge_text, font=font_badge, fill=(245, 250, 255, 255))

    # Dynamic Studio Motto
    font_motto = _load_font("mono", 36)
    motto_text = f"« {spec['studio_motto']} »"
    draw.text((bx0 + 4, by0 + bh + 22), motto_text, font=font_motto, fill=(255, 202, 40, 240))

    # Location Badge Pill
    loc_text = f"📍 {spec['location_badge']}"
    font_loc = _load_font("title", 42)
    ltb = draw.textbbox((0, 0), loc_text, font=font_loc)
    lw, lh = ltb[2] - ltb[0] + 36, ltb[3] - ltb[1] + 18
    ly = by0 + bh + 78
    draw.rounded_rectangle([bx0, ly, bx0 + lw, ly + lh], radius=6, fill=(24, 32, 44, 230), outline=(58, 72, 94, 255), width=2)
    draw.text((bx0 + 18, ly + 8), loc_text, font=font_loc, fill=(0, 229, 255, 255))

    # 5. Bottom Ticket-Stub Manifest Bar
    bar_y0, bar_y1 = 1950, 2090
    bar_x0, bar_x1 = 120, 3720
    # Semi-translucent dark pill with perforated notches
    draw.rounded_rectangle([bar_x0, bar_y0, bar_x1, bar_y1], radius=16, fill=(20, 26, 36, 235), outline=(50, 64, 84, 255), width=2)
    # Perforated stub cutouts (left & right semicircle notches)
    draw.ellipse([bar_x0 - 24, (bar_y0 + bar_y1) // 2 - 24, bar_x0 + 24, (bar_y0 + bar_y1) // 2 + 24], fill=(16, 21, 28, 255))
    draw.ellipse([bar_x1 - 24, (bar_y0 + bar_y1) // 2 - 24, bar_x1 + 24, (bar_y0 + bar_y1) // 2 + 24], fill=(16, 21, 28, 255))

    font_ticket = _load_font("mono", 34)
    f_date = spec.get("date_str", "2026-11-05")
    f_title = spec.get("short_title", "Antigravity Ride")
    f_stats = f"{spec.get('distance_mi', 0.0):.1f} mi  •  {spec.get('elevation_ft', 0):,} ft"

    t_part1 = f"📅 DATE: {f_date}"
    t_part2 = f"🎬 MISSION: {f_title}"
    t_part3 = f"🚴 TELEMETRY: {f_stats}"

    cy = bar_y0 + (bar_y1 - bar_y0) // 2 - 16
    draw.text((bar_x0 + 60, cy), t_part1, font=font_ticket, fill=(200, 215, 230, 255))
    draw.text((bar_x0 + 640, cy), "│", font=font_ticket, fill=(70, 88, 112, 255))
    draw.text((bar_x0 + 680, cy), t_part2, font=font_ticket, fill=(255, 255, 255, 255))
    draw.text((bar_x1 - 820, cy), "│", font=font_ticket, fill=(70, 88, 112, 255))
    draw.text((bar_x1 - 780, cy), t_part3, font=font_ticket, fill=(0, 229, 255, 255))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    print(f"Generated 4K Opening Bookend Canvas -> {out_png}")
    return out_png


def render_outro_canvas_4k(spec: dict, out_png: Path) -> Path:
    """Renders the 4K (3840x2160) AGVS Post-Ride Bar Tab & Credits background canvas."""
    w, h = 3840, 2160
    canvas = Image.new("RGBA", (w, h), (14, 18, 24, 255))
    draw = ImageDraw.Draw(canvas)

    # 1. Subtle cafe / slate grid texture
    for gx in range(120, w - 120, 240):
        draw.line([(gx, 100), (gx, h - 100)], fill=(24, 30, 40, 130), width=1)
    for gy in range(120, h - 100, 240):
        draw.line([(120, gy), (w - 120, gy)], fill=(24, 30, 40, 130), width=1)

    # 2. Pre-render Realistic Soft Drop Shadow for Left Postcard (+1.5 deg tilt)
    # Postcard center: x ~ 1240, y ~ 1060, size ~ 2283 x 1353
    shadow_mask = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    card_w, card_h = 2283, 1353
    card_shadow = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 190))
    card_shadow_rot = card_shadow.rotate(1.5, resample=Image.BICUBIC, expand=True)
    sw, sh = card_shadow_rot.size
    sx = int(1240 - sw / 2 + 24)
    sy = int(1060 - sh / 2 + 32)
    shadow_mask.paste(card_shadow_rot, (sx, sy), card_shadow_rot)
    shadow_mask = shadow_mask.filter(ImageFilter.GaussianBlur(36))
    canvas = Image.alpha_composite(canvas, shadow_mask)
    draw = ImageDraw.Draw(canvas)

    # 3. Right Side: "AGVS Production Receipt / Credits Card"
    rx0, ry0 = 2360, 160
    rw = 1360
    dash_y = ry0 + 160

    # Header
    font_h1 = _load_font("receipt", 46)
    font_h2 = _load_font("mono", 26)
    font_cat = _load_font("mono", 26)
    font_item = _load_font("receipt", 29)
    font_hero = _load_font("receipt", 29)
    font_footer = _load_font("mono", 23)

    def _draw_item(x: int, y: int, text: str, font, fill, max_w: int = 1220, line_h: int = 38) -> int:
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
        for line_str in lines:
            draw.text((x, y), line_str, font=font, fill=fill)
            y += line_h
        return y

    cur_y = dash_y + 32

    # Pre-calculate or render sections
    # We will draw background container after knowing exact bottom bounds for a tailored receipt look
    # or draw a crisp container with ry1 calculated dynamically!
    # Let's collect elements or draw on a dedicated receipt surface:
    receipt_img = Image.new("RGBA", (rw, 2000), (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(receipt_img)

    # Receipt relative coords: rx in [0..rw]
    # Header inside receipt
    r_draw.text((50, 44), "CREATED BY ALEXANDER KOMLIK", font=font_h1, fill=(255, 255, 255, 255))
    r_draw.text((52, 104), "AN ANTIGRAVITY VIDEO STUDIO PRODUCTION", font=font_h2, fill=(0, 229, 255, 240))
    r_draw.line([(36, 160), (rw - 36, 160)], fill=(70, 88, 112, 220), width=2)

    ry = 192

    def _r_item(x: int, y: int, text: str, font, fill, max_w: int = rw - 140, line_h: int = 38) -> int:
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
        for line_str in lines:
            r_draw.text((x, y), line_str, font=font, fill=fill)
            y += line_h
        return y

    # THE CREW / PELOTON
    r_draw.text((50, ry), "THE CREW / PELOTON:", font=font_cat, fill=(255, 202, 40, 240))
    ry += 34
    for c in spec.get("cast_credits", [])[:4]:
        ry = _r_item(70, ry, f"• {c}", font_item, (230, 238, 248, 255), line_h=38)
    ry += 14

    # LEAD STEED
    r_draw.text((50, ry), "LEAD STEED:", font=font_cat, fill=(255, 202, 40, 240))
    ry += 34
    ry = _r_item(70, ry, f"• {spec.get('steed_credit')}", font_item, (230, 238, 248, 255), line_h=38)
    ry += 14

    # CAMERA & GIMBAL
    r_draw.text((50, ry), "CAMERA & GIMBAL:", font=font_cat, fill=(255, 202, 40, 240))
    ry += 34
    ry = _r_item(70, ry, "• BleeqUP Ranger AI Glasses (100% Organic Head-Turns)", font_item, (230, 238, 248, 255), line_h=36)
    ry = _r_item(70, ry, "• iPhone 15 Pro (Live Dual-Cam Sync & Selfie Cuts)", font_item, (230, 238, 248, 255), line_h=36)
    ry += 14

    # TELEMETRY & MEMORY
    r_draw.text((50, ry), "TELEMETRY & MEMORY BANK:", font=font_cat, fill=(255, 202, 40, 240))
    ry += 34
    ry = _r_item(70, ry, "• Garmin Edge 840 (Smoothed — 0% Fake Altimeter Spikes)", font_item, (230, 238, 248, 255), line_h=36)
    ry = _r_item(70, ry, "• my_digital_brain.md (Cross-Era Lifetime Lore & Archival Pulls)", font_item, (230, 238, 248, 255), line_h=36)
    ry += 14

    # STUDIO ENGINE & MAIN HERO
    r_draw.text((50, ry), "STUDIO ENGINE & MAIN HERO:", font=font_cat, fill=(0, 229, 255, 240))
    ry += 34
    hero_title = spec.get("main_hero", "Antigravity Video Studio (AGVS v2.0)")
    repo_url = spec.get("github_repo", "github.com/akomlik/antigravity-video-studio")
    ry = _r_item(70, ry, f"• {hero_title}", font_hero, (255, 255, 255, 255), line_h=36)
    ry = _r_item(70, ry, f"• Open Source: {repo_url}", font_hero, (100, 220, 255, 255), line_h=36)
    ry = _r_item(70, ry, "• Autonomous AI Pair Programming & 0.2s Lossless Remux", font_hero, (180, 205, 235, 230), line_h=36)
    ry += 14

    # FUEL & SPONSORS
    r_draw.text((50, ry), "FUEL & SPONSORS:", font=font_cat, fill=(255, 202, 40, 240))
    ry += 34
    ry = _r_item(70, ry, f"• {spec.get('fuel_sponsors')}", font_item, (230, 238, 248, 255), line_h=38)
    ry += 20

    # Bottom Dashed Line
    r_draw.line([(36, ry), (rw - 36, ry)], fill=(70, 88, 112, 220), width=2)
    ry += 24

    # Bottom Footer Stamp
    r_draw.text((50, ry), "⚠️ 0% Gravity Guaranteed on Descents Only", font=font_footer, fill=(255, 112, 67, 240))
    r_draw.text((50, ry + 30), "No Argon Quotas Were Harmed in This Render", font=font_footer, fill=(160, 180, 200, 200))
    r_draw.text((50, ry + 60), f"🚀 AGVS Repo: {repo_url}", font=font_footer, fill=(0, 229, 255, 230))
    ry += 105

    # Tailored receipt height
    card_rh = ry
    receipt_bg = Image.new("RGBA", (rw, card_rh), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(receipt_bg)
    bg_draw.rounded_rectangle([0, 0, rw, card_rh], radius=14, fill=(20, 25, 34, 248), outline=(52, 66, 86, 255), width=2)

    # Paste receipt content onto background
    receipt_final = Image.alpha_composite(receipt_bg, receipt_img.crop((0, 0, rw, card_rh)))

    # Composite receipt onto canvas with realistic soft drop shadow
    receipt_shadow = Image.new("RGBA", (rw, card_rh), (0, 0, 0, 160))
    sh_pad = 40
    sh_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    sh_layer.paste(receipt_shadow, (rx0 + 16, ry0 + 20))
    sh_layer = sh_layer.filter(ImageFilter.GaussianBlur(30))
    canvas = Image.alpha_composite(canvas, sh_layer)
    canvas.paste(receipt_final, (rx0, ry0), receipt_final)

    out_png.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out_png)
    print(f"Generated 4K Closing Bookend Canvas -> {out_png}")
    return out_png


def render_postcard_border_png(width: int, height: int, video_w: int, video_h: int, border_px: int, chin_px: int, script_text: str | None, out_png: Path) -> Path:
    """Creates a transparent-center postcard border with optional script text on the bottom chin."""
    border_img = Image.new("RGBA", (width, height), (255, 255, 255, 255))
    d = ImageDraw.Draw(border_img)
    # Cut out the inner video area
    d.rectangle([border_px, border_px, border_px + video_w, border_px + video_h], fill=(0, 0, 0, 0))

    if script_text:
        font_script = _load_font("script", 64)
        bbox = d.textbbox((0, 0), script_text, font=font_script)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        tx = (width - tw) // 2
        ty = height - chin_px + (chin_px - th) // 2 - 8
        d.text((tx, ty), script_text, font=font_script, fill=(35, 44, 58, 255))

    out_png.parent.mkdir(parents=True, exist_ok=True)
    border_img.save(out_png)
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
    Composites the first 3.5s of the opening clip inside a -2.0° tilted white postcard frame
    over the 4K route map canvas.
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # Postcard dimensions (70% of 3840x2160 = 2688x1512)
    vw, vh = 2688, 1512
    bw = 32
    chin = 64
    pw, ph = vw + bw * 2, vh + bw + chin

    border_png = out_mp4.parent / "intro_postcard_border.png"
    render_postcard_border_png(pw, ph, vw, vh, bw, chin, script_text=None, out_png=border_png)

    # Postcard center: x ~ 2380, y ~ 1030
    # Center after rotation (-2.0 deg):
    # Top-left offset for ffmpeg overlay:
    # pw = 2752, ph = 1608
    # Center at (2380, 1030) -> top-left ~ (1004, 226)
    ox, oy = 1004, 226

    # FFmpeg filter:
    # Scale video -> pad to card size -> overlay border -> rotate -2 deg -> overlay on canvas
    cmd = [
        "/opt/homebrew/bin/ffmpeg", "-y",
        "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(canvas_png),
        "-ss", f"{clip_start_s:.3f}", "-t", f"{duration_s:.2f}", "-i", str(first_clip_path),
        "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(border_png),
        "-filter_complex",
        f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=decrease,pad={pw}:{ph}:{bw}:{bw}:color=0x00000000[vpad]; "
        f"[vpad][2:v]overlay=0:0:format=auto[card]; "
        f"[card]format=rgba,rotate=-2.0*PI/180:ow=rotw(-2.0*PI/180):oh=roth(-2.0*PI/180):c=none[rcard]; "
        f"[0:v][rcard]overlay={ox}:{oy}:format=auto[outv]",
        "-map", "[outv]", "-map", "1:a?",
        "-c:v", "h264_videotoolbox", "-b:v", "40M",
        "-c:a", "aac", "-b:a", "192k",
        "-t", f"{duration_s:.2f}",
        str(out_mp4),
    ]

    print(f"Rendering Opening Postcard Bookend (3.5s) -> {out_mp4}...")
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"Warning: videotoolbox failed, trying libx264 ({res.stderr[-250:]})")
        cmd[cmd.index("h264_videotoolbox")] = "libx264"
        cmd.insert(cmd.index("libx264") + 1, "-preset")
        cmd.insert(cmd.index("-preset") + 1, "veryfast")
        subprocess.run(cmd, check=True)

    print(f"Opening Bookend Video ready: {out_mp4} ({out_mp4.stat().st_size / 1024 / 1024:.1f} MB)")
    return out_mp4


def composite_outro_bookend_mp4(
    canvas_png: Path,
    last_clip_path: Path,
    out_mp4: Path,
    duration_s: float = 4.5,
    last_clip_is_still: bool = False,
    last_clip_dur_s: float = 7.0,
) -> Path:
    """
    Composites the final 4.5s of the timeline inside a +1.5° tilted white postcard frame on the left,
    alongside the AGVS Production Receipt on the right.
    """
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    # Postcard dimensions (58% of 3840x2160 = 2227x1253)
    vw, vh = 2227, 1253
    bw = 28
    chin = 72
    pw, ph = vw + bw * 2, vh + bw + chin

    border_png = out_mp4.parent / "outro_postcard_border.png"
    render_postcard_border_png(
        pw, ph, vw, vh, bw, chin, script_text="Wish you were here! — AGVS", out_png=border_png
    )

    # Center at x ~ 1240, y ~ 1060
    # Card size: pw=2283, ph=1353
    # Top-left offset: 1240 - 2283/2 ~ 98, 1060 - 1353/2 ~ 383
    ox, oy = 98, 383

    # If still photo: loop for duration_s with gentle zoom (scale 100% -> 104%)
    if last_clip_is_still:
        vf_input = (
            f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=increase,crop={vw}:{vh},"
            f"pad={pw}:{ph}:{bw}:{bw}:color=0x00000000[vpad]"
        )
        cmd = [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(canvas_png),
            "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(last_clip_path),
            "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(border_png),
            "-f", "lavfi", "-t", f"{duration_s:.2f}", "-i", "anullsrc=r=48000:cl=stereo",
            "-filter_complex",
            f"{vf_input}; "
            f"[vpad][2:v]overlay=0:0:format=auto[card]; "
            f"[card]format=rgba,rotate=1.5*PI/180:ow=rotw(1.5*PI/180):oh=roth(1.5*PI/180):c=none[rcard]; "
            f"[0:v][rcard]overlay={ox}:{oy}:format=auto[outv]",
            "-map", "[outv]", "-map", "3:a",
            "-c:v", "h264_videotoolbox", "-b:v", "40M",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration_s:.2f}",
            str(out_mp4),
        ]
    else:
        # Video clip: take the final duration_s seconds
        clip_st = max(0.0, last_clip_dur_s - duration_s)
        cmd = [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(canvas_png),
            "-ss", f"{clip_st:.3f}", "-t", f"{duration_s:.2f}", "-i", str(last_clip_path),
            "-loop", "1", "-t", f"{duration_s:.2f}", "-i", str(border_png),
            "-filter_complex",
            f"[1:v]scale={vw}:{vh}:force_original_aspect_ratio=decrease,pad={pw}:{ph}:{bw}:{bw}:color=0x00000000[vpad]; "
            f"[vpad][2:v]overlay=0:0:format=auto[card]; "
            f"[card]format=rgba,rotate=1.5*PI/180:ow=rotw(1.5*PI/180):oh=roth(1.5*PI/180):c=none[rcard]; "
            f"[0:v][rcard]overlay={ox}:{oy}:format=auto[outv]",
            "-map", "[outv]", "-map", "1:a?",
            "-c:v", "h264_videotoolbox", "-b:v", "40M",
            "-c:a", "aac", "-b:a", "192k",
            "-t", f"{duration_s:.2f}",
            str(out_mp4),
        ]

    print(f"Rendering Closing Credits Bookend (4.5s) -> {out_mp4}...")
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if res.returncode != 0:
        print(f"Warning: videotoolbox failed, trying libx264 ({res.stderr[-250:]})")
        cmd[cmd.index("h264_videotoolbox")] = "libx264"
        cmd.insert(cmd.index("libx264") + 1, "-preset")
        cmd.insert(cmd.index("-preset") + 1, "veryfast")
        subprocess.run(cmd, check=True)

    print(f"Closing Bookend Video ready: {out_mp4} ({out_mp4.stat().st_size / 1024 / 1024:.1f} MB)")
    return out_mp4


# ---------------------------------------------------------------------------
# Main Orchestration
# ---------------------------------------------------------------------------

def generate_project_bookends(
    project_dir: Path,
    first_clip_path: Path | None = None,
    last_clip_path: Path | None = None,
    intro_duration_s: float = 3.5,
    outro_duration_s: float = 4.5,
) -> tuple[Path, Path]:
    """Generates both 4K composited MP4 bookends for a project folder."""
    project_dir = Path(project_dir).expanduser().resolve()
    spec = extract_project_bookends_spec(project_dir)

    intro_dur = spec.get("intro_duration_s", intro_duration_s)
    outro_dur = spec.get("outro_duration_s", outro_duration_s)

    overlays_dir = project_dir / "overlays"
    overlays_dir.mkdir(parents=True, exist_ok=True)

    intro_canvas = overlays_dir / "bookend_intro_canvas_4K.png"
    outro_canvas = overlays_dir / "bookend_outro_canvas_4K.png"

    render_intro_canvas_4k(spec, intro_canvas)
    render_outro_canvas_4k(spec, outro_canvas)

    # Determine first and last clips if not provided
    if not first_clip_path or not Path(first_clip_path).exists():
        manifest_p = project_dir / "project_manifest.json"
        if manifest_p.exists():
            m = json.loads(manifest_p.read_text(encoding="utf-8"))
            raw_folder = Path("~/Movies").expanduser() / m.get("raw_media_folder", "")
            if raw_folder.exists():
                vids = sorted(list(raw_folder.glob("VIDEO_*.MP4")) + list(raw_folder.glob("IMG_*.MOV")))
                if vids:
                    first_clip_path = vids[0]

    if not last_clip_path or not Path(last_clip_path).exists():
        manifest_p = project_dir / "project_manifest.json"
        if manifest_p.exists():
            m = json.loads(manifest_p.read_text(encoding="utf-8"))
            raw_folder = Path("~/Movies").expanduser() / m.get("raw_media_folder", "")
            if raw_folder.exists():
                stills = sorted(list(raw_folder.glob("IMG_*.jpg")) + list(raw_folder.glob("IMG_*.HEIC")))
                if stills:
                    last_clip_path = stills[-1]

    if not first_clip_path:
        raise RuntimeError("Could not determine first_clip_path for opening bookend.")
    if not last_clip_path:
        raise RuntimeError("Could not determine last_clip_path for closing bookend.")

    first_clip_path = Path(first_clip_path).expanduser().resolve()
    last_clip_path = Path(last_clip_path).expanduser().resolve()

    intro_mp4 = overlays_dir / "bookend_intro_4K.mp4"
    outro_mp4 = overlays_dir / "bookend_outro_4K.mp4"

    composite_intro_bookend_mp4(
        canvas_png=intro_canvas,
        first_clip_path=first_clip_path,
        out_mp4=intro_mp4,
        duration_s=intro_dur,
    )

    last_is_still = last_clip_path.suffix.lower() in (".jpg", ".jpeg", ".png", ".heic")
    composite_outro_bookend_mp4(
        canvas_png=outro_canvas,
        last_clip_path=last_clip_path,
        out_mp4=outro_mp4,
        duration_s=outro_dur,
        last_clip_is_still=last_is_still,
    )

    return intro_mp4, outro_mp4


def main():
    p = argparse.ArgumentParser(description="AGVS Signature Bookends Generator (4K Postcard Opening & Bar Tab Credits)")
    p.add_argument("--project-dir", required=True, help="Path to project directory in 04_Project_Catalog/YEAR/<project>")
    p.add_argument("--first-clip", help="Path to opening clip (first 3.5s)")
    p.add_argument("--last-clip", help="Path to closing clip (last 4.5s)")
    p.add_argument("--intro-dur", type=float, default=3.5, help="Intro duration in seconds (default: 3.5)")
    p.add_argument("--outro-dur", type=float, default=4.5, help="Outro duration in seconds (default: 4.5)")
    args = p.parse_args()

    intro_mp4, outro_mp4 = generate_project_bookends(
        project_dir=Path(args.project_dir),
        first_clip_path=Path(args.first_clip) if args.first_clip else None,
        last_clip_path=Path(args.last_clip) if args.last_clip else None,
        intro_duration_s=args.intro_dur,
        outro_duration_s=args.outro_dur,
    )
    print(f"\n✅ AGVS Bookends successfully generated:\n  Intro: {intro_mp4}\n  Outro: {outro_mp4}")


if __name__ == "__main__":
    main()
