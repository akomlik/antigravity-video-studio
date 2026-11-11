"""
agvs_core/ingest_sync.py
Media discovery, BleeqUP Ranger AI sync integration, ExifTool ISO-8601 UTC + GPS probing,
calibration-clock detection, and non-destructive Storyboard.md synchronization.
"""

from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional, Union
from zoneinfo import ZoneInfo

from ranger_sync.models import MediaKind
from ranger_sync.parser import classify_filename

from agvs_core.config import STUDIO_ROOT, find_binary

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
        # Preserve catalog Storyboard.md unless raw_sb is both strictly newer AND at least as complete
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
