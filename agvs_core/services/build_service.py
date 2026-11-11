"""
agvs_core/services/build_service.py
Cockpit & CLI service layer for Stage 1 validation, BGM speaker preview, A2 track swapping, and 4K timeline assembly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from agvs_core.config import find_binary, get_bgm_root, resolve_studio_path
from agvs_core.music_catalog import swap_project_music
from agvs_core.schemas import ProjectManifest, TimelineSpec
from agvs_core.services.events import ProgressCallback, ProgressEvent, noop_progress
from agvs_core.services.project_service import resolve_project_catalog_dir
from agvs_core.timeline_builder import build_project_timeline, verify_zero_project_scripts


def validate_spec(project_ref: str | Path) -> tuple[Optional[ProjectManifest], TimelineSpec]:
    """Runs zero-script preflight plus strict Pydantic v2 validation on `project_manifest.json` & `timeline_spec.json`."""
    cat_dir = resolve_project_catalog_dir(project_ref)
    verify_zero_project_scripts(cat_dir)
    manifest_path = cat_dir / "project_manifest.json"
    spec_path = cat_dir / "timeline_spec.json"
    manifest = ProjectManifest.from_file(manifest_path) if manifest_path.exists() else None
    spec = TimelineSpec.from_file(spec_path, manifest=manifest)
    return manifest, spec


def preview_bgm_command(track_relpath: str, seconds: int = 10) -> list[str]:
    """Builds the macOS `afplay -t <seconds>` command for a relative BGM path."""
    afplay_bin = find_binary("afplay", required=False) or "afplay"
    norm = track_relpath.strip()
    track_path = resolve_studio_path(norm) if norm.startswith("03_Audio_Library/") else (get_bgm_root() / norm)
    return [afplay_bin, "-t", str(seconds), str(track_path)]


def build_and_render_timeline(
    project_ref: str | Path,
    render_export: bool = False,
    mux_audio_only: bool = False,
    open_gui: bool = True,
    on_progress: ProgressCallback = noop_progress,
) -> dict[str, Any]:
    """Validates `timeline_spec.json` and builds `.fcproj` (and optionally exports 4K MP4s after human review)."""
    cat_dir = resolve_project_catalog_dir(project_ref)
    on_progress(ProgressEvent("build", "validate", 10.0, f"Validating declarative spec for {cat_dir.name}"))
    validate_spec(cat_dir)
    on_progress(
        ProgressEvent(
            "build",
            "assemble",
            40.0,
            f"Building timeline for {cat_dir.name} (render_export={render_export})",
        )
    )
    result = build_project_timeline(
        project_dir=cat_dir,
        render_export=render_export,
        mux_audio_only=mux_audio_only,
        open_gui=open_gui,
    )
    on_progress(ProgressEvent("build", "complete", 100.0, f"Timeline build finished for {cat_dir.name}"))
    return result


def swap_music(project_ref: str | Path, new_track_relpath: str, on_progress: ProgressCallback = noop_progress) -> Path:
    """Swaps the background music track in `timeline_spec.json` and re-validates the spec."""
    cat_dir = resolve_project_catalog_dir(project_ref)
    on_progress(ProgressEvent("swap_music", "update", 30.0, f"Updating A2 music -> {new_track_relpath}"))
    updated_spec = swap_project_music(cat_dir, new_track_relpath)
    validate_spec(cat_dir)
    on_progress(ProgressEvent("swap_music", "complete", 100.0, f"Validated updated timeline_spec.json in {cat_dir.name}"))
    return updated_spec
