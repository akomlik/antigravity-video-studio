"""
agvs_core/services/project_service.py
Stateless project discovery, schema-validated inspection, and Hot/Cold archive relinking.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from agvs_core.config import get_project_catalog_root, get_studio_root, to_studio_relpath
from agvs_core.flashback_lrcat import relink_project_archive
from agvs_core.schemas import ProjectManifest, StoryboardTuningSpec, TimelineSpec


def list_projects(year: Optional[str] = None, studio_root: Optional[Path] = None) -> list[dict[str, Any]]:
    """Lists all catalog projects under `04_Project_Catalog/` (optionally filtered by year)."""
    cat_root = (studio_root / "04_Project_Catalog") if studio_root else get_project_catalog_root()
    if not cat_root.exists():
        return []

    year_dirs = [cat_root / year] if year else sorted(d for d in cat_root.iterdir() if d.is_dir() and not d.name.startswith("."))
    projects: list[dict[str, Any]] = []
    for y_dir in year_dirs:
        if not y_dir.exists():
            continue
        for p_dir in sorted(d for d in y_dir.iterdir() if d.is_dir() and not d.name.startswith(".")):
            projects.append(
                {
                    "project_id": p_dir.name,
                    "year": y_dir.name,
                    "catalog_relpath": to_studio_relpath(p_dir),
                    "has_storyboard": (p_dir / "Storyboard.md").exists(),
                    "has_manifest": (p_dir / "project_manifest.json").exists(),
                    "has_timeline_spec": (p_dir / "timeline_spec.json").exists(),
                    "has_fcproj": any(p_dir.glob("*.fcproj")),
                    "has_youtube_metadata": (p_dir / "youtube_metadata.json").exists(),
                }
            )
    return projects


def resolve_project_catalog_dir(project_ref: str | Path, studio_root: Optional[Path] = None) -> Path:
    """Resolves a project ID, catalog path, or hot-media path to its `04_Project_Catalog/YEAR/<name>` folder."""
    root = studio_root or get_studio_root()
    p = Path(project_ref).expanduser()
    if p.exists() and (p / "project_manifest.json").exists() and "04_Project_Catalog" in str(p.resolve()):
        return p.resolve()
    cand_rel = root / p
    if cand_rel.exists() and cand_rel.is_dir():
        return cand_rel.resolve()
    name = p.name
    matches = sorted((root / "04_Project_Catalog").glob(f"*/{name}"))
    if matches:
        return matches[0].resolve()
    if p.exists():
        return p.resolve()
    raise FileNotFoundError(f"Project catalog directory not found for: {project_ref}")


def inspect_project(project_ref: str | Path, studio_root: Optional[Path] = None) -> dict[str, Any]:
    """Loads and validates a project's manifest, timeline_spec, and Storyboard Section 5 tuning spec."""
    cat_dir = resolve_project_catalog_dir(project_ref, studio_root=studio_root)
    manifest_path = cat_dir / "project_manifest.json"
    spec_path = cat_dir / "timeline_spec.json"
    storyboard_path = cat_dir / "Storyboard.md"

    manifest = ProjectManifest.from_file(manifest_path) if manifest_path.exists() else None
    spec = TimelineSpec.from_file(spec_path, manifest=manifest) if spec_path.exists() else None
    tuning = StoryboardTuningSpec.from_storyboard_file(storyboard_path) if storyboard_path.exists() else None

    return {
        "project_id": cat_dir.name,
        "catalog_relpath": to_studio_relpath(cat_dir),
        "manifest": manifest,
        "timeline_spec": spec,
        "storyboard_tuning": tuning,
        "cut_count": len(spec.cuts) if spec else 0,
        "hud_mode": spec.hud_mode if spec else None,
        "edition_visual_mode": spec.edition_visual_mode if spec else None,
    }


def relink_archive(project_catalog_dir: Path, media_subfolder: str, direction: str = "to-external") -> list[Path]:
    """Relinks `.fcproj` and `project_manifest.json` between Tier 2 hot media and Tier 3 cold archive."""
    return relink_project_archive(project_catalog_dir, media_subfolder, direction=direction)
