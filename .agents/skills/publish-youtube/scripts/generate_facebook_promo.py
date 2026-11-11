#!/usr/bin/env python3
"""Thin CLI & backward-compatibility shim over `agvs_core.youtube_pub` (Facebook promotional copy)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

from agvs_core.youtube_pub import build_facebook_promo, print_promo_box  # noqa: E402,F401


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate copy-ready Facebook promo options for a project")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--url")
    args = parser.parse_args(argv)
    promo = build_facebook_promo(Path(args.project_dir).expanduser().resolve(), live_url=args.url)
    print_promo_box(promo)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
