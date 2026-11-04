#!/usr/bin/env python3
"""
ingest_and_sync_media.py
Universal pre-processor for Google Antigravity video workflows:
- Step 0a: Runs ranger-sync (https://github.com/akomlik/bleequp-ranger-sync) if needed
- Step 0b: Ensures Storyboard.md exists (or creates an initial Storyboard.md draft if missing)
- Step 0c: Converts iPhone .HEIC to .jpg via macOS sips & extracts .proxies/ video thumbnails
- Auto-detects genre: cycling_ride | hike_outdoor | social_event | archival_slideshow
- Extracts QuickTime ISO6709 GPS tags from iPhone .MOV clips and syncs Garmin .gpx when present
- Scans 03_Audio_Library/01_Curated_BGM/ for [BPM]_[Mood]_[TrackName]_[Artist].mp3 tracks
- Saves project_manifest.json and syncs Storyboard.md to 04_Project_Catalog/YEAR/
"""

import argparse
import datetime as dt
import json
import math
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

os.environ["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{Path.home() / '.local/bin'}:{os.environ.get('PATH', '')}"

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
BGM_ROOT = STUDIO_ROOT / "03_Audio_Library" / "01_Curated_BGM"


def run_filmcraft_version_check(studio_root: Path):
    """Step 0a-pre: Enforces FilmCraft >= v0.17.0, auto-syncs filmcraft-cli, and diffs new MCP commands."""
    checker = studio_root / ".agents/skills/assemble-timeline/scripts/check_filmcraft_env.py"
    if checker.exists():
        sys.path.insert(0, str(checker.parent))
        try:
            from check_filmcraft_env import verify_filmcraft_environment
            status = verify_filmcraft_environment(auto_sync_cli=True, check_remote=True)
            print(
                f"FilmCraft Verified: App v{status.get('app_version')} | CLI v{status.get('cli_version')} "
                f"({status.get('capabilities', {}).get('total', 0)} MCP commands)"
            )
            return status
        except Exception as e:
            print(f"FilmCraft check warning: {e}")
    return {}


def run_bleequp_ranger_sync_if_needed(project_dir: Path, skip_sync: bool):
    """Step 0a: Runs akomlik/bleequp-ranger-sync (ranger-sync) if installed and not already synced."""
    if skip_sync:
        print("Skipping ranger-sync (--skip-bleequp-sync flag set; files already fixed).")
        return
    marker = project_dir / ".bleequp_synced"
    if marker.exists():
        print("Detected .bleequp_synced marker; BleeqUP media already processed.")
        return
    # Also check if files already have epoch timestamps from ranger-sync or if no BleeqUP files exist
    has_bleequp = any(
        f.name.startswith(("VIDEO_", "IMG_17"))
        for f in project_dir.iterdir()
        if f.is_file()
    )
    if not has_bleequp:
        return
    sync_bin = shutil.which("ranger-sync") or shutil.which("bleequp-ranger-sync")
    if sync_bin:
        print(f"Step 0: Running {sync_bin} on {project_dir}...")
        subprocess.run([sync_bin, str(project_dir)], check=False)
        marker.touch()
    else:
        print("Note: ranger-sync not on PATH or already run; proceeding with existing files.")


def convert_heic_to_jpg(project_dir: Path):
    """Step 0c: Converts iPhone .HEIC stills to high-quality .jpg via macOS sips."""
    for heic in list(project_dir.glob("*.HEIC")) + list(project_dir.glob("*.heic")):
        jpg_out = heic.with_suffix(".jpg")
        if not jpg_out.exists():
            subprocess.run(
                ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "95", str(heic), "--out", str(jpg_out)],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )


