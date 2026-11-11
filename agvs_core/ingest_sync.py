"""
agvs_core/ingest_sync.py
Media discovery, BleeqUP Ranger AI sync integration, HEIC->JPEG upright bake,
ExifTool ISO-8601 UTC + GPS probing, calibration-clock detection,
non-destructive Storyboard.md synchronization, and manifest generation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from ranger_sync.models import MediaKind
from ranger_sync.parser import classify_filename

from agvs_core.config import STUDIO_ROOT, find_binary, get_studio_root
from agvs_core.telemetry_gpx import haversine_m, parse_gpx_with_summary, select_primary_ride_gpx

_CALIBRATION_FILENAME_PATTERNS = ("bigclock", "clock_sync", "calib", "time_sync")


def has_bleequp_files(project_dir: Path) -> bool:
    """Detects BleeqUP Ranger AI media using `ranger_sync.parser.classify_filename` (Epoch 1.8B+ safe)."""
    if not project_dir.exists():
        return False
    for entry in project_dir.iterdir():
        if not entry.is_file() or entry.name.startswith("."):
            continue
        res = classify_filename(entry.name)
        if res is not None and res[0] in (
            MediaKind.BLEEQUP_PHOTO,
            MediaKind.BLEEQUP_VIDEO,
            MediaKind.BLEEQUP_AI_MOTION,
            MediaKind.BLEEQUP_AI_VIDEO,
        ):
            return True
    return False


def is_bleequp_filename(filename: str) -> bool:
    """True when `filename` matches a BleeqUP raw or AI filename pattern (13-digit epoch safe across 2027+)."""
    res = classify_filename(filename)
    return res is not None and res[0] != MediaKind.REFERENCE_IPHONE


def is_calibration_clock_filename(filename: str, extra_calibration_files: Optional[set[str]] = None) -> bool:
    """Detects clock-sync reference photos (e.g. bigclock.app shots or explicit `--mark-calibration` files)."""
    low = filename.lower()
    if extra_calibration_files and low in {f.lower() for f in extra_calibration_files}:
        return True
    return any(pat in low for pat in _CALIBRATION_FILENAME_PATTERNS)


def parse_iso6709(iso_str: str) -> tuple[Optional[float], Optional[float]]:
    """Parses Apple QuickTime ISO6709 location string (e.g. '+39.7707+003.0230+028.000/') into (lat, lon)."""
    if not iso_str:
        return None, None
    m = re.match(r"^([+-]\d+\.\d+)([+-]\d+\.\d+)", iso_str.strip())
    if m:
        return round(float(m.group(1)), 5), round(float(m.group(2)), 5)
    return None, None


def parse_media_utc(
    item_or_str: Union[dict[str, Any], str, None],
    gpx_points: Optional[list[dict[str, Any]]] = None,
) -> Optional[dt.datetime]:
    """
    Parses either a manifest item dict or raw timestamp string into a timezone-aware UTC `datetime`.
    Handles ISO-8601 (`Z`, `+0100`, `+01:00`), EXIF (`YYYY:MM:DD HH:MM:SS`), and BleeqUP 13-digit epochs.
    """
    if item_or_str is None:
        return gpx_points[0]["time"] if gpx_points else None

    if isinstance(item_or_str, str):
        fname = ""
        raw = item_or_str.strip()
    else:
        fname = str(item_or_str.get("filename") or "")
        raw = str(item_or_str.get("creation_time_utc") or "").strip()

    m_epoch = re.search(r"(?:VIDEO|IMG)_(\d{13})\b", fname, re.IGNORECASE)
    epoch_dt = (
        dt.datetime.fromtimestamp(int(m_epoch.group(1)) / 1000.0, tz=dt.timezone.utc)
        if m_epoch
        else None
    )

    if raw:
        norm = re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", raw.replace("Z", "+00:00"))
        if re.match(r"^\d{4}:\d{2}:\d{2}\s+\d{2}:\d{2}:\d{2}", norm):
            norm = norm[:10].replace(":", "-") + "T" + norm[11:]
        try:
            parsed = dt.datetime.fromisoformat(norm)
            if parsed.tzinfo is None:
                if gpx_points:
                    lat0, lon0 = gpx_points[0]["lat"], gpx_points[0]["lon"]
                    if 35.0 <= lat0 <= 45.0 and -10.0 <= lon0 <= 15.0:
                        return parsed.replace(tzinfo=ZoneInfo("Europe/Madrid")).astimezone(dt.timezone.utc)
                    if 32.0 <= lat0 <= 42.0 and -125.0 <= lon0 <= -114.0:
                        return parsed.replace(tzinfo=ZoneInfo("America/Los_Angeles")).astimezone(dt.timezone.utc)
                return parsed.replace(tzinfo=dt.timezone.utc)
            return parsed.astimezone(dt.timezone.utc)
        except ValueError:
            pass

    if epoch_dt is not None:
        return epoch_dt
    if gpx_points:
        return gpx_points[0]["time"]
    return None if isinstance(item_or_str, str) else dt.datetime.now(dt.timezone.utc)


def probe_still_exif(filepath: Path) -> dict[str, Any]:
    """Probes still-photo width, height, ISO-8601 UTC timestamp, camera TZ offset, and GPS via ExifTool (with sips fallback)."""
    result: dict[str, Any] = {
        "width": 0,
        "height": 0,
        "creation_time_utc": None,
        "camera_tz_offset": None,
        "qt_lat": None,
        "qt_lon": None,
    }
    exiftool_bin = find_binary("exiftool", required=False)
    if exiftool_bin:
        proc = subprocess.run(
            [
                exiftool_bin,
                "-json",
                "-n",
                "-ImageWidth",
                "-ImageHeight",
                "-SubSecDateTimeOriginal",
                "-DateTimeOriginal",
                "-OffsetTimeOriginal",
                "-CreateDate",
                "-GPSLatitude",
                "-GPSLongitude",
                str(filepath),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            try:
                meta = json.loads(proc.stdout)[0]
                result["width"] = int(meta.get("ImageWidth") or 0)
                result["height"] = int(meta.get("ImageHeight") or 0)
                lat, lon = meta.get("GPSLatitude"), meta.get("GPSLongitude")
                if isinstance(lat, (int, float)) and isinstance(lon, (int, float)):
                    result["qt_lat"] = round(float(lat), 5)
                    result["qt_lon"] = round(float(lon), 5)
                tz_off = str(meta.get("OffsetTimeOriginal") or "").strip()
                if tz_off:
                    result["camera_tz_offset"] = tz_off
                raw_dt = (
                    meta.get("SubSecDateTimeOriginal")
                    or meta.get("DateTimeOriginal")
                    or meta.get("CreateDate")
                )
                if raw_dt:
                    s_dt = str(raw_dt).strip()
                    if tz_off and not re.search(r"(Z|[+-]\d{2}:?\d{2})$", s_dt):
                        s_dt = f"{s_dt}{tz_off}"
                    dt_utc = parse_media_utc(s_dt)
                    if dt_utc is not None:
                        result["creation_time_utc"] = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                pass

    if not result["width"] or not result["height"]:
        sips_bin = find_binary("sips", required=False)
        if sips_bin:
            proc = subprocess.run(
                [sips_bin, "-g", "pixelWidth", "-g", "pixelHeight", "-g", "creation", str(filepath)],
                capture_output=True,
                text=True,
                check=False,
            )
            for line in proc.stdout.splitlines():
                if "pixelWidth:" in line:
                    result["width"] = int(line.split(":")[-1].strip())
                elif "pixelHeight:" in line:
                    result["height"] = int(line.split(":")[-1].strip())
                elif "creation:" in line and not result["creation_time_utc"]:
                    raw_c = line.split("creation:")[-1].strip()
                    if raw_c and raw_c != "<nil>":
                        dt_utc = parse_media_utc(raw_c)
                        if dt_utc is not None:
                            result["creation_time_utc"] = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    return result


def classify_video_source_device(filepath: Path, width: int, height: int, format_tags: dict[str, Any]) -> str:
    """Classifies video source device without mislabeling generic 1080p AI/YouTube MP4s as BleeqUP."""
    make = (
        str(format_tags.get("com.apple.quicktime.make") or "")
        + " "
        + str(format_tags.get("encoder") or "")
    ).lower()
    if "apple" in make or filepath.suffix.lower() == ".mov":
        return "iPhone_15_Pro"
    if "bleequp" in make or is_bleequp_filename(filepath.name) or (width, height) in (
        (2880, 1620),
        (1620, 2880),
        (3200, 1800),
        (1800, 3200),
    ):
        return "BleeqUP_Ranger_AI"
    return "unknown"


def sync_storyboard_non_destructive(
    project_dir: Path,
    catalog_dir: Path,
    genre: str = "cycling_ride",
    media_items: Optional[list[dict[str, Any]]] = None,
) -> tuple[str, str]:
    """
    Synchronizes `Storyboard.md` between `project_dir` and `catalog_dir` non-destructively:
    - Never overwrites a rich/newer `catalog_dir/Storyboard.md` with a stale stub from `project_dir`!
    - Back-syncs `catalog_dir/Storyboard.md` -> `project_dir/Storyboard.md` when the catalog copy is authoritative.
    """
    catalog_dir.mkdir(parents=True, exist_ok=True)
    raw_sb = project_dir / "Storyboard.md"
    cat_sb = catalog_dir / "Storyboard.md"

    if cat_sb.exists():
        if not raw_sb.exists():
            shutil.copy2(cat_sb, raw_sb)
            return "Storyboard.md", "existing_catalog"
        cat_stat = cat_sb.stat()
        raw_stat = raw_sb.stat()
        if cat_stat.st_size >= raw_stat.st_size or cat_stat.st_mtime >= raw_stat.st_mtime:
            if cat_sb.read_bytes() != raw_sb.read_bytes():
                shutil.copy2(cat_sb, raw_sb)
            return "Storyboard.md", "preserved_catalog"
        shutil.copy2(raw_sb, cat_sb)
        return "Storyboard.md", "updated_from_raw"

    status = "existing"
    if not raw_sb.exists():
        status = "created_skeleton_needs_refinement"
        items = media_items or []
        lines = [
            f"# Storyboard: {project_dir.name}",
            f"- **Detected Genre:** `{genre}`",
            f"- **Total Media Files:** {len(items)}",
            "- **Status:** `DRAFT — Awaiting AI Visual Inspection & User Story Refinement`",
            "",
            "## 1. Story Premise & Highlights",
            "- *[Add story notes or refine interactively via `/storyboard`]*",
            "",
            "## 2. Scene-by-Scene Storyboard (`Scene 00` -> `Scene N`)",
            "- **Scene 01 (Opening):** *[Pending visual inspection]*",
            "",
            "## 3. Chronological Media & GPS Log",
        ]
        for m in items:
            gps_str = f" (GPS: {m['qt_lat']}, {m['qt_lon']})" if m.get("qt_lat") else ""
            dur_str = f" [{m.get('duration_s', 0)}s]" if m.get("media_type") == "video" else " [Still]"
            lines.append(f"- `{m['filename']}` — `{m.get('creation_time_utc')}`{dur_str}{gps_str}")
        raw_sb.write_text("\n".join(lines) + "\n", encoding="utf-8")

    shutil.copy2(raw_sb, cat_sb)
    return "Storyboard.md", status


def convert_heic_to_jpg(project_dir: Path) -> None:
    """Converts iPhone .HEIC stills to .jpg, bakes upright pixel orientation (Orientation=1), and preserves EXIF dates."""
    exiftool_bin = find_binary("exiftool", required=False)
    sips_bin = find_binary("sips", required=False) or "sips"

    for heic in list(project_dir.glob("*.HEIC")) + list(project_dir.glob("*.heic")):
        jpg_out = heic.with_suffix(".jpg")
        needs_exif_sync = False
        if not jpg_out.exists():
            subprocess.run(
                [sips_bin, "-s", "format", "jpeg", "-s", "formatOptions", "95", str(heic), "--out", str(jpg_out)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            needs_exif_sync = True
        elif abs(jpg_out.stat().st_mtime - heic.stat().st_mtime) > 2.0:
            needs_exif_sync = True

        if needs_exif_sync and jpg_out.exists() and exiftool_bin:
            subprocess.run(
                [exiftool_bin, "-overwrite_original", "-tagsFromFile", str(heic), "-all:all", str(jpg_out)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    try:
        from PIL import Image, ImageOps

        for jpg_p in list(project_dir.glob("*.jpg")) + list(project_dir.glob("*.JPG")):
            if jpg_p.is_symlink():
                continue
            with Image.open(jpg_p) as im:
                ori = im.getexif().get(274, 1)
                if ori != 1:
                    st = jpg_p.stat()
                    upright = ImageOps.exif_transpose(im)
                    exif_bytes = upright.info.get("exif")
                    save_kw: dict[str, Any] = {"quality": 95, "subsampling": 0}
                    if exif_bytes:
                        save_kw["exif"] = exif_bytes
                    upright.save(jpg_p, "JPEG", **save_kw)
                    if exiftool_bin:
                        subprocess.run(
                            [exiftool_bin, "-overwrite_original", "-Orientation=1", "-n", str(jpg_p)],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    os.utime(jpg_p, (st.st_atime, st.st_mtime))
                    print(f"[✓] Baked upright pixel orientation on {jpg_p.name} (was EXIF Orientation={ori})")
    except Exception as exc:
        print(f"Note: EXIF orientation check warning: {exc}")

    if exiftool_bin:
        for heic in list(project_dir.glob("*.HEIC")) + list(project_dir.glob("*.heic")):
            jpg_out = heic.with_suffix(".jpg")
            if jpg_out.exists() and abs(jpg_out.stat().st_mtime - heic.stat().st_mtime) > 2.0:
                subprocess.run(
                    [
                        exiftool_bin,
                        "-overwrite_original",
                        "-FileCreateDate<DateTimeOriginal",
                        "-FileModifyDate<DateTimeOriginal",
                        str(jpg_out),
                    ],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


def run_bleequp_ranger_sync_if_needed(project_dir: Path, skip_sync: bool, force_resync: bool = False) -> None:
    """Runs `ranger-sync apply --auto-shift --rename-shifted --write-filesystem` when BleeqUP media is present."""
    if skip_sync:
        print("Skipping ranger-sync (--skip-bleequp-sync flag set; files already fixed).")
        return
    marker = project_dir / ".bleequp_synced"
    if marker.exists() and not force_resync:
        print("Detected .bleequp_synced marker; BleeqUP media already processed.")
        return
    if not has_bleequp_files(project_dir):
        return
    sync_bin = find_binary("ranger-sync", required=False) or find_binary("bleequp-ranger-sync", required=False)
    if sync_bin:
        print(f"Step 0b: Running {sync_bin} apply --auto-shift --rename-shifted --write-filesystem on {project_dir}...")
        res = subprocess.run(
            [
                sync_bin,
                "apply",
                str(project_dir),
                "--auto-shift",
                "--rename-shifted",
                "--write-filesystem",
                "--overwrite-original",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.stdout:
            print(res.stdout, end="")
        if res.returncode == 0:
            marker.touch()
        else:
            if res.stderr:
                print(res.stderr, file=sys.stderr, end="")
            raise RuntimeError(
                f"ranger-sync failed with exit code {res.returncode} — aborting ingest to prevent out-of-order timeline."
            )
    else:
        print("Note: ranger-sync not on PATH; proceeding with existing files.")


def generate_video_proxy_thumb(video_path: Path, proxy_dir: Path, duration_s: float) -> Optional[str]:
    """Extracts a lightweight 640px JPEG thumbnail at 25% into the clip AND a 3x2 contact strip for clips >= 10s."""
    proxy_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = proxy_dir / f"{video_path.stem}_thumb.jpg"
    strip_path = proxy_dir / f"{video_path.stem}_strip.jpg"
    ffmpeg_bin = find_binary("ffmpeg", required=False)

    if not thumb_path.exists():
        if ffmpeg_bin:
            seek_s = max(0.0, round(duration_s * 0.25, 2))
            subprocess.run(
                [
                    ffmpeg_bin,
                    "-y",
                    "-ss",
                    str(seek_s),
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=640:-1",
                    "-q:v",
                    "4",
                    str(thumb_path),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.run(
                ["qlmanage", "-t", "-s", "640", "-o", str(proxy_dir), str(video_path)],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            ql_png = proxy_dir / f"{video_path.name}.png"
            if ql_png.exists():
                subprocess.run(
                    ["sips", "-s", "format", "jpeg", str(ql_png), "--out", str(thumb_path)],
                    check=False,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                ql_png.unlink(missing_ok=True)

    if duration_s >= 10.0 and not strip_path.exists() and ffmpeg_bin:
        interval = max(1.5, round(duration_s / 6.2, 2))
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(video_path),
                "-vf",
                f"fps=1/{interval},scale=480:-1,tile=3x2",
                "-frames:v",
                "1",
                "-q:v",
                "4",
                str(strip_path),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    return f".proxies/{thumb_path.name}" if thumb_path.exists() else None


def probe_media_file(filepath: Path, proxy_dir: Path) -> dict[str, Any]:
    """Extracts resolution, aspect ratio, fps, duration, codec, QuickTime GPS, and creation timestamp."""
    ext = filepath.suffix.lower()
    info: dict[str, Any] = {
        "filename": filepath.name,
        "relpath": filepath.name,
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
        ffprobe_bin = find_binary("ffprobe", required=False)
        if ffprobe_bin:
            cmd = [ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(filepath)]
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
                        r_fps = str(s.get("r_frame_rate", "30/1")).split("/")
                        info["fps"] = round(float(r_fps[0]) / max(float(r_fps[1]) if len(r_fps) > 1 else 1.0, 1.0), 2)
                        trc = str(s.get("color_transfer", ""))
                        if "arib-std-b67" in trc or "smpte2084" in trc:
                            info["color_space"] = "BT.2020_HDR"
                        break

                info["source_device"] = classify_video_source_device(filepath, info["width"], info["height"], tags)
                ctime = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
                if ctime:
                    dt_utc = parse_media_utc(str(ctime))
                    info["creation_time_utc"] = dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ") if dt_utc else str(ctime)
                loc_iso = tags.get("com.apple.quicktime.location.ISO6709") or tags.get("location")
                if loc_iso:
                    info["qt_lat"], info["qt_lon"] = parse_iso6709(str(loc_iso))
        info["proxy_thumb"] = generate_video_proxy_thumb(filepath, proxy_dir, info["duration_s"])
    else:
        still_meta = probe_still_exif(filepath)
        info["width"] = still_meta["width"]
        info["height"] = still_meta["height"]
        info["creation_time_utc"] = still_meta["creation_time_utc"]
        if still_meta.get("camera_tz_offset"):
            info["camera_tz_offset"] = still_meta["camera_tz_offset"]
        if still_meta.get("qt_lat") is not None:
            info["qt_lat"] = still_meta["qt_lat"]
            info["qt_lon"] = still_meta["qt_lon"]
        if (info["width"], info["height"]) in ((4656, 3496), (3496, 4656)) or is_bleequp_filename(filepath.name):
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
        info["creation_time_utc"] = mtime.strftime("%Y-%m-%dT%H:%M:%SZ")

    if is_calibration_clock_filename(filepath.name):
        info["calibration_clock_only"] = True
        info["exclude_from_timeline"] = True

    return info


def detect_genre(requested_genre: str, gpx_points: list[dict[str, Any]], media_items: list[dict[str, Any]]) -> str:
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


def compute_editorial_guidance(item_info: dict[str, Any], genre: str, gpx_points: list[dict[str, Any]]) -> dict[str, Any]:
    """Computes phase, duration recommendations, and Imperial/metric telemetry."""
    if genre == "archival_slideshow":
        return {
            "phase": "Archival_Memory_Slide",
            "highlight_score": 80,
            "recommended_hold_s": 4.0,
            "framing_mode": "Blur_Pillarbox_V2" if item_info["aspect_ratio"] != "16:9_wide" else "Full_Frame_Ken_Burns",
            "recommended_audio_gain_db": -99.0,
            "music_baseline_db": -16.0,
        }

    if genre == "social_event" or not gpx_points:
        is_vid = item_info["media_type"] == "video"
        return {
            "phase": "Story_Scene_Or_Dialogue" if is_vid else "Story_Photo_Highlight",
            "highlight_score": 75,
            "recommended_in_s": 0.0,
            "recommended_out_s": min(item_info["duration_s"], 5.0) if is_vid else 3.5,
            "recommended_audio_gain_db": 0.0 if is_vid else -99.0,
            "music_baseline_db": -17.5 if is_vid else -16.0,
            "music_speech_duck_db": -24.0,
        }

    media_dt = parse_media_utc(item_info, gpx_points) or gpx_points[0]["time"]
    in_gpx_ride_window = bool(
        gpx_points[0]["time"] - dt.timedelta(seconds=120)
        <= media_dt
        <= gpx_points[-1]["time"] + dt.timedelta(seconds=120)
    )
    nearest = min(gpx_points, key=lambda p: abs((p["time"] - media_dt).total_seconds()))
    if abs((nearest["time"] - media_dt).total_seconds()) > 1800 and item_info.get("qt_lat") and item_info.get("qt_lon"):
        nearest = min(
            gpx_points,
            key=lambda p: haversine_m(item_info["qt_lat"], item_info["qt_lon"], p["lat"], p["lon"]),
        )
    gpx_spatial_error_m = None
    if in_gpx_ride_window and item_info.get("qt_lat") is not None and item_info.get("qt_lon") is not None:
        gpx_spatial_error_m = round(
            haversine_m(item_info["qt_lat"], item_info["qt_lon"], nearest["lat"], nearest["lon"]), 1
        )

    dur_s = float(item_info.get("duration_s") or 0.0)
    clip_window = [p for p in gpx_points if -1.0 <= (p["time"] - media_dt).total_seconds() <= max(dur_s, 1.0)] or [nearest]

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
    if len(pwrs) >= 3:
        max_pwr = max(int(round(sum(pwrs[i : i + 3]) / 3.0)) for i in range(len(pwrs) - 2))
    else:
        max_pwr = max(pwrs) if pwrs else 0
    dist_mi = round(nearest["dist_km"] * 0.621371, 2)
    ele_ft = round(nearest["ele"] * 3.28084, 0)

    if genre == "hike_outdoor":
        phase = "Summit_Or_Trail_Break" if spd < 0.8 else ("Steep_Trail_Ascent" if grad >= 8.0 else "Scenic_Trail_Walk")
        gain_db = -6.0
        music_folder_hint = "02_Scenic_Wonder"
    else:
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
        and (max_spd_mph >= 25.0 or abs(max_grad_pct) >= 4.0 or max_pwr >= 150 or max_hr >= 135)
    )

    return {
        "phase": phase,
        "music_folder_hint": music_folder_hint,
        "matched_gpx_utc": nearest["time"].isoformat(),
        "in_gpx_ride_window": in_gpx_ride_window,
        "gpx_spatial_error_m": gpx_spatial_error_m,
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
        "music_baseline_db": -17.5,
    }


def verify_and_refine_bleequp_stop_sync(
    project_dir: Path,
    gpx_points: list[dict[str, Any]],
    media_items: list[dict[str, Any]],
    proxy_dir: Path,
) -> bool:
    """Uses Gemini Vision on contact strips around GPX stationary stops to catch subtle 10-300s RTC drift."""
    if not gpx_points or len(gpx_points) < 20 or not os.environ.get("GEMINI_API_KEY"):
        return False
    sync_bin = find_binary("ranger-sync", required=False) or find_binary("bleequp-ranger-sync", required=False)
    if not sync_bin:
        return False

    stops = []
    for i in range(len(gpx_points) - 1):
        pa, pb = gpx_points[i], gpx_points[i + 1]
        gap_s = (pb["time"] - pa["time"]).total_seconds()
        if gap_s >= 180.0 and haversine_m(pa["lat"], pa["lon"], pb["lat"], pb["lon"]) <= 150.0:
            stops.append((pa["time"].timestamp(), pb["time"].timestamp()))
    if not stops:
        return False

    stop_start, stop_end = stops[0]
    candidates = []
    for m in media_items:
        if m.get("source_device") != "BleeqUP_Ranger_AI" or m.get("media_type") != "video":
            continue
        ts_dt = parse_media_utc(m, gpx_points)
        if not ts_dt:
            continue
        ts = ts_dt.timestamp()
        if stop_start - 180.0 <= ts <= stop_start + 60.0 and m.get("duration_s", 0) >= 15.0:
            candidates.append((ts, m))
    if not candidates:
        return False

    candidates.sort(key=lambda x: abs((x[0] + x[1]["duration_s"] * 0.4) - stop_start))
    cand_ts, cand_m = candidates[0]
    strip_file = proxy_dir / f"{Path(cand_m['filename']).stem}_strip.jpg"
    if not strip_file.exists():
        return False

    try:
        from google import genai
        from PIL import Image
        from agvs_core.ai_creative import _generate_vision_content

        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        dur = cand_m["duration_s"]
        prompt = (
            f"This 3x2 contact sheet shows 6 evenly spaced frames across a {dur:.1f}-second cycling POV video. "
            f"Does this clip show the cyclist riding and then arriving/stopping at a cafe or building entrance? "
            f'Return ONLY valid JSON: {{"arrives_at_stop": true/false, "stop_second": number}}'
        )
        resp = _generate_vision_content(client, [Image.open(strip_file), prompt], json_mode=True)
        data = json.loads((resp.text or "{}").strip())
        if data.get("arrives_at_stop") and isinstance(data.get("stop_second"), (int, float)):
            residual_s = round(stop_start - (cand_ts + float(data["stop_second"])))
            if 10 <= abs(residual_s) <= 300:
                pre_files = []
                for m in media_items:
                    if not is_bleequp_filename(m["filename"]):
                        continue
                    t_dt = parse_media_utc(m, gpx_points)
                    if t_dt and t_dt.timestamp() <= stop_end - 300.0:
                        pre_files.append(m["filename"])
                if pre_files:
                    spec = f"{','.join(pre_files)}:{residual_s:+d}s"
                    subprocess.run(
                        [
                            sync_bin,
                            "apply",
                            str(project_dir),
                            "--shift-files",
                            spec,
                            "--rename-shifted",
                            "--write-filesystem",
                            "--overwrite-original",
                        ],
                        check=False,
                    )
                    return True
    except Exception as exc:
        print(f"Note: AI stop-sync check skipped ({exc})")
    return False


def ingest_project_media(
    project_dir: Path,
    genre: str = "auto",
    skip_bleequp_sync: bool = False,
    force_resync: bool = False,
    mark_calibration: Optional[list[str]] = None,
    studio_root: Optional[Path] = None,
) -> dict[str, Any]:
    """Full Stage 0 media pre-processor: HEIC->JPG, ranger-sync, GPX telemetry, Storyboard sync, and manifest creation."""
    p_dir = project_dir.expanduser().resolve()
    root = (studio_root or get_studio_root()).expanduser().resolve()
    proxy_dir = p_dir / ".proxies"

    try:
        from agvs_core.filmcraft_env import verify_filmcraft_environment

        verify_filmcraft_environment(auto_sync_cli=True, check_remote=False)
    except Exception as exc:
        print(f"FilmCraft check warning: {exc}")

    convert_heic_to_jpg(p_dir)
    run_bleequp_ranger_sync_if_needed(p_dir, skip_bleequp_sync, force_resync)

    primary_gpx, archival_gpx = select_primary_ride_gpx(p_dir, project_name=p_dir.name)
    gpx_files = ([primary_gpx] + archival_gpx) if primary_gpx else []
    gpx_points, total_km, total_elev_m = parse_gpx_with_summary(primary_gpx) if primary_gpx else ([], 0.0, 0.0)

    def _is_raw_capture(f: Path) -> bool:
        if not f.is_file() or f.name.startswith("."):
            return False
        if f.suffix.lower() not in (".mp4", ".mov", ".jpg", ".jpeg", ".tif", ".tiff", ".png"):
            return False
        if f.name.startswith(("bookend_intro_", "bookend_outro_")) or "_spotlight_4K" in f.name:
            return False
        return True

    media_items = [probe_media_file(f, proxy_dir) for f in sorted(p_dir.iterdir()) if _is_raw_capture(f)]
    if not skip_bleequp_sync and verify_and_refine_bleequp_stop_sync(p_dir, gpx_points, media_items, proxy_dir):
        media_items = [probe_media_file(f, proxy_dir) for f in sorted(p_dir.iterdir()) if _is_raw_capture(f)]

    detected_genre = detect_genre(genre, gpx_points, media_items)
    calib_set = {Path(x).name.lower() for x in (mark_calibration or [])}
    for item in media_items:
        if item["filename"].lower() in calib_set:
            item["calibration_clock_only"] = True
            item["exclude_from_timeline"] = True
        item["editorial"] = compute_editorial_guidance(item, detected_genre, gpx_points)

    media_items.sort(key=lambda m: ((parse_media_utc(m, gpx_points) or dt.datetime.min.replace(tzinfo=dt.timezone.utc)).timestamp(), m.get("filename", "")))

    year_match = re.match(r"^(20\d{2}|19\d{2})", p_dir.name)
    year_folder = year_match.group(1) if year_match else str(dt.date.today().year)
    catalog_dir = root / "04_Project_Catalog" / year_folder / p_dir.name
    catalog_dir.mkdir(parents=True, exist_ok=True)

    cat_manifest_path = catalog_dir / "project_manifest.json"
    if cat_manifest_path.exists():
        try:
            old_manifest = json.loads(cat_manifest_path.read_text(encoding="utf-8"))
            old_by_name = {m.get("filename", "").lower(): m for m in (old_manifest.get("media_inventory") or [])}
            for item in media_items:
                prev = old_by_name.get(item.get("filename", "").lower())
                if prev:
                    if "sub_clips" in prev and "subclips" not in prev:
                        prev["subclips"] = prev.pop("sub_clips")
                    for preserve_key in (
                        "subclips",
                        "landmarks",
                        "visual_summary",
                        "subclip_indexed_at",
                        "exclude_from_timeline",
                        "calibration_clock_only",
                    ):
                        if preserve_key in prev and preserve_key not in item:
                            item[preserve_key] = prev[preserve_key]
        except Exception:
            pass

    storyboard_file, storyboard_status = sync_storyboard_non_destructive(
        p_dir, catalog_dir, genre=detected_genre, media_items=media_items
    )

    from agvs_core.music_catalog import recommend_music_tracks

    manifest: dict[str, Any] = {
        "project_name": p_dir.name,
        "year_bucket": year_folder,
        "raw_media_folder": f"{year_folder}/{p_dir.name}",
        "catalog_project_dir": f"04_Project_Catalog/{year_folder}/{p_dir.name}",
        "storyboard_file": storyboard_file,
        "storyboard_status": storyboard_status,
        "proxy_thumbnails_dir": ".proxies",
        "detected_genre": detected_genre,
        "gpx_file": gpx_files[0].name if gpx_files else None,
        "archival_gpx_files": [g.name for g in archival_gpx],
        "music_library_root": "03_Audio_Library/01_Curated_BGM",
        "recommended_music_candidates": recommend_music_tracks(detected_genre, studio_root=root, allow_online_probe=False),
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

    serialized = json.dumps(manifest, indent=2, ensure_ascii=False)
    cat_manifest_path.write_text(serialized, encoding="utf-8")
    (p_dir / "project_manifest.json").write_text(serialized, encoding="utf-8")
    print(f"Created {cat_manifest_path} [Genre: {detected_genre} | Storyboard: {storyboard_status}] ({len(media_items)} items).")

    try:
        from agvs_core.ai_creative import process_project_subclips

        process_project_subclips(p_dir, studio_root=root)
    except Exception as exc:
        print(f"Note: Subclip indexing skipped ({exc})")

    return manifest


def ingest_cli_main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Universal media, Storyboard.md & telemetry ingestion for Antigravity.")
    parser.add_argument("--project-dir", required=True, help="Path to raw media folder")
    parser.add_argument("--genre", default="auto", choices=["auto", "cycling_ride", "hike_outdoor", "social_event", "archival_slideshow"])
    parser.add_argument("--skip-bleequp-sync", action="store_true")
    parser.add_argument("--force-resync", action="store_true")
    parser.add_argument("--mark-calibration", nargs="*", default=[])
    parser.add_argument("--studio-root", default=str(STUDIO_ROOT))
    args = parser.parse_args(argv)

    ingest_project_media(
        project_dir=Path(args.project_dir),
        genre=args.genre,
        skip_bleequp_sync=args.skip_bleequp_sync,
        force_resync=args.force_resync,
        mark_calibration=args.mark_calibration,
        studio_root=Path(args.studio_root),
    )
