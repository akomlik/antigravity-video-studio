#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.flickr_pub`."""

from __future__ import annotations

import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.flickr_pub import (  # noqa: E402,F401
    TOKEN_DIR,
    TOKEN_FILE,
    assign_photo_to_album,
    authenticate_interactive,
    cross_link_flickr_on_youtube,
    extract_gpx_coordinates,
    extract_project_metadata,
    get_flickr_credentials,
    get_flickr_index_path,
    get_oauth_session,
    main,
    register_in_flickr_index,
    set_photo_geolocation,
    upload_video_to_flickr,
)

if __name__ == "__main__":
    raise SystemExit(main())
