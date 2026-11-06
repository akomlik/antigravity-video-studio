"""
studio_config.py
Universal studio configuration and portable relative path resolver for Antigravity Video Studio.

Reads `studio.conf` at the workspace root (or ANTIGRAVITY_STUDIO_CONFIG / ANTIGRAVITY_STUDIO_ROOT)
and provides dynamic resolution of Tier 1 (Studio Root), Tier 2 (Hot Media), and Tier 3 (Cold Media)
paths without freezing machine-specific absolute paths into repository or catalog files.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional, Union


def _find_studio_root() -> Path:
    """Discovers studio root via env var or by searching upward for studio.conf."""
    env_root = os.environ.get("ANTIGRAVITY_STUDIO_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root).resolve()

    # Search upward from this file
    current = Path(__file__).resolve().parent
    for p in [current] + list(current.parents):
        if (p / "studio.conf").exists() or (p / "editing_constitution.md").exists():
            return p
    return current


STUDIO_ROOT = _find_studio_root()


def load_config() -> dict:
    """Loads studio.conf or returns standard defaults."""
    conf_path = None
    env_conf = os.environ.get("ANTIGRAVITY_STUDIO_CONFIG")
    if env_conf and Path(env_conf).exists():
        conf_path = Path(env_conf)
    else:
        candidate = STUDIO_ROOT / "studio.conf"
        if candidate.exists():
            conf_path = candidate

    defaults = {
        "studio_name": "Antigravity Video Studio",
        "version": "2.1.0",
        "storage": {
            "studio_root": ".",
            "hot_media_dir": "~/Movies",
            "cold_media_dir": "/Volumes/Crucial-4T/Movies",
            "cache_dir": "~/Movies/Cache_And_Previews",
            "exports_dir": "~/Movies/Exports",
            "archival_photos_dir": "/Volumes/Crucial-4T/Pictures",
        },
        "catalogs": {
            "project_catalog_dir": "04_Project_Catalog",
            "bgm_library_dir": "03_Audio_Library/01_Curated_BGM",
            "sfx_library_dir": "03_Audio_Library/02_SFX",
            "voice_profile_dir": "03_Audio_Library/03_Voice_Profile",
            "archive_indexes_dir": "00_Archive_Indexes",
        },
    }

    if conf_path:
        try:
            user_conf = json.loads(conf_path.read_text(encoding="utf-8"))
            if "storage" in user_conf:
                defaults["storage"].update(user_conf["storage"])
            if "catalogs" in user_conf:
                defaults["catalogs"].update(user_conf["catalogs"])
            if "studio_name" in user_conf:
                defaults["studio_name"] = user_conf["studio_name"]
        except Exception as e:
            print(f"Warning reading {conf_path}: {e}", file=sys.stderr)

    return defaults


_CONFIG = load_config()
_STORAGE = _CONFIG.get("storage", {})
_CATALOGS = _CONFIG.get("catalogs", {})


def get_studio_root() -> Path:
    return STUDIO_ROOT


def get_hot_media_dir() -> Path:
    override = os.environ.get("HOT_MEDIA_DIR") or os.environ.get("LOCAL_MOVIES_ROOT")
    val = override or _STORAGE.get("hot_media_dir", "~/Movies")
    return Path(val).expanduser().resolve()


def get_cold_media_dir() -> Path:
    override = os.environ.get("COLD_MEDIA_DIR") or os.environ.get("EXTERNAL_MOVIES_ROOT")
    val = override or _STORAGE.get("cold_media_dir", "/Volumes/Crucial-4T/Movies")
    return Path(val).expanduser().resolve()


def get_cache_dir() -> Path:
    override = os.environ.get("FILMCRAFT_CACHE_DIR") or os.environ.get("CACHE_DIR")
    val = override or _STORAGE.get("cache_dir", "~/Movies/Cache_And_Previews")
    p = Path(val).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_exports_dir() -> Path:
    override = os.environ.get("EXPORTS_DIR")
    val = override or _STORAGE.get("exports_dir", "~/Movies/Exports")
    p = Path(val).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_bgm_root() -> Path:
    return STUDIO_ROOT / _CATALOGS.get("bgm_library_dir", "03_Audio_Library/01_Curated_BGM")


def get_sfx_root() -> Path:
    return STUDIO_ROOT / _CATALOGS.get("sfx_library_dir", "03_Audio_Library/02_SFX")


def get_project_catalog_root() -> Path:
    return STUDIO_ROOT / _CATALOGS.get("project_catalog_dir", "04_Project_Catalog")


def to_studio_relpath(path: Union[Path, str]) -> str:
    """Converts a Path or str into a clean relative path against STUDIO_ROOT if located within it."""
    try:
        p = Path(path).resolve()
        return str(p.relative_to(STUDIO_ROOT))
    except (ValueError, Exception):
        return str(path)


def resolve_studio_path(relpath: Union[Path, str]) -> Path:
    """Resolves a relative studio path against STUDIO_ROOT."""
    p = Path(relpath)
    if p.is_absolute() and p.exists():
        return p
    return (STUDIO_ROOT / p).resolve()


def to_media_relpath(path: Union[Path, str]) -> str:
    """Converts a media file path into a relative path against HOT_MEDIA_DIR or COLD_MEDIA_DIR."""
    p = Path(path).resolve()
    hot = get_hot_media_dir()
    cold = get_cold_media_dir()

    for base in [hot, cold]:
        try:
            return str(p.relative_to(base))
        except ValueError:
            pass
    return str(path)


def resolve_media_path(relpath: Union[Path, str]) -> Path:
    """Resolves a relative media path by checking HOT_MEDIA_DIR first, then COLD_MEDIA_DIR."""
    p = Path(relpath)
    if p.is_absolute() and p.exists():
        return p

    hot_target = get_hot_media_dir() / p
    if hot_target.exists():
        return hot_target

    cold_target = get_cold_media_dir() / p
    if cold_target.exists():
        return cold_target

    return hot_target  # Default to hot media path
