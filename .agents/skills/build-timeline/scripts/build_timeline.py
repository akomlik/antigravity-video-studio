#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.timeline_builder`."""

from __future__ import annotations

import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.audio_dsp import (  # noqa: E402,F401
    build_broadcast_audio_mixes,
    get_audio_duration as get_duration,
    prepare_boosted_dialog_stems,
    prepare_paced_voiceovers,
)
from agvs_core.timeline_builder import (  # noqa: E402,F401
    PRESET_4K_MATCH_SOURCE,
    TICKS_PER_SEC,
    attach_bookend_cuts_if_needed,
    build_edition_export_plan,
    build_fcproj_document,
    build_fcproj_from_spec,
    build_project_timeline,
    check_bgm_non_reuse_preflight,
    check_landmark_synchronization_preflight,
    check_zero_project_scripts_preflight,
    ensure_blur_pillarbox_still,
    execute_edition_exports,
    fmt_srt_tc,
    generate_srt_subtitles,
    main,
    make_motion_ken_burns,
    make_opacity_in_out,
    make_static_motion,
    probe_media_dimensions,
    verify_and_repair_v1_continuity,
    verify_music_non_reuse,
    verify_zero_project_scripts,
)

if __name__ == "__main__":
    raise SystemExit(main())
