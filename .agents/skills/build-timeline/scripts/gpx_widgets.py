#!/usr/bin/env python3
"""Backwards-compatible CLI/module shim delegating to `agvs_core.vintage_cards`."""

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
from agvs_core.vintage_cards import *  # noqa: E402,F401,F403
from agvs_core.vintage_cards import _load_font  # noqa: E402,F401
