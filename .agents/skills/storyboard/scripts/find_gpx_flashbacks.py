#!/usr/bin/env python3
"""
find_gpx_flashbacks.py
Automated GPX Geospatial Flashback Discovery Engine for Antigravity Video Studio.

Scans the active Adobe Lightroom Classic catalog (.lrcat) along the trajectory of a ride/hike GPX track,
identifying historical candidate memories taken within a spatial corridor (e.g., 50m-100m) of the route.
Supports rated (1★-5★) and unrated photos, checks published 4K status in LR_Published_4K/,
and extracts rendered JPEG previews directly from Previews.lrdata without needing Lightroom to be open.
"""

import argparse
import json
import math
import os
import re
import shutil
import sqlite3
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# Ensure studio root is in sys.path
_studio_root = Path(__file__).resolve().parents[4]
if str(_studio_root) not in sys.path:
    sys.path.insert(0, str(_studio_root))

try:
    from studio_config import (
        find_active_lightroom_catalog,
        get_archival_pulls_dir,
        get_hot_media_dir,
        to_studio_relpath,
    )
except ImportError:
    find_active_lightroom_catalog = lambda: None
    get_archival_pulls_dir = lambda: Path.home() / "Movies/Archival_Pulls"
    get_hot_media_dir = lambda: Path.home() / "Movies"
    to_studio_relpath = lambda p: str(p)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in meters."""
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def parse_gpx_track(gpx_path: Path) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Parses GPX track, calculating cumulative distances, timestamps, and bounding box.
    Returns (sampled_points, metadata).
    """
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns = {"default": "http://www.topografix.com/GPX/1/1"}

    raw_points = []
    total_dist_m = 0.0
    prev_pt = None
    start_time_str = None

    # Search trkpt with or without namespace
    trkpts = root.findall(".//default:trkpt", ns) or root.findall(".//trkpt")

    for i, pt in enumerate(trkpts):
        lat = float(pt.attrib["lat"])
        lon = float(pt.attrib["lon"])
        time_elem = pt.find("default:time", ns) if "default" in ns else None
        if time_elem is None:
            time_elem = pt.find("time")
        t_str = time_elem.text if time_elem is not None else None
        if i == 0 and t_str:
            start_time_str = t_str

        if prev_pt:
            step_d = haversine_m(prev_pt[0], prev_pt[1], lat, lon)
            total_dist_m += step_d

        raw_points.append({
            "lat": lat,
            "lon": lon,
            "dist_m": total_dist_m,
            "time": t_str
        })
        prev_pt = (lat, lon)

    if not raw_points:
        raise ValueError(f"No valid track points found in {gpx_path}")

    # Subsample points roughly every 15-20 meters for swift corridor searching
    sampled = []
    last_sampled_dist = -999.0
    for p in raw_points:
        if (p["dist_m"] - last_sampled_dist) >= 15.0 or not sampled:
            sampled.append(p)
            last_sampled_dist = p["dist_m"]

    # Always ensure the final point is included
    if raw_points and sampled[-1] != raw_points[-1]:
        sampled.append(raw_points[-1])

    min_lat = min(p["lat"] for p in sampled)
    max_lat = max(p["lat"] for p in sampled)
    min_lon = min(p["lon"] for p in sampled)
    max_lon = max(p["lon"] for p in sampled)

    meta = {
        "gpx_file": gpx_path.name,
        "total_distance_km": round(total_dist_m / 1000.0, 2),
        "total_distance_mi": round(total_dist_m / 1609.344, 2),
        "total_trackpoints": len(raw_points),
        "sampled_trackpoints": len(sampled),
        "start_time": start_time_str,
        "bbox": {
            "min_lat": min_lat,
            "max_lat": max_lat,
            "min_lon": min_lon,
            "max_lon": max_lon,
        }
    }
    return sampled, meta


def check_published_status(base_name: str, archival_pulls_dir: Path) -> Optional[Path]:
    """Checks if base_name is already published as a 4K JPEG in LR_Published_4K/."""
    pub_dir = archival_pulls_dir / "LR_Published_4K"
    if not pub_dir.exists():
        return None

    # Search for matching files across subfolders (e.g. 05_Stock_Mallorca/APC_0756.jpg)
    for p in pub_dir.rglob(f"{base_name}.*"):
        if p.is_file() and p.suffix.lower() in [".jpg", ".jpeg", ".png", ".tiff"]:
            return p
    return None


