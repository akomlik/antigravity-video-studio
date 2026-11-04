#!/usr/bin/env python3
"""
index_lightroom_catalog.py
Safely reads the Adobe Lightroom Classic (.lrcat) SQLite database in read-only mode
to index Published Collections, 1977+ B&W film scans, 1980-1984 university photos,
events, hikes, and cycling archives.
"""

import argparse
import json
import sqlite3
import subprocess
import sys
from pathlib import Path


def ensure_lightroom_closed(lrcat_path: Path):
    """Prevents SQLite lock contention by checking if Lightroom is running or lock file exists on macOS."""
    res = subprocess.run(["pgrep", "-f", "Adobe Lightroom Classic"], capture_output=True, text=True)
    lock_file = lrcat_path.with_suffix(lrcat_path.suffix + ".lock")
    if (res.returncode == 0 and res.stdout.strip()) or lock_file.exists():
        sys.exit(
            f"ABORT: Adobe Lightroom Classic is currently open (detected {lock_file.name}). "
            "Close Lightroom before indexing .lrcat."
        )


def index_lrcat(lrcat_path: Path, out_json: Path):
    ensure_lightroom_closed(lrcat_path)
    uri = f"file:{lrcat_path.resolve()}?mode=ro&nolock=1"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    query = """
    SELECT
        img.id_local AS image_id,
        rf.name AS volume_name,
        rf.absolutePath || fo.pathFromRoot || fi.baseName || '.' || fi.extension AS source_path,
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

    rows = [dict(r) for r in cur.execute(query).fetchall()]
    conn.close()

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({"total_indexed": len(rows), "photos": rows}, indent=2), encoding="utf-8")
    print(f"Indexed {len(rows)} high-value Lightroom photos across all eras into {out_json}")


if __name__ == "__main__":
    import os
    studio_root = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
    p = argparse.ArgumentParser()
    p.add_argument(
        "--lrcat",
        default="~/Pictures/Lightroom/Lightroom Catalog-v13-3.lrcat",
        help="Path to your Lightroom Classic .lrcat file"
    )
    p.add_argument(
        "--out",
        default=str(studio_root / "00_Archive_Indexes/lightroom_stock_index.json")
    )
    args = p.parse_args()
    index_lrcat(Path(args.lrcat).expanduser(), Path(args.out).expanduser())
