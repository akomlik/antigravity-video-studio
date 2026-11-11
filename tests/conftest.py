"""Shared pytest fixtures and portable module loaders for AGVS v3 Golden Regression Suite."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

STUDIO_ROOT = Path(__file__).resolve().parent.parent
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

CATALOG_2026 = STUDIO_ROOT / "04_Project_Catalog" / "2026"
FEMENIA_DIR = CATALOG_2026 / "2026-11-05_Femenia_Climbing"
PARADISE_DIR = CATALOG_2026 / "2026-11-10_Another_Day_In_Paradise"


def load_script_module(module_alias: str, rel_script_path: str):
    """Dynamically loads a skill script by relative path from STUDIO_ROOT without freezing absolute paths."""
    script_path = STUDIO_ROOT / rel_script_path
    scripts_dir = str(script_path.parent)
    if scripts_dir not in sys.path:
        sys.path.insert(0, scripts_dir)
    spec = importlib.util.spec_from_file_location(module_alias, script_path)
    assert spec is not None and spec.loader is not None, f"Cannot load {rel_script_path}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_alias] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="session")
def studio_root() -> Path:
    return STUDIO_ROOT


@pytest.fixture(scope="session")
def femenia_dir() -> Path:
    if not FEMENIA_DIR.exists():
        pytest.skip("Golden fixture 2026-11-05_Femenia_Climbing not present on disk")
    return FEMENIA_DIR


@pytest.fixture(scope="session")
def paradise_dir() -> Path:
    if not PARADISE_DIR.exists():
        pytest.skip("Golden fixture 2026-11-10_Another_Day_In_Paradise not present on disk")
    return PARADISE_DIR
