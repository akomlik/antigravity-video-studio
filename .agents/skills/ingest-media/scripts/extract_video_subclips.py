#!/usr/bin/env python3
"""Thin CLI shim over `agvs_core.ai_creative`."""

import sys
from pathlib import Path

_STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(_STUDIO_ROOT))

from agvs_core.ai_creative import analyze_clip_strip, process_project_subclips, subclips_cli_main as main, update_storyboard_media_log  # noqa: E402,F401

if __name__ == "__main__":
    main()