def get_cached_preview(
    image_id: int, previews_db_path: Path, previews_root: Path
) -> Optional[Tuple[Path, int]]:
    """
    Finds the highest-resolution rendered JPEG cached in Previews.lrdata.
    Returns (file_path, resolution_px) or None.
    """
    if not previews_db_path.exists() or not previews_root.exists():
        return None

    try:
        conn = sqlite3.connect(f"file:{previews_db_path}?mode=ro&nolock=1", uri=True)
        cur = conn.cursor()
        row = cur.execute(
            "SELECT uuid, digest FROM ImageCacheEntry WHERE imageId = ?", (image_id,)
        ).fetchone()
        conn.close()

        if not row:
            return None

        uuid, digest = row
        sub_dir = previews_root / uuid[0] / uuid[:4]
        if not sub_dir.exists():
            return None

        candidates = list(sub_dir.glob(f"{uuid}*"))
        best_file = None
        max_res = 0

        for f in candidates:
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
    sampled_gpx: List[Dict[str, Any]],
    bbox: Dict[str, float],
    max_distance_m: float = 100.0,
    min_rating: float = 0.0,
    before_date: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Queries .lrcat for photos inside GPX bounding box and computes route proximity."""
    # Bounding box buffer (~1.5 km margin in degrees)
    margin = 0.015
    q_min_lat = bbox["min_lat"] - margin
    q_max_lat = bbox["max_lat"] + margin
    q_min_lon = bbox["min_lon"] - margin
    q_max_lon = bbox["max_lon"] + margin

    conn = sqlite3.connect(f"file:{lrcat_path.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

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
    params = [q_min_lat, q_max_lat, q_min_lon, q_max_lon, min_rating]
    if before_date:
        query += " AND img.captureTime < ?"
        params.append(before_date)

    rows = cur.execute(query, params).fetchall()
    conn.close()

    archival_pulls_dir = get_archival_pulls_dir()
    previews_db = previews_dir / "previews.db"

    results = []
    for r in rows:
        plat, plon = r["gpsLatitude"], r["gpsLongitude"]
        # Find closest point on GPX route
        min_d = 999999.0
        closest_pt = None

        for pt in sampled_gpx:
            d = haversine_m(plat, plon, pt["lat"], pt["lon"])
            if d < min_d:
                min_d = d
                closest_pt = pt

        if min_d <= max_distance_m and closest_pt:
            base_name = r["baseName"]
            capture_time = r["captureTime"]
            year = capture_time[:4] if capture_time else "Unknown"

            # Check published 4K status
            published_path = check_published_status(base_name, archival_pulls_dir)

            # Check cached preview
            preview_info = get_cached_preview(r["image_id"], previews_db, previews_dir)
            preview_path, preview_res = preview_info if preview_info else (None, None)

            results.append({
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
            })

    return results


def cluster_and_rank(candidates: List[Dict[str, Any]], cluster_radius_m: float = 35.0) -> List[Dict[str, Any]]:
    """Groups multiple photos taken at the same spot on the same day into a single cluster."""
    clusters = []

    # Sort primarily by route distance along the ride
    sorted_candidates = sorted(candidates, key=lambda c: c["route_km"])

    for c in sorted_candidates:
        matched_cluster = None
        for cl in clusters:
            # Check if same date and nearby along route
            if cl["date"] == c["capture_time"][:10] and abs(cl["route_km"] - c["route_km"]) * 1000.0 <= cluster_radius_m:
                matched_cluster = cl
                break

        if matched_cluster:
            matched_cluster["photos"].append(c)
            # Promote hero if current photo is higher rated or published
            hero = matched_cluster["hero"]
            if (c["is_published"] and not hero["is_published"]) or (c["rating"] > hero["rating"]):
                matched_cluster["hero"] = c
        else:
            clusters.append({
                "date": c["capture_time"][:10] if c["capture_time"] else "Unknown",
                "route_km": c["route_km"],
                "route_mi": c["route_mi"],
                "hero": c,
                "photos": [c]
            })

    # Sort clusters: Published & High Rating first, then by closest distance to route
    def cluster_sort_key(cl):
        h = cl["hero"]
        pub_score = 10 if h["is_published"] else 0
        rating_score = h["rating"]
        dist_score = max(0.0, 100.0 - h["distance_m"]) / 100.0
        return -(pub_score + rating_score + dist_score)

    clusters.sort(key=cluster_sort_key)
    return clusters


def stage_previews(clusters: List[Dict[str, Any]], out_dir: Path) -> List[Dict[str, Any]]:
    """Copies/symlinks the cached preview JPEGs into .flashback_candidates/ for instant review."""
    out_dir.mkdir(parents=True, exist_ok=True)
    staged = []

    for rank, cl in enumerate(clusters, start=1):
        h = cl["hero"]
        dest_filename = f"flashback_{rank:02d}_{h['base_name']}_{h['year']}_{int(h['rating'])}star.jpg"
        dest_path = out_dir / dest_filename

        # If already published, link to published 4K file
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

        # Otherwise copy/link cached preview JPEG
        if h["preview_path"]:
            src = Path(h["preview_path"])
            if src.exists():
                try:
                    if dest_path.exists() or dest_path.is_symlink():
                        dest_path.unlink()
                    shutil.copy2(src, dest_path)
                    h["staged_preview"] = str(dest_path)
                    staged.append(h)
                except Exception as e:
                    print(f"Warning copying preview {src}: {e}", file=sys.stderr)

    return staged


def render_markdown_report(clusters: List[Dict[str, Any]], meta: Dict[str, Any], limit: int = 8) -> str:
    """Generates an aesthetic Markdown report separating Ready-to-Cut from Unrated Hidden Gems."""
    rated_clusters = [cl for cl in clusters if cl["hero"]["is_published"] or cl["hero"]["rating"] >= 3]
    unrated_clusters = [cl for cl in clusters if not cl["hero"]["is_published"] and cl["hero"]["rating"] < 3]

    lines = [
        f"### 🗺️ GPX Flashback Discoveries (`{meta['gpx_file']}` — {meta['total_distance_km']} km / {meta['total_distance_mi']} mi)",
        f"*Scanned {len(clusters)} location clusters across your Lightroom Catalog:*",
        "",
        "#### 🌟 Part 1: Published & High-Rated Flashbacks (Ready to Cut)",
        "| Rank | Date & Era | Rating | Location / Route | Distance | File & Source | Status & Action |",
        "| :---: | :--- | :---: | :--- | :---: | :--- | :--- |"
    ]

    for i, cl in enumerate(rated_clusters[:limit], start=1):
        h = cl["hero"]
        date_str = h["capture_time"][:10] if h["capture_time"] else "Unknown"
        age_years = datetime.now().year - int(h["year"]) if h["year"].isdigit() else ""
        age_tag = f"({age_years} yrs ago)" if age_years else ""

        stars = "★" * int(h["rating"]) + "☆" * (5 - int(h["rating"])) if h["rating"] > 0 else "Unrated"
        count_note = f" (+{len(cl['photos'])-1} shots)" if len(cl['photos']) > 1 else ""

        loc_str = f"km {h['route_km']} (mi {h['route_mi']})"
        dist_str = f"{h['distance_m']}m away"
        file_str = f"`{h['base_name']}.{h['extension']}`{count_note}"

        if h["is_published"]:
            status_str = "**✅ 4K Published** (Ready to Cut)"
        elif h["preview_res"]:
            status_str = f"⚡ {h['preview_res']}px Preview Cached (Rate & Publish in LR)"
        else:
            status_str = "📷 RAW in Catalog"

        lines.append(f"| **#{i:02d}** | {date_str} {age_tag} | `{stars}` | {loc_str} | {dist_str} | {file_str} | {status_str} |")

    if unrated_clusters:
        lines.append("")
        lines.append("#### 💎 Part 2: Unrated Hidden Gems Along Your Route (Scavenged Candidates)")
        lines.append("| Rank | Date & Era | Rating | Location / Route | Distance | File & Source | Preview Available |")
        lines.append("| :---: | :--- | :---: | :--- | :---: | :--- | :--- |")

        for j, cl in enumerate(unrated_clusters[:6], start=1):
            h = cl["hero"]
            date_str = h["capture_time"][:10] if h["capture_time"] else "Unknown"
            age_years = datetime.now().year - int(h["year"]) if h["year"].isdigit() else ""
            age_tag = f"({age_years} yrs ago)" if age_years else ""
            count_note = f" (+{len(cl['photos'])-1} shots)" if len(cl['photos']) > 1 else ""

            loc_str = f"km {h['route_km']} (mi {h['route_mi']})"
            dist_str = f"{h['distance_m']}m away"
            file_str = f"`{h['base_name']}.{h['extension']}`{count_note}"
            prev_str = f"⚡ {h['preview_res']}px in `.flashback_candidates/`" if h["preview_res"] else "None"

            lines.append(f"| **💎 #{j:02d}** | {date_str} {age_tag} | `Unrated` | {loc_str} | {dist_str} | {file_str} | {prev_str} |")

    lines.append("")
    lines.append("> **💡 Co-Creation Flashback Law:**")
    lines.append("> Select any candidate number (e.g. `Flashback #01` or `💎 #01`) to weave into `Storyboard.md`.")
    lines.append("> If an unrated candidate looks compelling, give it a star rating in Lightroom and click Publish!")
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(description="Find Lightroom flashbacks along GPX route")
    p.add_argument("--gpx", help="Path to GPX file")
    p.add_argument("--project-dir", help="Project directory (locates GPX and stages candidate previews)")
    p.add_argument("--max-distance", type=float, default=100.0, help="Max distance in meters from route (default: 100m)")
    p.add_argument("--min-rating", type=float, default=0.0, help="Min rating (default: 0.0 to surface unrated gems)")
    p.add_argument("--before-date", help="Only photos captured before this date (YYYY-MM-DD)")
    p.add_argument("--limit", type=int, default=12, help="Max flashback clusters to return (default: 12)")
    p.add_argument("--extract-previews", action="store_true", help="Stage preview JPEGs into .flashback_candidates/")
    p.add_argument("--out-json", help="Path to write JSON results")
    args = p.parse_args()

    # Determine GPX path
    gpx_file = None
    if args.gpx:
        gpx_file = Path(args.gpx).expanduser().resolve()
    elif args.project_dir:
        p_dir = Path(args.project_dir).expanduser().resolve()
        gpxs = list(p_dir.glob("*.gpx"))
        if gpxs:
            gpx_file = gpxs[0]

    if not gpx_file or not gpx_file.exists():
        print("No GPX file found. Provide --gpx <path> or --project-dir <path> with a .gpx track.", file=sys.stderr)
        sys.exit(0)

    # Locate Lightroom Catalog
    active = find_active_lightroom_catalog()
    if not active:
        print("No active Lightroom catalog found in studio.conf ('lightroom_catalog_dir'). Skipping flashback discovery.")
        sys.exit(0)

    lrcat_path, previews_dir = active
    print(f"Scanning GPX: {gpx_file.name} against Lightroom: {lrcat_path.name}...")

    sampled_gpx, meta = parse_gpx_track(gpx_file)

    # Determine before_date threshold
    before_date = args.before_date
    if not before_date and meta.get("start_time"):
        before_date = meta["start_time"][:10]
    elif not before_date and args.project_dir:
        # Try folder name date YYYY-MM-DD
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
        before_date=before_date
    )

    clusters = cluster_and_rank(candidates)
    rated_clusters = [cl for cl in clusters if cl["hero"]["is_published"] or cl["hero"]["rating"] >= 3]
    unrated_clusters = [cl for cl in clusters if not cl["hero"]["is_published"] and cl["hero"]["rating"] < 3]
    top_clusters = rated_clusters[:args.limit] + unrated_clusters[:6]

    if args.extract_previews and args.project_dir:
        stage_dir = Path(args.project_dir).expanduser().resolve() / ".flashback_candidates"
        stage_previews(top_clusters, stage_dir)
        print(f"Staged {len(top_clusters)} candidate preview JPEGs into {stage_dir}")

    report = render_markdown_report(clusters, meta, limit=args.limit)
    print("\n" + report + "\n")

    if args.out_json:
        out_p = Path(args.out_json).expanduser().resolve()
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_data = {
            "metadata": meta,
            "total_clusters": len(clusters),
            "clusters": clusters[:args.limit]
        }
        out_p.write_text(json.dumps(out_data, indent=2), encoding="utf-8")
        print(f"Saved JSON results to {out_p}")


if __name__ == "__main__":
    main()
