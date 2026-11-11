"""
agvs_core/services/ingest_service.py
Cockpit & CLI service layer for Stage 0 media ingestion, subclip indexing, and Lightroom flashback discovery.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from agvs_core.ai_creative import process_project_subclips
from agvs_core.config import find_active_lightroom_catalog
from agvs_core.flashback_lrcat import cluster_and_rank, parse_gpx_track, query_catalog_flashbacks, stage_previews
from agvs_core.ingest_sync import ingest_project_media
from agvs_core.services.events import ProgressCallback, ProgressEvent, noop_progress
from agvs_core.telemetry_gpx import select_primary_ride_gpx


def run_ingest(
    project_dir: Path,
    genre: str = "auto",
    skip_bleequp_sync: bool = False,
    force_resync: bool = False,
    mark_calibration: Optional[list[str]] = None,
    on_progress: ProgressCallback = noop_progress,
) -> dict[str, Any]:
    on_progress(ProgressEvent("ingest", "start", 5.0, f"Ingesting media in {project_dir.name}"))
    manifest = ingest_project_media(
        project_dir=project_dir,
        genre=genre,
        skip_bleequp_sync=skip_bleequp_sync,
        force_resync=force_resync,
        mark_calibration=mark_calibration,
    )
    on_progress(
        ProgressEvent(
            "ingest",
            "complete",
            100.0,
            f"Ingested {len(manifest.get('media_inventory', []))} items ({manifest.get('detected_genre')})",
        )
    )
    return manifest


def scan_flashbacks(
    project_dir: Path,
    max_distance_m: float = 100.0,
    min_rating: float = 0.0,
    extract_previews: bool = False,
    on_progress: ProgressCallback = noop_progress,
) -> dict[str, Any]:
    p_dir = project_dir.expanduser().resolve()
    gpx_file, _ = select_primary_ride_gpx(p_dir, project_name=p_dir.name)
    active = find_active_lightroom_catalog()
    if not gpx_file or not active:
        return {"metadata": None, "clusters": []}

    lrcat_path, previews_dir = active
    on_progress(ProgressEvent("flashbacks", "scan", 25.0, f"Scanning {lrcat_path.name} along {gpx_file.name}"))
    sampled_gpx, meta = parse_gpx_track(gpx_file)
    before_date = str(meta.get("start_time") or "")[:10] or None
    candidates = query_catalog_flashbacks(
        lrcat_path=lrcat_path,
        previews_dir=previews_dir,
        sampled_gpx=sampled_gpx,
        bbox=meta["bbox"],
        max_distance_m=max_distance_m,
        min_rating=min_rating,
        before_date=before_date,
    )
    clusters = cluster_and_rank(candidates)
    if extract_previews:
        stage_previews(clusters[:12], p_dir / ".flashback_candidates")
    on_progress(ProgressEvent("flashbacks", "complete", 100.0, f"Found {len(clusters)} flashback location clusters"))
    return {"metadata": meta, "clusters": clusters}


def extract_subclips(project_dir: Path, force: bool = False, on_progress: ProgressCallback = noop_progress) -> bool:
    on_progress(ProgressEvent("subclips", "analyze", 20.0, f"Indexing long clips in {project_dir.name}"))
    updated = process_project_subclips(project_dir.expanduser().resolve(), force=force)
    on_progress(ProgressEvent("subclips", "complete", 100.0, "Subclip indexing finished"))
    return updated
