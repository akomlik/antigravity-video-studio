#!/usr/bin/env python3
"""Backwards-compatible CLI/module shim delegating to agvs_core.vintage_cards."""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.telemetry_gpx import (  # noqa: E402,F401
    ACTIVITY_SPEED_THRESHOLDS,
    haversine_m,
    load_gpx_track as load_gpx_stream,
    select_primary_ride_gpx,
    should_show_telemetry_hud,
)
from agvs_core.vintage_cards import (  # noqa: E402,F401
    COLOR_BORDER_UMBER,
    COLOR_CRIMSON,
    COLOR_ESPRESSO_INK,
    COLOR_FOREST_GREEN,
    COLOR_NEATLINE,
    COLOR_PARCHMENT_FILL,
    COLOR_UMBER_INK,
    _load_font,
    draw_vintage_card,
    load_apple_font,
    paginate_speech_segments,
    render_character_callout_badge,
    render_corner_map_widget,
    render_declarative_overlays,
    render_flashback_memory_badge,
    render_live_telemetry_hud_series,
    render_strava_comparison_vintage_card,
    render_telemetry_hud_widget,
    render_translation_subtitle_card,
    strip_unicode_emojis,
)
