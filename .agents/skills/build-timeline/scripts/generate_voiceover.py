#!/usr/bin/env python3
"""Thin CLI shim over `agvs_core.voice_profile`."""

import sys
from pathlib import Path

_STUDIO_ROOT = Path(__file__).resolve().parents[4]
if str(_STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(_STUDIO_ROOT))

from agvs_core.voice_profile import (  # noqa: E402,F401
    ensure_custom_voice,
    generate_voiceover_cli_main as main,
    load_dotenv_if_needed,
    synthesize_narration,
)

if __name__ == "__main__":
    main()
