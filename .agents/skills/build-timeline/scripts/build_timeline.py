#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.timeline_builder`."""

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.audio_dsp import (  # noqa: E402,F401
    build_broadcast_audio_mixes,
    get_audio_duration as get_duration,
    prepare_boosted_dialog_stems,
    prepare_paced_voiceovers,
)
from agvs_core.timeline_builder import *  # noqa: E402,F401,F403
from agvs_core.timeline_builder import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
