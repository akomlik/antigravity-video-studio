#!/usr/bin/env python3
"""
extract_facebook_stills.py
Extracts 4–6 high-resolution photo stills from iPhone .MOV and BleeqUP POV video clips
specifically for native Facebook post attachments (solving the "no photos taken, only video" problem).
"""

import argparse
import subprocess
from pathlib import Path


def extract_stills_for_project(project_dir: Path) -> list[Path]:
    project_dir = Path(project_dir).expanduser().resolve()
    stills_dir = project_dir / "FB_Stills"
    stills_dir.mkdir(parents=True, exist_ok=True)

    extracted = []

    # Target key clips in the project folder
    candidates = [
        # (filename_pattern, timestamp_sec, output_name)
        ("IMG_8476.MOV", 3.5, "01_Bakery_Display.jpg"),
        ("IMG_8477.mov", 5.0, "02_Village_Square_Cafe.jpg"),
        ("IMG_8479.MOV", 3.0, "03_Pastry_Macro.jpg"),
        ("IMG_8484.mov", 6.0, "04_Pro_Cycle_Cafe_Patio.jpg"),
        ("VIDEO_1793094211149.MP4", 41.0, "05_Village_Fountain_POV.jpg"),
        ("VIDEO_1793098237718.MP4", 20.0, "06_Scenic_Cami_Climb.jpg"),
    ]

    for clip_name, ts, out_name in candidates:
        clip_p = project_dir / clip_name
        if not clip_p.exists():
            continue
        out_p = stills_dir / out_name
        cmd = [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-ss", str(ts),
            "-i", str(clip_p),
            "-vframes", "1",
            "-q:v", "2",
            str(out_p),
        ]
        res = subprocess.run(cmd, capture_output=True)
        if res.returncode == 0 and out_p.exists():
            extracted.append(out_p)

    return extracted


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Extract photo stills from project video clips for Facebook")
    p.add_argument("--project-dir", required=True, help="Path to project directory")
    args = p.parse_args()
    stills = extract_stills_for_project(Path(args.project_dir))
    print(f"Extracted {len(stills)} stills into {Path(args.project_dir) / 'FB_Stills'}")