def generate_video_proxy_thumb(video_path: Path, proxy_dir: Path, duration_s: float):
    """Extracts a lightweight 640px JPEG thumbnail at 25% into the video clip for fast AI vision inspection."""
    proxy_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = proxy_dir / f"{video_path.stem}_thumb.jpg"
    if not thumb_path.exists():
        if shutil.which("ffmpeg"):
            seek_s = max(0.0, round(duration_s * 0.25, 2))
            subprocess.run(
                [
                    "ffmpeg", "-y", "-ss", str(seek_s), "-i", str(video_path),
                    "-frames:v", "1", "-vf", "scale=640:-1", "-q:v", "4", str(thumb_path)
                ],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
        else:
            # macOS native QuickLook fallback if ffmpeg is still installing
            subprocess.run(
                ["qlmanage", "-t", "-s", "640", "-o", str(proxy_dir), str(video_path)],
                check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            ql_png = proxy_dir / f"{video_path.name}.png"
            if ql_png.exists():
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", str(ql_png), "--out", str(thumb_path)],
                    check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
                )
                ql_png.unlink(missing_ok=True)
    return str(thumb_path) if thumb_path.exists() else None


def parse_iso6709(iso_str: str):
    """Parses Apple QuickTime ISO6709 location string (e.g. '+39.7707+003.0230+028.000/') into (lat, lon)."""
    if not iso_str:
        return None, None
    m = re.match(r"^([+-]\d+\.\d+)([+-]\d+\.\d+)", iso_str.strip())
    if m:
        return round(float(m.group(1)), 5), round(float(m.group(2)), 5)
    return None, None


def haversine_m(lat1, lon1, lat2, lon2):
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def parse_gpx(gpx_path: Path):
    """Parses Garmin GPX 1.1 with TrackPointExtension (hr, cad, power)."""
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    points = []
    total_dist_m = 0.0
    total_elev_gain_m = 0.0

    for trkpt in root.iter():
        if not trkpt.tag.endswith("trkpt"):
            continue
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        ele, timestamp, hr, cad, power = 0.0, None, None, None, None

        for child in trkpt.iter():
            tag = child.tag.split("}")[-1]
            if tag == "ele" and child.text:
                ele = float(child.text)
            elif tag == "time" and child.text:
                ts_str = child.text.replace("Z", "+00:00")
                timestamp = dt.datetime.fromisoformat(ts_str)
            elif tag == "hr" and child.text:
                hr = int(float(child.text))
            elif tag == "cad" and child.text:
                cad = int(float(child.text))
            elif tag in ("power", "watts") and child.text:
                power = int(float(child.text))

        if timestamp is None:
            continue

        speed_kmh = 0.0
        gradient_pct = 0.0
        if points:
            prev = points[-1]
            dist = haversine_m(prev["lat"], prev["lon"], lat, lon)
            dt_sec = max((timestamp - prev["time"]).total_seconds(), 0.001)
            speed_kmh = (dist / dt_sec) * 3.6
            total_dist_m += dist
            dele = ele - prev["ele"]
            if dele > 0.2:
                total_elev_gain_m += dele
            # Compute smoothed road grade over a >=40m horizontal lookback window
            # so 0.2m barometric sensor quantization does not create fake 6.7% spikes on flat roads!
            cur_km = total_dist_m / 1000.0
            anchor = prev
            for p_back in reversed(points):
                if (cur_km - p_back["dist_km"]) * 1000.0 >= 40.0:
                    anchor = p_back
                    break
            horiz_m = (cur_km - anchor["dist_km"]) * 1000.0
            if horiz_m >= 15.0:
                gradient_pct = ((ele - anchor["ele"]) / horiz_m) * 100.0

        points.append({
            "time": timestamp,
            "lat": lat,
            "lon": lon,
            "ele": round(ele, 1),
            "dist_km": round(total_dist_m / 1000.0, 2),
            "speed_kmh": round(speed_kmh, 1),
            "gradient_pct": round(gradient_pct, 1),
            "hr": hr,
            "cad": cad,
            "power": power,
        })

    return points, round(total_dist_m / 1000.0, 2), round(total_elev_gain_m, 1)


def probe_media_file(filepath: Path, proxy_dir: Path):
    """Extracts resolution, aspect ratio, fps, duration, codec, QuickTime GPS, and creation timestamp."""
    ext = filepath.suffix.lower()
    info = {
        "filename": filepath.name,
        "abspath": str(filepath.resolve()),
        "media_type": "video" if ext in (".mp4", ".mov") else "still",
        "source_device": "unknown",
        "width": 0,
        "height": 0,
        "aspect_ratio": "16:9",
        "fps": 0.0,
        "duration_s": 0.0,
        "color_space": "Rec.709",
        "creation_time_utc": None,
        "qt_lat": None,
        "qt_lon": None,
        "proxy_thumb": None,
    }

    if info["media_type"] == "video":
        if shutil.which("ffprobe"):
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", str(filepath)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and res.stdout:
                data = json.loads(res.stdout)
                fmt = data.get("format", {})
                tags = fmt.get("tags", {})
                info["duration_s"] = round(float(fmt.get("duration", 0.0)), 2)

                for s in data.get("streams", []):
                    if s.get("codec_type") == "video":
                        info["width"] = int(s.get("width", 0))
                        info["height"] = int(s.get("height", 0))
                        r_fps = s.get("r_frame_rate", "30/1").split("/")
                        info["fps"] = round(float(r_fps[0]) / max(float(r_fps[1]), 1.0), 2)
                        trc = s.get("color_transfer", "")
                        if "arib-std-b67" in trc or "smpte2084" in trc:
                            info["color_space"] = "BT.2020_HDR"
                        break

                make = (tags.get("com.apple.quicktime.make", "") + tags.get("encoder", "")).lower()
                if "apple" in make or filepath.suffix.lower() == ".mov":
                    info["source_device"] = "iPhone_15_Pro"
                elif (info["width"], info["height"]) in [(3200, 1800), (1800, 3200), (1920, 1080), (1080, 1920)]:
                    info["source_device"] = "BleeqUP_Ranger_AI"

                ctime = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
                if ctime:
                    info["creation_time_utc"] = ctime
                loc_iso = tags.get("com.apple.quicktime.location.ISO6709") or tags.get("location")
                if loc_iso:
                    info["qt_lat"], info["qt_lon"] = parse_iso6709(loc_iso)
        else:
            # Spotlight mdls fallback if ffprobe is not yet installed
            res = subprocess.run(
                [
                    "mdls", "-name", "kMDItemDurationSeconds",
                    "-name", "kMDItemPixelWidth", "-name", "kMDItemPixelHeight",
                    "-name", "kMDItemContentCreationDate",
                    "-name", "kMDItemLatitude", "-name", "kMDItemLongitude",
                    str(filepath)
                ],
                capture_output=True, text=True, check=False
            )
            for line in res.stdout.splitlines():
                if "kMDItemDurationSeconds" in line and "(null)" not in line:
                    info["duration_s"] = round(float(line.split("=")[-1].strip()), 2)
                elif "kMDItemPixelWidth" in line and "(null)" not in line:
                    info["width"] = int(float(line.split("=")[-1].strip()))
                elif "kMDItemPixelHeight" in line and "(null)" not in line:
                    info["height"] = int(float(line.split("=")[-1].strip()))
                elif "kMDItemLatitude" in line and "(null)" not in line:
                    info["qt_lat"] = round(float(line.split("=")[-1].strip()), 5)
                elif "kMDItemLongitude" in line and "(null)" not in line:
                    info["qt_lon"] = round(float(line.split("=")[-1].strip()), 5)
            info["source_device"] = "iPhone_15_Pro" if filepath.suffix.lower() == ".mov" else "BleeqUP_Ranger_AI"

        info["proxy_thumb"] = generate_video_proxy_thumb(filepath, proxy_dir, info["duration_s"])
    else:
        res = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", "-g", "creation", str(filepath)],
            capture_output=True, text=True, check=False
        )
        for line in res.stdout.splitlines():
            if "pixelWidth:" in line:
                info["width"] = int(line.split(":")[-1].strip())
            elif "pixelHeight:" in line:
                info["height"] = int(line.split(":")[-1].strip())
            elif "creation:" in line and not info["creation_time_utc"]:
                raw_c = line.split("creation:")[-1].strip()
                if raw_c and raw_c != "<nil>":
                    info["creation_time_utc"] = raw_c
        if (info["width"], info["height"]) in [(4656, 3496), (3496, 4656)]:
            info["source_device"] = "BleeqUP_Ranger_AI"
        else:
            info["source_device"] = "Still_Camera_Or_Scan"

    if info["width"] and info["height"]:
        ratio = info["width"] / info["height"]
        if ratio < 0.85:
            info["aspect_ratio"] = "9:16_portrait"
        elif ratio < 1.55:
            info["aspect_ratio"] = "4:3_or_vintage"
        else:
            info["aspect_ratio"] = "16:9_wide"

    if not info["creation_time_utc"]:
        mtime = dt.datetime.fromtimestamp(filepath.stat().st_mtime, tz=dt.timezone.utc)
        info["creation_time_utc"] = mtime.isoformat()

    return info


