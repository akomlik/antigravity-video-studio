#!/usr/bin/env python3
"""
check_filmcraft_env.py
FilmCraft Version Gate, CLI Auto-Sync, and MCP Capability Diffing Utility for Antigravity Video Studio v2.

Why this exists:
- FilmCraft (storytold/filmcraft) ships new releases every 48-72 hours via the ArtCraft Launcher.
- Updating FilmCraft.app via ArtCraft Launcher does NOT automatically update `/opt/homebrew/bin/filmcraft-cli`,
  and running an older FilmCraft (< 0.17.0) lacks key Studio v2 features (`essentialSound.*` auto-ducking &
  speech repair, 5x faster GPU Bokeh Blur, serialized bridge `render_frame`, and Shorts/Reels presets).
- This script enforces `MIN_FILMCRAFT_VERSION = "0.17.0"`, keeps `filmcraft-cli` synchronized with
  `/Applications/FilmCraft.app` (including `--sync-cli` one-command GitHub release download + ad-hoc codesign),
  checks `storytold/filmcraft` for newer upstream releases, and diffs live `filmcraft-cli commands --json`
  against `00_Archive_Indexes/filmcraft_capabilities.json` so you immediately see any newly added MCP commands.
"""

import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
CAPABILITIES_FILE = STUDIO_ROOT / "00_Archive_Indexes/filmcraft_capabilities.json"
MIN_FILMCRAFT_VERSION = "0.17.0"
APP_PLIST = Path("/Applications/FilmCraft.app/Contents/Info.plist")
GITHUB_LATEST_API = "https://api.github.com/repos/storytold/filmcraft/releases/latest"


def parse_semver(ver_str: str) -> tuple[int, ...]:
    if not ver_str:
        return (0, 0, 0)
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", ver_str)
    if not m:
        return (0, 0, 0)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def get_app_version() -> str | None:
    if not APP_PLIST.exists():
        return None
    try:
        with APP_PLIST.open("rb") as f:
            pl = plistlib.load(f)
            return str(pl.get("CFBundleShortVersionString") or "").strip()
    except Exception:
        return None


def find_cli_binary() -> Path | None:
    for candidate in [
        shutil.which("filmcraft-cli"),
        "/opt/homebrew/bin/filmcraft-cli",
        "/usr/local/bin/filmcraft-cli",
    ]:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    return None


def get_cli_version(cli_bin: Path | None) -> str | None:
    if not cli_bin or not cli_bin.exists():
        return None
    try:
        res = subprocess.run([str(cli_bin), "--version"], capture_output=True, text=True, check=False, timeout=5)
        if res.returncode == 0 and res.stdout:
            m = re.search(r"(\d+\.\d+\.\d+)", res.stdout)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None


