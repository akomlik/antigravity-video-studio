#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.filmcraft_env`."""

from __future__ import annotations

import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.filmcraft_env import (  # noqa: E402,F401
    APP_PLIST,
    GITHUB_LATEST_API,
    MIN_FILMCRAFT_VERSION,
    diff_and_update_capabilities,
    fetch_latest_github_release,
    find_cli_binary,
    get_app_version,
    get_capabilities_file,
    get_cli_version,
    main,
    parse_semver,
    sync_filmcraft_cli,
    verify_filmcraft_environment,
)

if __name__ == "__main__":
    raise SystemExit(main())
