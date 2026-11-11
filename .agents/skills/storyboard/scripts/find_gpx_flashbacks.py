#!/usr/bin/env python3
"""Thin CLI shim over `agvs_core.flashback_lrcat`."""

import sys
from pathlib import Path

_STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(_STUDIO_ROOT))

from agvs_core.flashback_lrcat import *  # noqa: E402,F401,F403
from agvs_core.flashback_lrcat import flashbacks_cli_main as main  # noqa: E402

if __name__ == "__main__":
    main()
