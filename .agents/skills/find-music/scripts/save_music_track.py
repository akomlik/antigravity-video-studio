#!/usr/bin/env python3
"""
save_music_track.py
Watches or grabs the latest downloaded MP3/WAV/M4A from ~/Downloads (or a specified file path),
renames it to the standardized [BPM]_[Mood]_[TrackName]_[Artist].mp3 taxonomy from
"Music for Video Workflow", moves it into ~/Music/Cycling_BGM/<category>/ (which syncs to
Google Drive 03_Audio_Library/01_Curated_BGM/<category>/), and logs it in music_catalog.json.
"""

import argparse
import datetime as dt
import json
import re
import shutil
from pathlib import Path

CYCLING_BGM_ROOT = Path("~/Music/Cycling_BGM").expanduser()
DOWNLOADS_DIR = Path("~/Downloads").expanduser()

CATEGORIES = [
    "01_Rolling_Cadence",
    "02_Scenic_Wonder",
    "03_Punchy_Climbs",
    "04_Warm_Social_And_Retro",
    "05_Short_Transitions",
]


def camel_clean(text: str) -> str:
    """Converts 'Circuit Rush - The Mini Vandals' or 'circuit_rush' into 'CircuitRush'."""
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "".join(w.capitalize() for w in words) or "Untitled"


def find_latest_download(downloads_dir: Path, since_minutes: int = 30) -> Path:
    cutoff = dt.datetime.now().timestamp() - (since_minutes * 60)
    candidates = [
        f for f in downloads_dir.iterdir()
        if f.is_file()
        and f.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac")
        and not f.name.startswith(".")
        and f.stat().st_mtime >= cutoff
    ]
    if not candidates:
        raise FileNotFoundError(f"No recent audio files (.mp3/.wav/.m4a) found in {downloads_dir} from the last {since_minutes} minutes.")
    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return candidates[0]


def main():
    p = argparse.ArgumentParser(description="Auto-rename and save downloaded YouTube Audio Library / CreatorMix track into ~/Music/Cycling_BGM/")
    p.add_argument("--source", default="latest", help="Path to downloaded file, or 'latest' to grab newest audio file in ~/Downloads")
    p.add_argument("--bpm", type=int, required=True, help="Track BPM (e.g. 118)")
    p.add_argument("--mood", required=True, help="Short mood descriptor (e.g. ChillBeat, AmbientWonder, DrivingEnergy, WarmAcoustic)")
    p.add_argument("--title", required=True, help="Track title (e.g. 'Circuit Rush')")
    p.add_argument("--artist", required=True, help="Artist or source (e.g. 'The Mini Vandals' or 'CreatorMix')")
    p.add_argument("--category", choices=CATEGORIES, required=True, help="Target mood folder inside ~/Music/Cycling_BGM/")
    p.add_argument("--source-site", choices=["YouTube_Audio_Library", "CreatorMix", "Other"], default="CreatorMix")
    p.add_argument("--notes", default="", help="Optional notes on what video scenes this track fits best")
    args = p.parse_args()

    src_path = find_latest_download(DOWNLOADS_DIR) if args.source == "latest" else Path(args.source).expanduser().resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"Source audio file not found: {src_path}")

    ext = src_path.suffix.lower()
    mood_clean = camel_clean(args.mood)
    title_clean = camel_clean(args.title)
    artist_clean = camel_clean(args.artist)

    new_filename = f"{args.bpm:03d}bpm_{mood_clean}_{title_clean}_{artist_clean}{ext}"
    dest_dir = CYCLING_BGM_ROOT / args.category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / new_filename

    shutil.move(str(src_path), str(dest_path))

    # Update music_catalog.json index
    catalog_json = CYCLING_BGM_ROOT / "music_catalog.json"
    catalog = {"tracks": []}
    if catalog_json.exists():
        try:
            catalog = json.loads(catalog_json.read_text(encoding="utf-8"))
        except Exception:
            catalog = {"tracks": []}

    entry = {
        "filename": new_filename,
        "abspath": str(dest_path.resolve()),
        "category": args.category,
        "bpm": args.bpm,
        "beat_interval_s": round(60.0 / max(args.bpm, 1), 3),
        "mood": mood_clean,
        "title": args.title,
        "artist": args.artist,
        "source_site": args.source_site,
        "notes": args.notes,
        "saved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    catalog["tracks"] = [t for t in catalog.get("tracks", []) if t.get("filename") != new_filename]
    catalog["tracks"].append(entry)
    catalog_json.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"Saved & indexed track -> {dest_path}")


if __name__ == "__main__":
    main()
