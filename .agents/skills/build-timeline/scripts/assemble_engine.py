#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.timeline_builder` and `agvs_core.audio_dsp`."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.audio_dsp import (  # noqa: E402,F401
    calculate_bgm_gains,
    compute_bgm_ducked_gain_db,
    filter_vo_cues_for_same_language_dialog,
    is_mellow_bgm_track,
    master_outro_fade_filter,
    measure_mean_volume_db,
    measure_volume_stats,
)
from agvs_core.filmcraft_env import verify_filmcraft_environment  # noqa: E402,F401
from agvs_core.timeline_builder import (  # noqa: E402,F401
    TICKS_PER_SEC,
    apply_v017_essential_sound_via_cli,
    make_motion_ken_burns,
    make_static_motion,
    make_volume_effect,
    polish_and_render_project,
    sanitize_caption_text,
    verify_and_repair_v1_continuity,
    verify_music_non_reuse,
    verify_zero_project_scripts,
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Universal Timeline Assembly & Polishing Engine (FilmCraft v0.17.0+)")
    p.add_argument("--project", required=True, help="Path to .fcproj project file")
    p.add_argument("--export-mp4", help="Optional path to output master MP4")
    p.add_argument("--burn-captions", action="store_true", help="Burn captions into video (default: False)")
    p.add_argument("--allow-used-music", action="store_true", help="Allow tracks already used in past projects")
    args = p.parse_args(argv)

    fcproj = Path(args.project).expanduser().resolve()
    mp4 = Path(args.export_mp4).expanduser().resolve() if args.export_mp4 else None
    polish_and_render_project(fcproj, mp4, burn_captions=args.burn_captions, allow_used_music=args.allow_used_music)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
