#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.youtube_pub` (YouTube Data API v3 upload)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.youtube_pub import (  # noqa: E402,F401
    DEFAULT_YOUTUBE_PRIVACY_STATUS,
    OAUTH_DIR,
    SCOPES,
    TOKEN_FILE,
    YT_WIRE_LANG,
    assign_playlists_and_captions,
    compute_srt_sha256,
    get_youtube_service,
    get_yt_index_path,
    infer_recording_date_iso,
    load_dotenv_if_needed,
    output_facebook_promo_after_publish,
    post_pinned_language_comment,
    register_in_archive_index,
    sanitize_yt_description,
    should_skip_video_insert_on_resume,
    update_existing_video_via_api,
    upload_cli_main as main,
    upload_option_b_multilingual,
    upload_raw_video,
)

if __name__ == "__main__":
    raise SystemExit(main())
