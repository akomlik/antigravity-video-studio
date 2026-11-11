"""
agvs_core/flashback_lrcat.py
Read-only Adobe Lightroom Classic (.lrcat) GPX corridor flashback discovery,
catalog stock indexing, YouTube archival B-roll slicing, and Hot/Cold media archive relinking.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import subprocess
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from agvs_core.config import (
    find_active_lightroom_catalog,
    find_binary,
    get_archival_pulls_dir,
    get_cold_media_dir,
    get_hot_media_dir,
    get_studio_root,
)
from agvs_core.telemetry_gpx import haversine_m, select_primary_ride_gpx


def parse_gpx_track(gpx_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Parses GPX track, calculating cumulative distances, timestamps, and bounding box."""
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns = {"default": "http://www.topografix.com/GPX/1/1"}

    raw_points: list[dict[str, Any]] = []
    total_dist_m = 0.0
    prev_pt: Optional[tuple[float, float]] = None
    start_time_str: Optional[str] = None

    trkpts = root.findall(".//default:trkpt", ns) or root.findall(".//trkpt")
    for i, pt in enumerate(trkpts):
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        time_elem = pt.find("default:time", ns)
        if time_elem is None:
            time_elem = pt.find("time")
        t_str = time_elem.text if time_elem is not None else None
        if i == 0 and t_str:
            start_time_str = t_str

        if prev_pt:
            total_dist_m += haversine_m(prev_pt[0], prev_pt[1], lat, lon)

        raw_points.append({"lat": lat, "lon": lon, "dist_m": total_dist_m, "time": t_str})
        prev_pt = (lat, lon)

    if not raw_points:
        raise ValueError(f"No valid track points found in {gpx_path}")

    sampled: list[dict[str, Any]] = []
    last_sampled_dist = -999.0
    for p in raw_points:
        if (p["dist_m"] - last_sampled_dist) >= 15.0 or not sampled:
            sampled.append(p)
            last_sampled_dist = p["dist_m"]
    if raw_points and sampled[-1] != raw_points[-1]:
        sampled.append(raw_points[-1])

    meta = {
        "gpx_file": gpx_path.name,
        "total_distance_km": round(total_dist_m / 1000.0, 2),
        "total_distance_mi": round(total_dist_m / 1609.344, 2),
        "total_trackpoints": len(raw_points),
        "sampled_trackpoints": len(sampled),
        "start_time": start_time_str,
        "bbox": {
            "min_lat": min(p["lat"] for p in sampled),
            "max_lat": max(p["lat"] for p in sampled),
            "min_lon": min(p["lon"] for p in sampled),
            "max_lon": max(p["lon"] for p in sampled),
        },
    }
    return sampled, meta


def check_published_status(base_name: str, archival_pulls_dir: Path) -> Optional[Path]:
    """Checks if base_name is already published as a 4K JPEG in LR_Published_4K/."""
    pub_dir = archival_pulls_dir / "LR_Published_4K"
    if not pub_dir.exists():
        return None
    for p in pub_dir.rglob(f"{base_name}.*"):
        if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".tiff"):
            return p
    return None


def get_cached_preview(image_id: int, previews_db_path: Path, previews_root: Path) -> Optional[tuple[Path, int]]:
    """Finds the highest-resolution rendered JPEG cached in Previews.lrdata."""
    if not previews_db_path.exists() or not previews_root.exists():
        return None
    try:
        conn = sqlite3.connect(f"file:{previews_db_path}?mode=ro&nolock=1", uri=True)
        cur = conn.cursor()
        row = cur.execute("SELECT uuid, digest FROM ImageCacheEntry WHERE imageId = ?", (image_id,)).fetchone()
        conn.close()
        if not row:
            return None
        uuid = row[0]
        sub_dir = previews_root / uuid[0] / uuid[:4]
        if not sub_dir.exists():
            return None
        best_file: Optional[Path] = None
        max_res = 0
        for f in sub_dir.glob(f"{uuid}*"):
            m = re.search(r"_(\d+)$", f.name)
            if m:
                res = int(m.group(1))
                if res > max_res:
                    max_res = res
                    best_file = f
        if best_file:
            return best_file, max_res
    except Exception:
        pass
    return None