def ensure_or_migrate_storyboard(project_dir: Path, catalog_dir: Path, genre: str, media_items: list):
    """
    Step 0b: Ensures Storyboard.md exists.
    - If missing, creates a chronological Storyboard.md skeleton from the probed media inventory
      so the agent can immediately enrich it and ask the user for story refinements.
    """
    storyboard_path = project_dir / "Storyboard.md"
    status = "existing"

    if not storyboard_path.exists():
        status = "created_skeleton_needs_refinement"
        lines = [
            f"# Storyboard: {project_dir.name}",
            f"- **Detected Genre:** `{genre}`",
            f"- **Total Media Files:** {len(media_items)} (`{sum(1 for m in media_items if m['media_type']=='video')}` videos, `{sum(1 for m in media_items if m['media_type']=='still')}` stills)",
            "- **Status:** `DRAFT — Awaiting AI Visual Inspection & User Story Refinement`",
            "",
            "## 1. Story Premise & Highlights (Add a few lines or tell Gemini in chat)",
            "- *[Who is in this story, what was the funniest/best moment, and are there any throwback photos or YouTube links to weave in?]*",
            "",
            "## 2. Scene-by-Scene Storyboard (`Scene 00` -> `Scene N`)",
            "- **Scene 00 (Optional Flashback / Intro Hook):** *[Pending visual inspection]*",
            "- **Scene 01 (Opening / Departure):** *[Pending visual inspection]*",
            "",
            "## 3. Chronological Media & GPS Log (Auto-Generated)",
        ]
        for m in media_items:
            gps_str = f" (GPS: {m['qt_lat']}, {m['qt_lon']})" if m.get("qt_lat") else ""
            dur_str = f" [{m['duration_s']}s]" if m["media_type"] == "video" else " [Still]"
            lines.append(f"- `{m['filename']}` — `{m['creation_time_utc']}`{dur_str}{gps_str}")
        storyboard_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"Created initial {storyboard_path.name} draft for AI visual inspection.")

    # Always keep a synced copy inside 04_Project_Catalog/YEAR/<project_name>/Storyboard.md
    shutil.copy2(storyboard_path, catalog_dir / "Storyboard.md")
    return str(storyboard_path), status


