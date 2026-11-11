#!/usr/bin/env python3
"""Backwards-compatible CLI/module shim delegating to `agvs_core.bookends`."""

import sys
from pathlib import Path

STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.bookends import *  # noqa: E402,F401,F403
from agvs_core.bookends import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
