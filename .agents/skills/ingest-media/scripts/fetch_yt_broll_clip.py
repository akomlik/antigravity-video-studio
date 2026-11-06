#!/usr/bin/env python3
"""
fetch_yt_broll_clip.py
Surgically downloads only a specific timestamp window (e.g., 5-8 seconds)
from an @akomlik YouTube archival video in H.264/MP4 format into ~/Movies/Archival_Pulls/.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Add studio root to sys.path to load studio_config dynamically
_studio_root = Path(__file__).resolve().parents[4]
if str(_studio_root) not in sys.path:
    sys.path.insert(0, str(_studio_root))

try:
    from studio_config import get_archival_pulls_dir
    DEFAULT_ARCHIVAL_DIR = str(get_archival_pulls_dir())
except ImportError:
    DEFAULT_ARCHIVAL_DIR = str(Path.home() / "Movies" / "Archival_Pulls")

os.environ["PATH"] = f"/opt/homebrew/bin:/usr/local/bin:{Path.home() / '.local/bin'}:{os.environ.get('PATH', '')}"


def fetch_clip(video_id: str, start_sec: float, end_sec: float, out_dir: Path, label: str):
    out_dir.mkdir(parents=True, exist_ok=True)
    out_template = str(out_dir / f"YT_{video_id}_{label}_{int(start_sec)}s_{int(end_sec)}s.%(ext)s")
    url = f"https://www.youtube.com/watch?v={video_id}"
    section_arg = f"*{start_sec}-{end_sec}"

    cmd = [
        "yt-dlp",
        "--download-sections", section_arg,
        "--force-keyframes-at-cuts",
        "-f", "bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]",
        "--merge-output-format", "mp4",
        "-o", out_template,
        url
    ]
    subprocess.run(cmd, check=True)
    print(f"Downloaded archival B-roll slice from {url} ({section_arg}) -> {out_dir}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--video-id", required=True, help="YouTube Video ID from youtube_motion_index.jsonl or Storyboard.md")
    p.add_argument("--start", type=float, required=True, help="Start time in seconds")
    p.add_argument("--end", type=float, required=True, help="End time in seconds")
    p.add_argument("--label", default="broll", help="Short descriptive tag (e.g. SJC_Olive_Jacket_2025)")
    p.add_argument("--out-dir", default=DEFAULT_ARCHIVAL_DIR)
    args = p.parse_args()
    fetch_clip(args.video_id, args.start, args.end, Path(args.out_dir).expanduser(), args.label)