def fetch_latest_github_release() -> dict | None:
    try:
        req = urllib.request.Request(
            GITHUB_LATEST_API,
            headers={"Accept": "application/vnd.github+json", "User-Agent": "antigravity-video-studio"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def sync_filmcraft_cli(target_version: str, cli_path: Path | None = None) -> Path:
    """Downloads filmcraft-cli-<ver>-macos-universal.zip from storytold/filmcraft, strips quarantine, and ad-hoc signs."""
    tag = f"v{target_version.lstrip('v')}"
    ver = target_version.lstrip("v")
    asset_name = f"filmcraft-cli-{ver}-macos-universal.zip"
    dest_bin = (cli_path.resolve() if cli_path and cli_path.exists() else Path("/opt/homebrew/bin/filmcraft-cli"))

    print(f"Syncing filmcraft-cli -> v{ver} ({asset_name})...")
    with tempfile.TemporaryDirectory(prefix="fc_cli_sync_") as tmpdir:
        tmp = Path(tmpdir)
        if shutil.which("gh"):
            subprocess.run(
                ["gh", "release", "download", tag, "--repo", "storytold/filmcraft", "--pattern", asset_name, "--dir", str(tmp)],
                check=True,
            )
        else:
            url = f"https://github.com/storytold/filmcraft/releases/download/{tag}/{asset_name}"
            urllib.request.urlretrieve(url, tmp / asset_name)

        subprocess.run(["unzip", "-q", "-o", str(tmp / asset_name), "-d", str(tmp)], check=True)
        extracted = list(tmp.rglob("filmcraft-cli"))
        if not extracted:
            raise FileNotFoundError(f"filmcraft-cli binary not found inside {asset_name}")
        src_bin = extracted[0]
        dest_bin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_bin, dest_bin)
        dest_bin.chmod(0o755)
        subprocess.run(["xattr", "-cr", str(dest_bin)], check=False)
        subprocess.run(["codesign", "--force", "--sign", "-", str(dest_bin)], check=True, capture_output=True)

    print(f"✅ Installed and signed filmcraft-cli v{ver} at {dest_bin}")
    return dest_bin


def diff_and_update_capabilities(cli_bin: Path, version_str: str, update_snapshot: bool = False) -> dict:
    """Queries `filmcraft-cli commands --json` and diffs against `00_Archive_Indexes/filmcraft_capabilities.json`."""
    res = subprocess.run([str(cli_bin), "commands", "--json"], capture_output=True, text=True, check=False)
    if res.returncode != 0 or not res.stdout.strip():
        return {"total": 0, "added": [], "removed": []}

    raw = json.loads(res.stdout)
    cmds = raw.get("commands", raw) if isinstance(raw, dict) else raw
    current_map = {c["id"]: c.get("params") or c.get("parameters") for c in cmds if isinstance(c, dict) and "id" in c}

    prev_map = {}
    prev_ver = None
    if CAPABILITIES_FILE.exists():
        try:
            old_data = json.loads(CAPABILITIES_FILE.read_text(encoding="utf-8"))
            prev_ver = old_data.get("version")
            prev_map = old_data.get("commands", {})
        except Exception:
            pass

    added = sorted(set(current_map.keys()) - set(prev_map.keys()))
    removed = sorted(set(prev_map.keys()) - set(current_map.keys()))

    if update_snapshot or not CAPABILITIES_FILE.exists() or added or removed or prev_ver != version_str:
        CAPABILITIES_FILE.parent.mkdir(parents=True, exist_ok=True)
        namespaces = {}
        for cid in sorted(current_map.keys()):
            ns = cid.split(".")[0] if "." in cid else cid
            namespaces[ns] = namespaces.get(ns, 0) + 1
        snapshot = {
            "version": version_str,
            "minimum_required_version": MIN_FILMCRAFT_VERSION,
            "total_commands": len(current_map),
            "namespaces": namespaces,
            "commands": current_map,
        }
        CAPABILITIES_FILE.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    return {
        "previous_version": prev_ver,
        "current_version": version_str,
        "total": len(current_map),
        "added": added,
        "removed": removed,
    }


def verify_filmcraft_environment(auto_sync_cli: bool = True, check_remote: bool = True, update_snapshot: bool = False) -> dict:
    app_ver = get_app_version()
    cli_bin = find_cli_binary()
    cli_ver = get_cli_version(cli_bin)

    if not app_ver and not cli_ver:
        raise RuntimeError(
            f"❌ FilmCraft not found! Please install FilmCraft >= v{MIN_FILMCRAFT_VERSION} via the ArtCraft Launcher "
            f"or from https://github.com/storytold/filmcraft/releases/latest."
        )

    effective_ver = app_ver or cli_ver
    if parse_semver(effective_ver) < parse_semver(MIN_FILMCRAFT_VERSION):
        raise RuntimeError(
            f"❌ FilmCraft v{effective_ver} is older than the minimum required v{MIN_FILMCRAFT_VERSION} for Antigravity Video Studio v2.\n"
            f"   Studio v2 relies on `essentialSound.*` auto-ducking & dialogue repair, 5x faster GPU Bokeh Blur, and serialized bridge rendering.\n"
            f"   👉 Open the ArtCraft Launcher and click Update on FilmCraft (or run `check_filmcraft_env.py --sync-cli`)."
        )

    # Ensure filmcraft-cli matches FilmCraft.app
    if app_ver and cli_ver != app_ver:
        if auto_sync_cli:
            print(f"⚠️  filmcraft-cli ({cli_ver or 'missing'}) != FilmCraft.app (v{app_ver}). Auto-syncing filmcraft-cli...")
            cli_bin = sync_filmcraft_cli(app_ver, cli_bin)
            cli_ver = get_cli_version(cli_bin)
        else:
            print(
                f"⚠️  Version mismatch: FilmCraft.app is v{app_ver}, but filmcraft-cli is v{cli_ver}. "
                f"Run `python3 ./.agents/skills/assemble-timeline/scripts/check_filmcraft_env.py --sync-cli` to align them."
            )

    remote_info = {}
    if check_remote:
        rel = fetch_latest_github_release()
        if rel and rel.get("tag_name"):
            latest_ver = rel["tag_name"].lstrip("v")
            remote_info = {
                "latest_version": latest_ver,
                "published_at": rel.get("published_at"),
                "url": rel.get("html_url"),
                "update_available": parse_semver(latest_ver) > parse_semver(effective_ver),
            }
            if remote_info["update_available"]:
                print(
                    f"🚀 New FilmCraft release available upstream: v{latest_ver} (installed: v{effective_ver})!\n"
                    f"   Update in ArtCraft Launcher, then run `check_filmcraft_env.py --sync-cli` to inspect new MCP commands."
                )

    cap_diff = {}
    if cli_bin and cli_ver:
        cap_diff = diff_and_update_capabilities(cli_bin, cli_ver, update_snapshot=update_snapshot)
        if cap_diff.get("added"):
            print(f"✨ Detected {len(cap_diff['added'])} NEW FilmCraft MCP commands in v{cli_ver}: {', '.join(cap_diff['added'][:15])}")

    status = {
        "ok": True,
        "minimum_required": MIN_FILMCRAFT_VERSION,
        "app_version": app_ver,
        "cli_version": cli_ver,
        "cli_binary": str(cli_bin) if cli_bin else None,
        "remote": remote_info,
        "capabilities": cap_diff,
    }
    return status


def main():
    parser = argparse.ArgumentParser(description="Verify FilmCraft >= v0.17.0, sync filmcraft-cli, and diff MCP commands.")
    parser.add_argument("--sync-cli", action="store_true", help="Force download & codesign of filmcraft-cli matching FilmCraft.app (or latest)")
    parser.add_argument("--no-auto-sync", action="store_true", help="Do not auto-download filmcraft-cli on mismatch")
    parser.add_argument("--no-remote", action="store_true", help="Skip GitHub latest release check")
    parser.add_argument("--update-snapshot", action="store_true", help="Force rewrite of 00_Archive_Indexes/filmcraft_capabilities.json")
    args = parser.parse_args()

    if args.sync_cli:
        target = get_app_version()
        if not target:
            rel = fetch_latest_github_release()
            target = (rel.get("tag_name") or MIN_FILMCRAFT_VERSION).lstrip("v") if rel else MIN_FILMCRAFT_VERSION
        sync_filmcraft_cli(target, find_cli_binary())

    status = verify_filmcraft_environment(
        auto_sync_cli=not args.no_auto_sync,
        check_remote=not args.no_remote,
        update_snapshot=args.update_snapshot,
    )
    print(
        f"✅ FilmCraft Environment Verified: App v{status['app_version']} | CLI v{status['cli_version']} | "
        f"{status['capabilities'].get('total', 0)} MCP commands indexed"
        + (
            f" | Upstream latest: v{status['remote'].get('latest_version')}"
            if status.get("remote", {}).get("latest_version")
            else ""
        )
    )


if __name__ == "__main__":
    main()
