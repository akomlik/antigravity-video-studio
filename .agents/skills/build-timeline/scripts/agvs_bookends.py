#!/usr/bin/env python3
"""Backwards-compatible CLI/module shim delegating to agvs_core.bookends."""

from __future__ import annotations

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.bookends import (  # noqa: E402,F401
    COLOR_ESPRESSO_INK,
    COLOR_FOREST_GREEN,
    COLOR_MAP_LAND,
    COLOR_MAP_WATER,
    COLOR_PARCHMENT_CENTER,
    COLOR_PARCHMENT_EDGE,
    COLOR_POLAROID_BORDER,
    COLOR_POLAROID_PAPER,
    COLOR_POSTMARK_CRIMSON,
    COLOR_TICKET_BG,
    COLOR_UMBER_INK,
    OUTRO_CREDITS_SUBLINE_EN,
    OUTRO_CREDITS_SUBLINE_RU,
    composite_intro_bookend_mp4,
    composite_outro_bookend_mp4,
    create_warm_parchment_canvas,
    draw_cartographic_neatline,
    draw_compass_rose,
    draw_postmark_watermark,
    extract_project_bookends_spec,
    fetch_and_render_vintage_basemap,
    generate_project_bookends,
    latlon_to_tile,
    load_apple_font,
    main,
    parse_gpx_points,
    render_intro_canvas_4k,
    render_outro_canvas_4k,
    render_polaroid_border_png,
    to_mercator_pixels,
)

if __name__ == "__main__":
    raise SystemExit(main())