def detect_genre(requested_genre: str, gpx_points: list, media_items: list):
    if requested_genre != "auto":
        return requested_genre
    videos = [m for m in media_items if m["media_type"] == "video"]
    if not videos and media_items:
        return "archival_slideshow"
    if gpx_points:
        avg_spd = sum(p["speed_kmh"] for p in gpx_points) / max(len(gpx_points), 1)
        return "cycling_ride" if avg_spd >= 10.0 else "hike_outdoor"
    if any(m["source_device"] == "BleeqUP_Ranger_AI" for m in media_items):
        return "cycling_ride"
    return "social_event"


def recommend_music_tracks(genre: str, studio_root: Path):
    """
    Scans 03_Audio_Library/01_Curated_BGM/ and CreatorMix online catalog.
    Enforces the Anti-Monotony Non-Reuse Law: excludes tracks previously used in 04_Project_Catalog/!
    If local pool has < 3 unused candidates, automatically supplements from CreatorMix online catalog.
    """
    music_root = studio_root / "03_Audio_Library" / "01_Curated_BGM"
    genre_folder_map = {
        "cycling_ride": (["01_Rolling_Cadence", "03_Punchy_Climbs"], ["synthwave", "house", "rock"]),
        "hike_outdoor": (["02_Scenic_Wonder", "04_Warm_Social_And_Retro"], ["lofi", "chillhop", "mixes"]),
        "social_event": (["04_Warm_Social_And_Retro", "01_Rolling_Cadence"], ["chillhop", "lofi"]),
        "archival_slideshow": (["04_Warm_Social_And_Retro", "02_Scenic_Wonder"], ["lofi", "mixes"]),
    }
    preferred_subs, cm_genres = genre_folder_map.get(genre, (["01_Rolling_Cadence"], ["synthwave"]))
    
    # Check previously used tracks in 04_Project_Catalog/
    find_music_dir = studio_root / ".agents/skills/find-music/scripts"
    sys.path.insert(0, str(find_music_dir))
    used_tracks = set()
    try:
        from fetch_creatormix_catalog import get_previously_used_tracks, search_catalog
        used_tracks = get_previously_used_tracks(studio_root)
    except Exception:
        pass

    candidates = []
    if music_root.exists():
        for f in sorted(music_root.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac") and not f.name.startswith("."):
                # Parse [BPM]_[Mood]_[TrackName]_[Artist].mp3 or fallback regex
                tax_match = re.match(r"^(\d{2,3})bpm_([^_]+)_([^_]+)_(.+)\.\w+$", f.name, re.IGNORECASE)
                if tax_match:
                    bpm = int(tax_match.group(1))
                    mood_tag = tax_match.group(2)
                    track_title = tax_match.group(3)
                    artist = tax_match.group(4)
                else:
                    bpm_match = re.search(r"(\d{2,3})\s*bpm", f.name.lower())
                    bpm = int(bpm_match.group(1)) if bpm_match else 115
                    mood_tag = f.parent.name
                    track_title = f.stem
                    artist = "CreatorMix_Or_YTAudio"

                # Check if already used in a project
                clean_title = re.sub(r"[^a-z0-9]", "", track_title.lower())
                is_used = any(u in clean_title or clean_title in u for u in used_tracks if len(u) > 3)
                if is_used:
                    continue  # Enforce Anti-Monotony Non-Reuse Law!

                beat_interval_s = round(60.0 / max(bpm, 1), 3)
                parent_name = f.parent.name
                priority = 1 if parent_name == preferred_subs[0] else (2 if parent_name in preferred_subs else 3)
                candidates.append({
                    "filename": f.name,
                    "abspath": str(f.resolve()),
                    "mood_folder": parent_name,
                    "mood_tag": mood_tag,
                    "track_title": track_title,
                    "artist": artist,
                    "estimated_bpm": bpm,
                    "beat_interval_s": beat_interval_s,
                    "recommended_cut_4bars_s": round(beat_interval_s * 8, 2),
                    "genre_match_priority": priority,
                    "source": "local_pool",
                })

    # If local pool has fewer than 3 unused matches, supplement from CreatorMix online catalog (134 tracks)
    if len(candidates) < 3:
        try:
            from fetch_creatormix_catalog import search_catalog
            for g in cm_genres:
                online_matches = search_catalog(genre=g, max_duration_s=180, exclude_used=True, limit=3)
                for om in online_matches:
                    candidates.append({
                        "filename": f"[ONLINE] {om['title']} ({om['duration_formatted']}) - {om['genre'].upper()}",
                        "abspath": None,
                        "mood_folder": preferred_subs[0],
                        "mood_tag": om["genre"].capitalize(),
                        "track_title": om["title"],
                        "artist": "CreatorMix",
                        "album": om["album"],
                        "duration_s": om["duration_s"],
                        "stream_url": om["stream_url"],
                        "genre_match_priority": 1,
                        "source": "creatormix_online",
                        "download_command": f"python3 ./.agents/skills/find-music/scripts/fetch_creatormix_catalog.py --search \"{om['title']}\" --download-idx 1",
                    })
                if len(candidates) >= 5:
                    break
        except Exception as e:
            print(f"CreatorMix online catalog check note: {e}")

    candidates.sort(key=lambda x: (x.get("genre_match_priority", 3), x.get("track_title", "")))
    return candidates[:5]


def parse_media_utc(item_info: dict, gpx_points: list) -> dt.datetime:
    """Accurately resolves UTC timestamp of a clip/photo from BleeqUP epoch filename, ISO8601, or EXIF."""
    fname = item_info.get("filename", "")
    m_epoch = re.search(r"(?:VIDEO|IMG)_(\d{13})\b", fname)
    if m_epoch:
        return dt.datetime.fromtimestamp(int(m_epoch.group(1)) / 1000.0, tz=dt.timezone.utc)

    raw = (item_info.get("creation_time_utc") or "").strip()
    if raw:
        # Normalize +0100 -> +01:00 and EXIF YYYY:MM:DD HH:MM:SS -> YYYY-MM-DDTHH:MM:SS
        norm = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", raw.replace("Z", "+00:00"))
        if re.match(r"^\d{4}:\d{2}:\d{2}\s+\d{2}:\d{2}:\d{2}", norm):
            norm = norm[:10].replace(":", "-") + "T" + norm[11:]
        try:
            parsed = dt.datetime.fromisoformat(norm)
            if parsed.tzinfo is None:
                # EXIF local time without tz: infer local offset from GPX date if in Europe/Madrid (+1/+2)
                if gpx_points:
                    gpx_start = gpx_points[0]["time"]
                    # Try +01:00 (CET) or +02:00 (CEST) or UTC, pick whichever lands inside the GPX time window
                    candidates = [
                        parsed.replace(tzinfo=dt.timezone(dt.timedelta(hours=h))).astimezone(dt.timezone.utc)
                        for h in (0, 1, 2, -7, -8)
                    ]
                    return min(candidates, key=lambda c: abs((c - gpx_start).total_seconds()))
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            pass

    return gpx_points[0]["time"] if gpx_points else dt.datetime.now(dt.timezone.utc)


def compute_editorial_guidance(item_info, genre: str, gpx_points: list):
    """Computes phase, duration recommendations, and Imperial/metric telemetry per Music for Video Workflow."""
    if genre == "archival_slideshow":
        return {
            "phase": "Archival_Memory_Slide",
            "highlight_score": 80,
            "recommended_hold_s": 4.0,
            "framing_mode": "Blur_Pillarbox_V2" if item_info["aspect_ratio"] != "16:9_wide" else "Full_Frame_Ken_Burns",
            "recommended_audio_gain_db": -99.0,
            "music_baseline_db": -11.0,
        }

    if genre == "social_event" or not gpx_points:
        is_vid = item_info["media_type"] == "video"
        return {
            "phase": "Story_Scene_Or_Dialogue" if is_vid else "Story_Photo_Highlight",
            "highlight_score": 75,
            "recommended_in_s": 0.0,
            "recommended_out_s": min(item_info["duration_s"], 5.0) if is_vid else 3.5,
            "recommended_audio_gain_db": 0.0 if is_vid else -99.0,
            "music_baseline_db": -15.0 if is_vid else -11.0,
            "music_speech_duck_db": -20.0,
        }

    media_dt = parse_media_utc(item_info, gpx_points)
    nearest = min(gpx_points, key=lambda p: abs((p["time"] - media_dt).total_seconds()))
    # If time is outside GPX window (>30 min) but clip has QuickTime GPS, match spatially
    if abs((nearest["time"] - media_dt).total_seconds()) > 1800 and item_info.get("qt_lat") and item_info.get("qt_lon"):
        nearest = min(
            gpx_points,
            key=lambda p: haversine_m(item_info["qt_lat"], item_info["qt_lon"], p["lat"], p["lon"]),
        )

    # Also compute window peak metrics over the duration of a video clip
    dur_s = float(item_info.get("duration_s") or 0.0)
    clip_window = [
        p for p in gpx_points
        if -1.0 <= (p["time"] - media_dt).total_seconds() <= max(dur_s, 1.0)
    ] or [nearest]

    spd = round(sum(p["speed_kmh"] for p in clip_window) / len(clip_window), 1)
    spd_mph = round(spd * 0.621371, 1)
    max_spd_mph = round(max(p["speed_kmh"] for p in clip_window) * 0.621371, 1)
    grad = round(sum(p["gradient_pct"] for p in clip_window) / len(clip_window), 1)
    max_grad_pct = round(max(clip_window, key=lambda p: abs(p["gradient_pct"]))["gradient_pct"], 1)
    hrs = [p["hr"] for p in clip_window if p.get("hr")]
    hr = int(round(sum(hrs) / len(hrs))) if hrs else (nearest["hr"] or 120)
    max_hr = max(hrs) if hrs else hr
    pwrs = [p["power"] for p in clip_window if p.get("power") is not None]
    pwr = int(round(sum(pwrs) / len(pwrs))) if pwrs else (nearest["power"] or 0)
    # 3-second rolling average power for peak detection so 1-second pedal kicks on flat roads don't trigger Climb/Surge
    if len(pwrs) >= 3:
        max_pwr = max(int(round(sum(pwrs[i:i+3]) / 3.0)) for i in range(len(pwrs) - 2))
    else:
        max_pwr = max(pwrs) if pwrs else 0
    dist_mi = round(nearest["dist_km"] * 0.621371, 2)
    ele_ft = round(nearest["ele"] * 3.28084, 0)

    if genre == "hike_outdoor":
        if spd < 0.8:
            phase = "Summit_Or_Trail_Break"
        elif grad >= 8.0:
            phase = "Steep_Trail_Ascent"
        else:
            phase = "Scenic_Trail_Walk"
        gain_db = -6.0
        music_folder_hint = "02_Scenic_Wonder"
    else:  # cycling_ride
        if spd < 2.5:
            phase = "Cafe_Or_Vista_Stop"
            music_folder_hint = "04_Warm_Social_And_Retro"
        elif grad >= 5.0:
            phase = "Climb_Effort"
            music_folder_hint = "03_Punchy_Climbs"
        elif spd >= 40.0 and grad <= -2.5:
            phase = "High_Speed_Descent"
            music_folder_hint = "03_Punchy_Climbs"
        else:
            phase = "Peloton_Paceline_Cruising"
            music_folder_hint = "01_Rolling_Cadence"
        gain_db = -24.0 if (item_info["source_device"] == "BleeqUP_Ranger_AI" and spd >= 40.0) else -6.0

    rec_in = 0.5 if item_info["source_device"] == "BleeqUP_Ranger_AI" and item_info["duration_s"] > 3.0 else 0.0
    rec_out = max(rec_in + 2.5, min(item_info["duration_s"] - 0.5, rec_in + 4.0))
    score = min(100, int(40 + abs(grad) * 4 + (spd * 0.6) + ((hr - 100) * 0.2) + (pwr * 0.05)))

    is_interesting_telemetry = bool(
        item_info["media_type"] == "video"
        and (max_spd_mph >= 25.0 or abs(max_grad_pct) >= 4.0 or max_pwr >= 220 or max_hr >= 135)
    )

    return {
        "phase": phase,
        "music_folder_hint": music_folder_hint,
        "matched_gpx_utc": nearest["time"].isoformat(),
        "distance_mi": dist_mi,
        "elevation_ft": int(ele_ft),
        "speed_mph": spd_mph,
        "max_speed_mph": max_spd_mph,
        "distance_km": nearest["dist_km"],
        "elevation_m": nearest["ele"],
        "speed_kmh": spd,
        "gradient_pct": grad,
        "max_gradient_pct": max_grad_pct,
        "hr_bpm": nearest["hr"],
        "max_hr_bpm": max_hr,
        "power_w": nearest["power"],
        "max_power_w": max_pwr,
        "lat": nearest["lat"],
        "lon": nearest["lon"],
        "show_telemetry_widget": is_interesting_telemetry,
        "highlight_score": score,
        "recommended_in_s": round(rec_in, 2),
        "recommended_out_s": round(rec_out, 2),
        "recommended_audio_gain_db": gain_db,
        "music_baseline_db": -15.0,
    }


def main():
    parser = argparse.ArgumentParser(description="Universal media, Storyboard.md & telemetry ingestion for Antigravity.")
    parser.add_argument("--project-dir", required=True, help="Path to raw media folder (e.g. ~/Movies/2026/2026-11-01_SaPobla_Market_Trip)")
    parser.add_argument("--genre", default="auto", choices=["auto", "cycling_ride", "hike_outdoor", "social_event", "archival_slideshow"])
    parser.add_argument("--skip-bleequp-sync", action="store_true", help="Skip running ranger-sync if already fixed")
    parser.add_argument("--studio-root", default=str(STUDIO_ROOT), help="Path to Google Drive Antigravity_Video_Studio root")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    studio_root = Path(args.studio_root).expanduser().resolve()
    proxy_dir = project_dir / ".proxies"

    run_filmcraft_version_check(studio_root)
    run_bleequp_ranger_sync_if_needed(project_dir, args.skip_bleequp_sync)
    convert_heic_to_jpg(project_dir)

    gpx_files = list(project_dir.glob("*.gpx")) + list(project_dir.glob("*.GPX"))
    gpx_points, total_km, total_elev_m = ([], 0.0, 0.0)
    if gpx_files:
        gpx_points, total_km, total_elev_m = parse_gpx(gpx_files[0])

    # Avoid duplicating .HEIC files that were just converted to .jpg
    media_items = []
    for f in sorted(project_dir.iterdir()):
        if f.is_file() and f.suffix.lower() in (".mp4", ".mov", ".jpg", ".jpeg", ".tif", ".tiff", ".png") and not f.name.startswith("."):
            media_items.append(probe_media_file(f, proxy_dir))

    genre = detect_genre(args.genre, gpx_points, media_items)
    for item in media_items:
        item["editorial"] = compute_editorial_guidance(item, genre, gpx_points)

    year_match = re.match(r"^(20\d{2}|19\d{2})", project_dir.name)
    year_folder = year_match.group(1) if year_match else str(dt.date.today().year)
    catalog_dir = studio_root / "04_Project_Catalog" / year_folder / project_dir.name
    catalog_dir.mkdir(parents=True, exist_ok=True)

    storyboard_file, storyboard_status = ensure_or_migrate_storyboard(project_dir, catalog_dir, genre, media_items)

    manifest = {
        "project_name": project_dir.name,
        "year_bucket": year_folder,
        "raw_media_folder": str(project_dir),
        "catalog_project_dir": str(catalog_dir),
        "storyboard_file": storyboard_file,
        "storyboard_status": storyboard_status,
        "proxy_thumbnails_dir": str(proxy_dir),
        "detected_genre": genre,
        "gpx_file": gpx_files[0].name if gpx_files else None,
        "music_library_root": str(studio_root / "03_Audio_Library" / "01_Curated_BGM"),
        "recommended_music_candidates": recommend_music_tracks(genre, studio_root),
        "project_summary": {
            "total_distance_mi": round(total_km * 0.621371, 1),
            "total_elevation_gain_ft": int(round(total_elev_m * 3.28084)),
            "total_distance_km": total_km,
            "total_elevation_gain_m": total_elev_m,
            "total_media_files": len(media_items),
            "video_count": sum(1 for m in media_items if m["media_type"] == "video"),
            "still_count": sum(1 for m in media_items if m["media_type"] == "still"),
        },
        "media_inventory": media_items,
    }

    cat_manifest_path = catalog_dir / "project_manifest.json"
    local_manifest_path = project_dir / "project_manifest.json"
    cat_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    local_manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Created {cat_manifest_path} [Genre: {genre} | Storyboard: {storyboard_status}] ({len(media_items)} items).")


if __name__ == "__main__":
    main()
