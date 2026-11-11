#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.youtube_pub` (metadata & thumbnails)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.youtube_pub import (  # noqa: E402,F401
    DEFAULT_YOUTUBE_PRIVACY_STATUS,
    TICKS_PER_SEC,
    extract_cues_and_chapters_from_fcproj,
    extract_thumbnail,
    fmt_mmss,
    fmt_srt_tc,
    format_music_credit,
    generate_composite_thumbnail,
    generate_project_youtube_metadata,
    localize_existing_thumbnail,
    metadata_cli_main as main,
    parse_storyboard_thumbnail_cfg,
    resolve_thumbnail_headline,
    write_srt,
)

if __name__ == "__main__":
    raise SystemExit(main())
