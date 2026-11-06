#!/usr/bin/env python3
"""
relink_project_media.py
Automatically updates media paths in FilmCraft (.fcproj), project_manifest.json,
and DaVinci Resolve Studio (via RelinkClips API) when a YEAR/YYYY-MM-DD folder
is moved between local ~/Movies/YEAR/ and external /Volumes/Crucial-4T/Movies/YEAR/.
"""

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

try:
    STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
    if str(STUDIO_ROOT) not in sys.path:
        sys.path.insert(0, str(STUDIO_ROOT))
    import studio_config
    LOCAL_MOVIES_ROOT = str(studio_config.get_hot_media_dir())
    EXTERNAL_MOVIES_ROOT = str(studio_config.get_cold_media_dir())
except Exception:
    LOCAL_MOVIES_ROOT = str(Path(os.environ.get("LOCAL_MOVIES_ROOT", "~/Movies")).expanduser())
    EXTERNAL_MOVIES_ROOT = os.environ.get("EXTERNAL_MOVIES_ROOT", "/Volumes/Crucial-4T/Movies")


def relink_json_file(file_path: Path, old_prefix: str, new_prefix: str):
    """Safely updates file paths inside UTF-8 JSON files (.fcproj and project_manifest.json)."""
    if not file_path.exists():
        return False
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy2(file_path, backup_path)
    raw_text = file_path.read_text(encoding="utf-8")
    count = raw_text.count(old_prefix)
    if count == 0:
        print(f"No paths matching '{old_prefix}' found in {file_path.name}.")
        return False
    updated_text = raw_text.replace(old_prefix, new_prefix)
    # Validate JSON integrity before writing
    json.loads(updated_text)
    file_path.write_text(updated_text, encoding="utf-8")
    print(f"Updated {count} media path references in {file_path} (backup at {backup_path.name}).")
    return True


def relink_resolve_active_project(new_folder_path: str):
    """Calls DaVinci Resolve Scripting API mediaPool.RelinkClips() if Resolve is running."""
    sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")
    try:
        import DaVinciResolveScript as dvr_script
        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            return
        pm = resolve.GetProjectManager()
        proj = pm.GetCurrentProject()
        if not proj:
            return
        mp = proj.GetMediaPool()
        root_bin = mp.GetRootFolder()

        def collect_clips(folder):
            items = list(folder.GetClipList() or [])
            for sub in (folder.GetSubFolderList() or []):
                items.extend(collect_clips(sub))
            return items

        all_clips = collect_clips(root_bin)
        if all_clips:
            ok = mp.RelinkClips(all_clips, new_folder_path)
            print(f"DaVinci Resolve RelinkClips({len(all_clips)} items -> {new_folder_path}): {ok}")
    except Exception as exc:
        print(f"Note: DaVinci Resolve live relink skipped ({exc}).")


def main():
    parser = argparse.ArgumentParser(description="Relink video project between ~/Movies and /Volumes/Crucial-4T/Movies.")
    parser.add_argument("--project-catalog-dir", required=True, help="Path to 04_Project_Catalog/YEAR/YYYY-MM-DD_<name>")
    parser.add_argument("--direction", choices=["to-external", "to-local"], default="to-external")
    parser.add_argument("--media-subfolder", required=True, help="Relative subfolder, e.g. 2026/2026-10-27_Buger_coffee")
    args = parser.parse_args()

    cat_dir = Path(args.project_catalog_dir).expanduser().resolve()
    if args.direction == "to-external":
        old_root, new_root = LOCAL_MOVIES_ROOT, EXTERNAL_MOVIES_ROOT
    else:
        old_root, new_root = EXTERNAL_MOVIES_ROOT, LOCAL_MOVIES_ROOT

    for fcproj in cat_dir.glob("*.fcproj"):
        relink_json_file(fcproj, old_root, new_root)
    relink_json_file(cat_dir / "project_manifest.json", old_root, new_root)

    target_media_dir = f"{new_root}/{args.media_subfolder.strip('/')}"
    relink_resolve_active_project(target_media_dir)


if __name__ == "__main__":
    main()