def query_catalog_flashbacks(
    lrcat_path: Path,
    previews_dir: Path,
    sampled_gpx: list[dict[str, Any]],
    bbox: dict[str, float],
    max_distance_m: float = 100.0,
    min_rating: float = 0.0,
    before_date: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Queries .lrcat in read-only mode for photos inside GPX bounding box and computes route proximity."""
    margin = 0.015
    params: list[Any] = [
        bbox["min_lat"] - margin,
        bbox["max_lat"] + margin,
        bbox["min_lon"] - margin,
        bbox["max_lon"] + margin,
        min_rating,
    ]
    query = """
    SELECT
        img.id_local AS image_id,
        rf.name AS volume_name,
        fo.pathFromRoot AS folder_rel_path,
        fi.baseName,
        fi.extension,
        img.captureTime,
        COALESCE(img.rating, 0) AS rating,
        img.colorLabels,
        exif.gpsLatitude,
        exif.gpsLongitude
    FROM Adobe_images img
    JOIN AgLibraryFile fi ON img.rootFile = fi.id_local
    JOIN AgLibraryFolder fo ON fi.folder = fo.id_local
    JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local
    JOIN AgHarvestedExifMetadata exif ON exif.image = img.id_local
    WHERE exif.hasGPS = 1
      AND exif.gpsLatitude BETWEEN ? AND ?
      AND exif.gpsLongitude BETWEEN ? AND ?
      AND COALESCE(img.rating, 0) >= ?
    """
    if before_date:
        query += " AND img.captureTime < ?"
        params.append(before_date)

    conn = sqlite3.connect(f"file:{lrcat_path.resolve()}?mode=ro&nolock=1", uri=True)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(query, params).fetchall()
    conn.close()

    archival_pulls_dir = get_archival_pulls_dir()
    previews_db = previews_dir / "previews.db"

    results: list[dict[str, Any]] = []
    for r in rows:
        plat, plon = r["gpsLatitude"], r["gpsLongitude"]
        min_d = 999999.0
        closest_pt: Optional[dict[str, Any]] = None
        for pt in sampled_gpx:
            d = haversine_m(plat, plon, pt["lat"], pt["lon"])
            if d < min_d:
                min_d = d
                closest_pt = pt

        if min_d <= max_distance_m and closest_pt:
            base_name = r["baseName"]
            capture_time = r["captureTime"]
            year = capture_time[:4] if capture_time else "Unknown"
            published_path = check_published_status(base_name, archival_pulls_dir)
            preview_info = get_cached_preview(r["image_id"], previews_db, previews_dir)
            preview_path, preview_res = preview_info if preview_info else (None, None)

            results.append(
                {
                    "image_id": r["image_id"],
                    "base_name": base_name,
                    "extension": r["extension"],
                    "capture_time": capture_time,
                    "year": year,
                    "rating": r["rating"],
                    "distance_m": round(min_d, 1),
                    "route_km": round(closest_pt["dist_m"] / 1000.0, 2),
                    "route_mi": round(closest_pt["dist_m"] / 1609.344, 2),
                    "is_published": published_path is not None,
                    "published_path": str(published_path) if published_path else None,
                    "has_preview": preview_path is not None,
                    "preview_path": str(preview_path) if preview_path else None,
                    "preview_res": preview_res,
                    "lat": plat,
                    "lon": plon,
                }
            )
    return results


def cluster_and_rank(candidates: list[dict[str, Any]], cluster_radius_m: float = 35.0) -> list[dict[str, Any]]:
    """Groups multiple photos taken at the same spot on the same day into a single cluster."""
    clusters: list[dict[str, Any]] = []
    for c in sorted(candidates, key=lambda item: item["route_km"]):
        c_date = c["capture_time"][:10] if c.get("capture_time") else "Unknown"
        matched_cluster = None
        for cl in clusters:
            if cl["date"] == c_date and abs(cl["route_km"] - c["route_km"]) * 1000.0 <= cluster_radius_m:
                matched_cluster = cl
                break
        if matched_cluster:
            matched_cluster["photos"].append(c)
            hero = matched_cluster["hero"]
            if (c["is_published"] and not hero["is_published"]) or (c["rating"] > hero["rating"]):
                matched_cluster["hero"] = c
        else:
            clusters.append(
                {
                    "date": c_date,
                    "route_km": c["route_km"],
                    "route_mi": c["route_mi"],
                    "hero": c,
                    "photos": [c],
                }
            )

    def _sort_key(cl: dict[str, Any]) -> float:
        h = cl["hero"]
        pub_score = 10 if h["is_published"] else 0
        dist_score = max(0.0, 100.0 - h["distance_m"]) / 100.0
        return -(pub_score + h["rating"] + dist_score)

    clusters.sort(key=_sort_key)
    return clusters


def stage_previews(clusters: list[dict[str, Any]], out_dir: Path) -> list[dict[str, Any]]:
    """Links/copies cached preview JPEGs into .flashback_candidates/ for instant review."""
    out_dir.mkdir(parents=True, exist_ok=True)
    staged: list[dict[str, Any]] = []
    for rank, cl in enumerate(clusters, start=1):
        h = cl["hero"]
        dest_path = out_dir / f"flashback_{rank:02d}_{h['base_name']}_{h['year']}_{int(h['rating'])}star.jpg"

        if h["is_published"] and h["published_path"]:
            src = Path(h["published_path"])
            try:
                if dest_path.exists() or dest_path.is_symlink():
                    dest_path.unlink()
                dest_path.symlink_to(src)
                h["staged_preview"] = str(dest_path)
                staged.append(h)
                continue
            except Exception:
                pass

        if h["preview_path"]:
            src = Path(h["preview_path"])
            if src.exists():
                try:
                    if dest_path.exists() or dest_path.is_symlink():
                        dest_path.unlink()
                    shutil.copy2(src, dest_path)
                    h["staged_preview"] = str(dest_path)
                    staged.append(h)
                except Exception as exc:
                    print(f"Warning copying preview {src}: {exc}", file=sys.stderr)
    return staged


def render_markdown_report(clusters: list[dict[str, Any]], meta: dict[str, Any], limit: int = 8) -> str:
    rated_clusters = [cl for cl in clusters if cl["hero"]["is_published"] or cl["hero"]["rating"] >= 3]
    unrated_clusters = [cl for cl in clusters if not cl["hero"]["is_published"] and cl["hero"]["rating"] < 3]

    lines = [
        f"### GPX Flashback Discoveries (`{meta['gpx_file']}` — {meta['total_distance_km']} km / {meta['total_distance_mi']} mi)",
        f"*Scanned {len(clusters)} location clusters across your Lightroom Catalog:*",
        "",
        "#### Part 1: Published & High-Rated Flashbacks (Ready to Cut)",
        "| Rank | Date & Era | Rating | Location / Route | Distance | File & Source | Status & Action |",
        "| :---: | :--- | :---: | :--- | :---: | :--- | :--- |",
    ]
    for i, cl in enumerate(rated_clusters[:limit], start=1):
        h = cl["hero"]
        date_str = h["capture_time"][:10] if h["capture_time"] else "Unknown"
        age_years = datetime.now().year - int(h["year"]) if str(h["year"]).isdigit() else ""
        age_tag = f"({age_years} yrs ago)" if age_years else ""
        stars = "★" * int(h["rating"]) + "☆" * (5 - int(h["rating"])) if h["rating"] > 0 else "Unrated"
        count_note = f" (+{len(cl['photos']) - 1} shots)" if len(cl["photos"]) > 1 else ""
        loc_str = f"km {h['route_km']} (mi {h['route_mi']})"
        dist_str = f"{h['distance_m']}m away"
        file_str = f"`{h['base_name']}.{h['extension']}`{count_note}"
        if h["is_published"]:
            status_str = "**4K Published** (Ready to Cut)"
        elif h["preview_res"]:
            status_str = f"{h['preview_res']}px Preview Cached (Rate & Publish in LR)"
        else:
            status_str = "RAW in Catalog"
        lines.append(f"| **#{i:02d}** | {date_str} {age_tag} | `{stars}` | {loc_str} | {dist_str} | {file_str} | {status_str} |")

    if unrated_clusters:
        lines.extend(
            [
                "",
                "#### Part 2: Unrated Hidden Gems Along Your Route (Scavenged Candidates)",
                "| Rank | Date & Era | Rating | Location / Route | Distance | File & Source | Preview Available |",
                "| :---: | :--- | :---: | :--- | :---: | :--- | :--- |",
            ]
        )
        for j, cl in enumerate(unrated_clusters[:6], start=1):
            h = cl["hero"]
            date_str = h["capture_time"][:10] if h["capture_time"] else "Unknown"
            age_years = datetime.now().year - int(h["year"]) if str(h["year"]).isdigit() else ""
            age_tag = f"({age_years} yrs ago)" if age_years else ""
            count_note = f" (+{len(cl['photos']) - 1} shots)" if len(cl["photos"]) > 1 else ""
            loc_str = f"km {h['route_km']} (mi {h['route_mi']})"
            dist_str = f"{h['distance_m']}m away"
            file_str = f"`{h['base_name']}.{h['extension']}`{count_note}"
            prev_str = f"{h['preview_res']}px in `.flashback_candidates/`" if h["preview_res"] else "None"
            lines.append(f"| **#{j:02d}** | {date_str} {age_tag} | `Unrated` | {loc_str} | {dist_str} | {file_str} | {prev_str} |")

    lines.extend(
        [
            "",
            "> **Co-Creation Flashback Law:**",
            "> Select any candidate number to weave into `Storyboard.md` via relative symlink from `LR_Published_4K/`.",
        ]
    )
    return "\n".join(lines)


def ensure_lightroom_closed(lrcat_path: Path) -> None:
    """Prevents SQLite lock contention when running full catalog indexing."""
    res = subprocess.run(["pgrep", "-f", "Adobe Lightroom Classic"], capture_output=True, text=True, check=False)
    lock_file = lrcat_path.with_suffix(lrcat_path.suffix + ".lock")
    if (res.returncode == 0 and res.stdout.strip()) or lock_file.exists():
        sys.exit(
            f"ABORT: Adobe Lightroom Classic is currently open (detected {lock_file.name}). "
            "Close Lightroom before indexing .lrcat."
        )


def index_lrcat(lrcat_path: Path, out_json: Path) -> dict[str, Any]:
    """Reads Adobe Lightroom Classic (.lrcat) in read-only mode and indexes archival stock."""
    ensure_lightroom_closed(lrcat_path)
    uri = f"file:{lrcat_path.resolve()}?mode=ro&nolock=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row

    query = """
    SELECT
        img.id_local AS image_id,
        rf.name AS volume_name,
        fo.pathFromRoot AS folder_rel_path,
        fi.baseName AS base_name,
        fi.extension AS ext,
        img.captureTime AS capture_time,
        COALESCE(img.rating, 0) AS rating,
        img.colorLabels AS color_label,
        img.fileWidth AS width,
        img.fileHeight AS height,
        GROUP_CONCAT(DISTINCT kw.name) AS keywords,
        GROUP_CONCAT(DISTINCT pc.name) AS published_collections
    FROM Adobe_images img
    JOIN AgLibraryFile fi ON img.rootFile = fi.id_local
    JOIN AgLibraryFolder fo ON fi.folder = fo.id_local
    JOIN AgLibraryRootFolder rf ON fo.rootFolder = rf.id_local
    LEFT JOIN AgLibraryKeywordImage kwi ON kwi.image = img.id_local
    LEFT JOIN AgLibraryKeyword kw ON kw.id_local = kwi.tag
    LEFT JOIN AgLibraryPublishedCollectionContent pcc ON pcc.image = img.id_local
    LEFT JOIN AgLibraryPublishedCollection pc ON pc.id_local = pcc.collection
    WHERE COALESCE(img.rating, 0) >= 3
       OR img.captureTime < '1990-01-01'
       OR pc.name IN ('Best-Pics', 'Last-Year', 'Body Transformation')
       OR pc.name LIKE '%Stock%'
       OR pc.name LIKE '%Video-4k%'
    GROUP BY img.id_local
    ORDER BY img.captureTime DESC;
    """
    rows = [dict(r) for r in conn.execute(query).fetchall()]
    conn.close()

    payload = {"total_indexed": len(rows), "photos": rows}
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Indexed {len(rows)} high-value Lightroom photos across all eras into {out_json}")
    return payload


def fetch_clip(video_id: str, start_sec: float, end_sec: float, out_dir: Path, label: str = "broll") -> Path:
    """Surgically downloads a specific timestamp window from a YouTube archival video via yt-dlp."""
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"YT_{video_id}_{label}_{int(start_sec)}s_{int(end_sec)}s"
    out_template = str(out_dir / f"{stem}.%(ext)s")
    url = f"https://www.youtube.com/watch?v={video_id}"
    section_arg = f"*{start_sec}-{end_sec}"
    yt_dlp_bin = find_binary("yt-dlp", required=False) or "yt-dlp"

    cmd = [
        yt_dlp_bin,
        "--download-sections",
        section_arg,
        "--force-keyframes-at-cuts",
        "-f",
        "bestvideo[ext=mp4][height<=2160]+bestaudio[ext=m4a]/best[ext=mp4]",
        "--merge-output-format",
        "mp4",
        "-o",
        out_template,
        url,
    ]
    subprocess.run(cmd, check=True)
    print(f"Downloaded archival B-roll slice from {url} ({section_arg}) -> {out_dir}")
    return out_dir / f"{stem}.mp4"


def relink_json_file(file_path: Path, old_prefix: str, new_prefix: str) -> bool:
    """Safely updates file paths inside UTF-8 JSON files (.fcproj and project_manifest.json)."""
    if not file_path.exists():
        return False
    raw_text = file_path.read_text(encoding="utf-8")
    count = raw_text.count(old_prefix)
    if count == 0:
        print(f"No paths matching '{old_prefix}' found in {file_path.name}.")
        return False
    backup_path = file_path.with_suffix(file_path.suffix + ".bak")
    shutil.copy2(file_path, backup_path)
    updated_text = raw_text.replace(old_prefix, new_prefix)
    json.loads(updated_text)
    file_path.write_text(updated_text, encoding="utf-8")
    print(f"Updated {count} media path references in {file_path} (backup at {backup_path.name}).")
    return True


def relink_resolve_active_project(new_folder_path: str) -> None:
    """Calls DaVinci Resolve Scripting API mediaPool.RelinkClips() if Resolve is running."""
    resolve_modules = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules")
    if not resolve_modules.exists():
        return
    if str(resolve_modules) not in sys.path:
        sys.path.append(str(resolve_modules))
    try:
        import DaVinciResolveScript as dvr_script  # type: ignore[import-not-found]

        resolve = dvr_script.scriptapp("Resolve")
        if not resolve:
            return
        pm = resolve.GetProjectManager()
        proj = pm.GetCurrentProject()
        if not proj:
            return
        mp = proj.GetMediaPool()
        root_bin = mp.GetRootFolder()

        def collect_clips(folder: Any) -> list[Any]:
            items = list(folder.GetClipList() or [])
            for sub in folder.GetSubFolderList() or []:
                items.extend(collect_clips(sub))
            return items

        all_clips = collect_clips(root_bin)
        if all_clips:
            ok = mp.RelinkClips(all_clips, new_folder_path)
            print(f"DaVinci Resolve RelinkClips({len(all_clips)} items -> {new_folder_path}): {ok}")
    except Exception as exc:
        print(f"Note: DaVinci Resolve live relink skipped ({exc}).")


def relink_project_archive(project_catalog_dir: Path, media_subfolder: str, direction: str = "to-external") -> list[Path]:
    """Relinks .fcproj and project_manifest.json between Tier 2 hot media and Tier 3 cold archive."""
    cat_dir = project_catalog_dir.expanduser().resolve()
    local_root = str(get_hot_media_dir())
    external_root = str(get_cold_media_dir())
    old_root, new_root = (local_root, external_root) if direction == "to-external" else (external_root, local_root)

    updated: list[Path] = []
    for fcproj in sorted(cat_dir.glob("*.fcproj")):
        if relink_json_file(fcproj, old_root, new_root):
            updated.append(fcproj)
    manifest_p = cat_dir / "project_manifest.json"
    if relink_json_file(manifest_p, old_root, new_root):
        updated.append(manifest_p)

    target_media_dir = f"{new_root}/{media_subfolder.strip('/')}"
    relink_resolve_active_project(target_media_dir)
    return updated


def flashbacks_cli_main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Find Lightroom flashbacks along GPX route")
    p.add_argument("--gpx", help="Path to GPX file")
    p.add_argument("--project-dir", help="Project directory (locates GPX and stages candidate previews)")
    p.add_argument("--max-distance", type=float, default=100.0, help="Max distance in meters from route (default: 100m)")
    p.add_argument("--min-rating", type=float, default=0.0, help="Min rating (default: 0.0 to surface unrated gems)")
    p.add_argument("--before-date", help="Only photos captured before this date (YYYY-MM-DD)")
    p.add_argument("--limit", type=int, default=12, help="Max flashback clusters to return (default: 12)")
    p.add_argument("--extract-previews", action="store_true", help="Stage preview JPEGs into .flashback_candidates/")
    p.add_argument("--out-json", help="Path to write JSON results")
    args = p.parse_args(argv)

    gpx_file: Optional[Path] = None
    if args.gpx:
        gpx_file = Path(args.gpx).expanduser().resolve()
    elif args.project_dir:
        p_dir = Path(args.project_dir).expanduser().resolve()
        primary_gpx, _ = select_primary_ride_gpx(p_dir, project_name=p_dir.name)
        gpx_file = primary_gpx

    if not gpx_file or not gpx_file.exists():
        print("No GPX file found. Provide --gpx <path> or --project-dir <path> with a .gpx track.", file=sys.stderr)
        return

    active = find_active_lightroom_catalog()
    if not active:
        print("No active Lightroom catalog found in studio.conf ('lightroom_catalog_dir'). Skipping flashback discovery.")
        return

    lrcat_path, previews_dir = active
    print(f"Scanning GPX: {gpx_file.name} against Lightroom: {lrcat_path.name}...")

    sampled_gpx, meta = parse_gpx_track(gpx_file)
    before_date = args.before_date
    if not before_date and meta.get("start_time"):
        before_date = str(meta["start_time"])[:10]
    elif not before_date and args.project_dir:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(args.project_dir).name)
        if m:
            before_date = m.group(1)

    candidates = query_catalog_flashbacks(
        lrcat_path=lrcat_path,
        previews_dir=previews_dir,
        sampled_gpx=sampled_gpx,
        bbox=meta["bbox"],
        max_distance_m=args.max_distance,
        min_rating=args.min_rating,
        before_date=before_date,
    )
    clusters = cluster_and_rank(candidates)
    rated_clusters = [cl for cl in clusters if cl["hero"]["is_published"] or cl["hero"]["rating"] >= 3]
    unrated_clusters = [cl for cl in clusters if not cl["hero"]["is_published"] and cl["hero"]["rating"] < 3]
    top_clusters = rated_clusters[: args.limit] + unrated_clusters[:6]

    if args.extract_previews and args.project_dir:
        stage_dir = Path(args.project_dir).expanduser().resolve() / ".flashback_candidates"
        stage_previews(top_clusters, stage_dir)
        print(f"Staged {len(top_clusters)} candidate preview JPEGs into {stage_dir}")

    print("\n" + render_markdown_report(clusters, meta, limit=args.limit) + "\n")

    if args.out_json:
        out_p = Path(args.out_json).expanduser().resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(
            json.dumps({"metadata": meta, "total_clusters": len(clusters), "clusters": clusters[: args.limit]}, indent=2),
            encoding="utf-8",
        )
        print(f"Saved JSON results to {out_p}")


def index_lrcat_cli_main(argv: Optional[list[str]] = None) -> None:
    active = find_active_lightroom_catalog()
    default_lrcat = str(active[0]) if active else ""
    p = argparse.ArgumentParser(description="Read-only Adobe Lightroom Classic (.lrcat) stock indexer")
    p.add_argument("--lrcat", default=default_lrcat, help="Path to your Lightroom Classic .lrcat file")
    p.add_argument(
        "--out",
        default=str(get_studio_root() / "00_Archive_Indexes/lightroom_stock_index.json"),
        help="Output JSON index path",
    )
    args = p.parse_args(argv)
    if not args.lrcat:
        sys.exit("No --lrcat specified and no active Lightroom catalog configured in studio.conf.")
    index_lrcat(Path(args.lrcat).expanduser(), Path(args.out).expanduser())


def fetch_yt_broll_cli_main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Download surgical YouTube B-roll timestamp slice into Archival_Pulls")
    p.add_argument("--video-id", required=True, help="YouTube Video ID from youtube_motion_index.jsonl or Storyboard.md")
    p.add_argument("--start", type=float, required=True, help="Start time in seconds")
    p.add_argument("--end", type=float, required=True, help="End time in seconds")
    p.add_argument("--label", default="broll", help="Short descriptive tag (e.g. SJC_Olive_Jacket_2025)")
    p.add_argument("--out-dir", default=str(get_archival_pulls_dir()))
    args = p.parse_args(argv)
    fetch_clip(args.video_id, args.start, args.end, Path(args.out_dir).expanduser(), args.label)


def relink_cli_main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Relink video project between hot media dir and cold external archive.")
    p.add_argument("--project-catalog-dir", required=True, help="Path to 04_Project_Catalog/YEAR/YYYY-MM-DD_<name>")
    p.add_argument("--direction", choices=["to-external", "to-local"], default="to-external")
    p.add_argument("--media-subfolder", required=True, help="Relative subfolder, e.g. 2026/2026-10-27_Buger_coffee")
    args = p.parse_args(argv)
    relink_project_archive(Path(args.project_catalog_dir), args.media_subfolder, direction=args.direction)
