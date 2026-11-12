"""
agvs_core/config.py
Single source of truth for studio storage configuration, portable relative paths,
external binary discovery, and 1Password / biometric credential resolution.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Union

_FORBIDDEN_ABS_PREFIXES = ("/" + "Users/", "/" + "Volumes/", "/private/" + "var/folders/")


def _find_studio_root() -> Path:
    """Discovers studio root via env var or by searching upward for studio.conf."""
    env_root = os.environ.get("ANTIGRAVITY_STUDIO_ROOT")
    if env_root and Path(env_root).exists():
        return Path(env_root).resolve()

    current = Path(__file__).resolve().parent
    for p in [current] + list(current.parents):
        if (p / "studio.conf").exists() or (p / "editing_constitution.md").exists():
            return p
    return current.parent


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
        "version": "3.0.0",
        "storage": {
            "studio_root": ".",
            "hot_media_dir": "~/Movies",
            "cold_media_dir": "/Volumes/Crucial-4T/Movies",
            "archival_pulls_dir": "~/Movies/Archival_Pulls",
            "lightroom_catalog_dir": "~/Pictures/Lightroom",
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


def get_map_tile_cache_dir() -> Path:
    """Persistent disk cache for OpenStreetMap/Carto map tiles outside Google Drive."""
    p = get_cache_dir() / "tiles"
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_exports_dir() -> Path:
    override = os.environ.get("EXPORTS_DIR")
    val = override or _STORAGE.get("exports_dir", "~/Movies/Exports")
    p = Path(val).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_archival_pulls_dir() -> Path:
    override = os.environ.get("ARCHIVAL_PULLS_DIR")
    val = override or _STORAGE.get("archival_pulls_dir", "~/Movies/Archival_Pulls")
    p = Path(val).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_archival_photos_dir() -> Path:
    override = os.environ.get("ARCHIVAL_PHOTOS_DIR")
    val = override or _STORAGE.get("archival_photos_dir", "/Volumes/Crucial-4T/Pictures")
    return Path(val).expanduser().resolve()


def get_lightroom_catalog_dir() -> Optional[Path]:
    override = os.environ.get("LIGHTROOM_CATALOG_DIR")
    val = override or _STORAGE.get("lightroom_catalog_dir")
    if not val:
        return None
    p = Path(val).expanduser().resolve()
    return p if p.exists() and p.is_dir() else None


def find_active_lightroom_catalog() -> Optional[tuple[Path, Path]]:
    """Finds the active Lightroom Classic .lrcat file and matching Previews.lrdata folder."""
    lr_dir = get_lightroom_catalog_dir()
    if not lr_dir:
        return None

    candidates = [
        p
        for p in lr_dir.glob("*.lrcat")
        if not p.name.endswith((".lock", "-wal", "-shm"))
        and "Old Lightroom Catalogs" not in str(p)
        and "Backups" not in str(p)
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    active_lrcat = candidates[0]

    previews_dir = active_lrcat.with_name(active_lrcat.stem + " Previews.lrdata")
    if not previews_dir.exists():
        for p in lr_dir.glob("*Previews.lrdata"):
            if p.is_dir():
                previews_dir = p
                break

    return active_lrcat, previews_dir


def get_bgm_root() -> Path:
    return STUDIO_ROOT / _CATALOGS.get("bgm_library_dir", "03_Audio_Library/01_Curated_BGM")


def get_sfx_root() -> Path:
    return STUDIO_ROOT / _CATALOGS.get("sfx_library_dir", "03_Audio_Library/02_SFX")


def get_project_catalog_root() -> Path:
    return STUDIO_ROOT / _CATALOGS.get("project_catalog_dir", "04_Project_Catalog")


def find_binary(name: str, required: bool = True) -> Optional[str]:
    """Locates a required external binary (ffmpeg, ffprobe, exiftool, filmcraft-cli, sips, yt-dlp, op)."""
    search_paths = [
        shutil.which(name),
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
        f"/usr/bin/{name}",
        str(Path("~/.local/bin").expanduser() / name),
    ]
    if name == "filmcraft-cli":
        search_paths.append("/Applications/FilmCraft.app/Contents/MacOS/filmcraft-cli")

    for candidate in search_paths:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    if required:
        raise FileNotFoundError(f"Required binary '{name}' not found on PATH or standard macOS locations.")
    return None


def ensure_relative_studio_path(path_str: str) -> str:
    """Enforces the Zero-Absolute-Path Law on stored catalog/manifest/spec strings."""
    val = str(path_str).strip()
    if any(val.startswith(pref) for pref in _FORBIDDEN_ABS_PREFIXES) or Path(val).is_absolute():
        raise ValueError(
            f"Absolute machine path forbidden by Zero-Absolute-Path Law: {val!r}. "
            "Store a relative path against STUDIO_ROOT or HOT_MEDIA_DIR instead."
        )
    return val


def ensure_no_raw_voice_id(value: str) -> str:
    """Enforces the Biometric Voice ID Security Law (rejects literal `voice_*` keys)."""
    val = str(value).strip()
    if re.search(r"\bvoice_[A-Za-z0-9]{6,}\b", val):
        raise ValueError(
            "Biometric Voice ID Security Law violation: literal `voice_*` secret forbidden in project files! "
            'Use "$GEMINI_VOICE_ID" instead.'
        )
    return val


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

    return hot_target


def get_local_secret_voice_cache_file() -> Path:
    """Local non-cloud-synced 0o600 voice ID cache under ~/.config/antigravity_studio/."""
    return Path("~/.config/antigravity_studio/voice_id.json").expanduser()


def mask_secret(secret: Optional[str]) -> str:
    """Masks a secret key or voice_* identifier for safe console logging."""
    if not secret:
        return "<empty>"
    s = str(secret).strip()
    if len(s) <= 8:
        return "***"
    return f"{s[:7]}...{s[-3:]}"


def get_gemini_voice_id(prefer_1password: bool = False) -> Optional[str]:
    """
    Resolves Alexander's Gemini TTS Voice ID securely without checking secrets into Git or cloud folders.
    Precedence:
    0. If `prefer_1password=True`, query 1Password CLI (`envvar:GEMINI_VOICE_ID`) first so freshly rotated secrets win.
    1. Local 0o600 cache outside Google Drive (~/.config/antigravity_studio/voice_id.json)
    2. os.environ.get("GEMINI_VOICE_ID") (direnv / 1Password shell export)
    3. Legacy git-ignored local overrides (.env or 03_Audio_Library/03_Voice_Profile/voice_id.json)
    4. 1Password CLI fallback: `op item get "envvar:GEMINI_VOICE_ID" --vault Private --fields credential --reveal`
    """
    op_bin = find_binary("op", required=False)
    if prefer_1password and op_bin:
        try:
            res = subprocess.run(
                [op_bin, "item", "get", "envvar:GEMINI_VOICE_ID", "--vault", "Private", "--fields", "credential", "--reveal"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if res.returncode == 0 and res.stdout.strip():
                val = res.stdout.strip()
                os.environ["GEMINI_VOICE_ID"] = val
                return val
        except Exception:
            pass

    local_cache = get_local_secret_voice_cache_file()
    if local_cache.exists():
        try:
            data = json.loads(local_cache.read_text(encoding="utf-8"))
            val = data.get("voice_id")
            if val:
                os.environ["GEMINI_VOICE_ID"] = val
                return val
        except Exception:
            pass

    v = os.environ.get("GEMINI_VOICE_ID")
    if v and v.strip() and v.strip() != "$GEMINI_VOICE_ID":
        return v.strip()

    for voice_json in (
        STUDIO_ROOT / "03_Audio_Library/03_Voice_Profile/voice_id.json",
    ):
        if voice_json.exists():
            try:
                data = json.loads(voice_json.read_text(encoding="utf-8"))
                val = data.get("voice_id")
                if val:
                    os.environ["GEMINI_VOICE_ID"] = val
                    return val
            except Exception:
                pass

    env_file = STUDIO_ROOT / ".env"
    if env_file.exists():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("GEMINI_VOICE_ID="):
                    val = line.split("=", 1)[1].strip().strip("\"'")
                    if val:
                        os.environ["GEMINI_VOICE_ID"] = val
                        return val
        except Exception:
            pass

    op_bin = find_binary("op", required=False)
    if op_bin:
        try:
            res = subprocess.run(
                [op_bin, "item", "get", "envvar:GEMINI_VOICE_ID", "--vault", "Private", "--fields", "credential", "--reveal"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode == 0 and res.stdout.strip():
                val = res.stdout.strip()
                os.environ["GEMINI_VOICE_ID"] = val
                return val
        except Exception:
            pass

    return None
