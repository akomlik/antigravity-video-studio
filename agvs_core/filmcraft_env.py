"""FilmCraft environment version gate (>= v0.17.0), CLI auto-sync, and MCP capability snapshot diffing."""

from __future__ import annotations

import argparse
import json
import plistlib
import re
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Any

from agvs_core.config import find_binary, get_studio_root

MIN_FILMCRAFT_VERSION = "0.17.0"
APP_PLIST = Path("/Applications/FilmCraft.app/Contents/Info.plist")
GITHUB_LATEST_API = "https://api.github.com/repos/storytold/filmcraft/releases/latest"


def get_capabilities_file() -> Path:
    return get_studio_root() / "00_Archive_Indexes" / "filmcraft_capabilities.json"


def parse_semver(ver_str: str | None) -> tuple[int, int, int]:
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
            return str(pl.get("CFBundleShortVersionString") or "").strip() or None
    except Exception:
        return None


def find_cli_binary() -> Path | None:
    found = find_binary("filmcraft-cli")
    return Path(found) if found else None


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


def fetch_latest_github_release() -> dict[str, Any] | None:
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
    tag = f"v{target_version.lstrip('v')}"
    ver = target_version.lstrip("v")
    asset_name = f"filmcraft-cli-{ver}-macos-universal.zip"
    dest_bin = cli_path.resolve() if cli_path and cli_path.exists() else Path("/opt/homebrew/bin/filmcraft-cli")

    with tempfile.TemporaryDirectory(prefix="fc_cli_sync_") as tmpdir:
        tmp = Path(tmpdir)
        gh_bin = find_binary("gh")
        if gh_bin:
            subprocess.run(
                [gh_bin, "release", "download", tag, "--repo", "storytold/filmcraft", "--pattern", asset_name, "--dir", str(tmp)],
                check=True,
            )
        else:
            url = f"https://github.com/storytold/filmcraft/releases/download/{tag}/{asset_name}"
            urllib.request.urlretrieve(url, tmp / asset_name)

        subprocess.run(["unzip", "-q", "-o", str(tmp / asset_name), "-d", str(tmp)], check=True)
        extracted = list(tmp.rglob("filmcraft-cli"))
        if not extracted:
            raise FileNotFoundError(f"filmcraft-cli binary not found inside {asset_name}")
        dest_bin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(extracted[0], dest_bin)
        dest_bin.chmod(0o755)
        subprocess.run(["xattr", "-cr", str(dest_bin)], check=False)
        subprocess.run(["codesign", "--force", "--sign", "-", str(dest_bin)], check=True, capture_output=True)
    return dest_bin


def diff_and_update_capabilities(cli_bin: Path, version_str: str, update_snapshot: bool = False) -> dict[str, Any]:
    cap_file = get_capabilities_file()
    res = subprocess.run([str(cli_bin), "commands", "--json"], capture_output=True, text=True, check=False)
    if res.returncode != 0 or not res.stdout.strip():
        return {"total": 0, "added": [], "removed": []}

    raw = json.loads(res.stdout)
    cmds = raw.get("commands", raw) if isinstance(raw, dict) else raw
    current_map = {c["id"]: c.get("params") or c.get("parameters") for c in cmds if isinstance(c, dict) and "id" in c}

    prev_map: dict[str, Any] = {}
    prev_ver = None
    if cap_file.exists():
        try:
            old_data = json.loads(cap_file.read_text(encoding="utf-8"))
            prev_ver = old_data.get("version")
            prev_map = old_data.get("commands", {})
        except Exception:
            pass

    added = sorted(set(current_map.keys()) - set(prev_map.keys()))
    removed = sorted(set(prev_map.keys()) - set(current_map.keys()))

    if update_snapshot or not cap_file.exists() or added or removed or prev_ver != version_str:
        cap_file.parent.mkdir(parents=True, exist_ok=True)
        namespaces: dict[str, int] = {}
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
        cap_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

    return {
        "previous_version": prev_ver,
        "current_version": version_str,
        "total": len(current_map),
        "added": added,
        "removed": removed,
    }


def verify_filmcraft_environment(
    auto_sync_cli: bool = True,
    check_remote: bool = True,
    update_snapshot: bool = False,
) -> dict[str, Any]:
    app_ver = get_app_version()
    cli_bin = find_cli_binary()
    cli_ver = get_cli_version(cli_bin)

    if not app_ver and not cli_ver:
        raise RuntimeError(
            f"FilmCraft not found. Install FilmCraft >= v{MIN_FILMCRAFT_VERSION} via ArtCraft Launcher."
        )

    effective_ver = app_ver or cli_ver or "0.0.0"
    if parse_semver(effective_ver) < parse_semver(MIN_FILMCRAFT_VERSION):
        raise RuntimeError(
            f"FilmCraft v{effective_ver} is older than minimum required v{MIN_FILMCRAFT_VERSION}."
        )

    if app_ver and cli_ver != app_ver and auto_sync_cli:
        cli_bin = sync_filmcraft_cli(app_ver, cli_bin)
        cli_ver = get_cli_version(cli_bin)

    remote_info: dict[str, Any] = {}
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

    cap_diff = diff_and_update_capabilities(cli_bin, cli_ver, update_snapshot=update_snapshot) if (cli_bin and cli_ver) else {}
    return {
        "ok": True,
        "minimum_required": MIN_FILMCRAFT_VERSION,
        "app_version": app_ver,
        "cli_version": cli_ver,
        "cli_binary": str(cli_bin) if cli_bin else None,
        "remote": remote_info,
        "capabilities": cap_diff,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Verify FilmCraft >= v0.17.0, sync filmcraft-cli, and diff MCP commands.")
    parser.add_argument("--sync-cli", action="store_true")
    parser.add_argument("--no-auto-sync", action="store_true")
    parser.add_argument("--no-remote", action="store_true")
    parser.add_argument("--update-snapshot", action="store_true")
    args = parser.parse_args(argv)

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
    print(f"FilmCraft Verified: App v{status['app_version']} | CLI v{status['cli_version']}")
    return 0
