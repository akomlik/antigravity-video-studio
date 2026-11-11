"""
agvs_core/services/publish_service.py
Cockpit & CLI service layer for Stage 2 release staging and human-gated YouTube / Flickr publishing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from agvs_core.config import get_exports_dir
from agvs_core.flickr_pub import extract_project_metadata, upload_video_to_flickr
from agvs_core.services.events import ProgressCallback, ProgressEvent, noop_progress
from agvs_core.services.project_service import resolve_project_catalog_dir
from agvs_core.youtube_pub import (
    DEFAULT_YOUTUBE_PRIVACY_STATUS,
    generate_project_youtube_metadata,
    upload_cli_main,
)


class HumanApprovalRequiredError(PermissionError):
    """Raised when `publish_youtube` or `publish_flickr` is called without an explicit human approval token."""


def _require_human_approval(token: Optional[str], target: str) -> None:
    if token is None or not str(token).strip():
        raise HumanApprovalRequiredError(
            f"MANDATORY HUMAN APPROVAL GATE: Refusing automated {target} upload without an explicit "
            "non-empty `human_approved_token`."
        )


def stage_release_bundle(
    project_ref: str | Path,
    mp4_path: Optional[Path] = None,
    thumb_mode: str = "preserve",
    thumb_text: Optional[str] = None,
    thumb_text_ua: Optional[str] = None,
    thumb_text_ru: Optional[str] = None,
    on_progress: ProgressCallback = noop_progress,
) -> Path:
    """Stages `youtube_metadata.json`, `.srt` captions, localized thumbnails, and `facebook_promo.md` with zero network uploads."""
    cat_dir = resolve_project_catalog_dir(project_ref)
    year = cat_dir.parent.name
    resolved_mp4 = mp4_path or (get_exports_dir(year) / f"{cat_dir.name}.mp4")
    on_progress(ProgressEvent("publish", "stage", 25.0, f"Staging metadata & promo bundle for {cat_dir.name}"))
    meta_path = generate_project_youtube_metadata(
        project_dir=cat_dir,
        mp4_path=resolved_mp4,
        thumb_mode=thumb_mode,
        thumb_text=thumb_text,
        thumb_text_ua=thumb_text_ua,
        thumb_text_ru=thumb_text_ru,
    )
    on_progress(ProgressEvent("publish", "staged", 100.0, f"Release bundle staged at {meta_path.name}"))
    return meta_path


def publish_youtube(
    project_ref: str | Path,
    human_approved_token: Optional[str] = None,
    privacy_status: str = DEFAULT_YOUTUBE_PRIVACY_STATUS,
    option_b: bool = False,
    update_video_id: Optional[str] = None,
    on_progress: ProgressCallback = noop_progress,
) -> Path:
    """
    Uploads 1 (`en_only`/`option_a`) or 3 (`option_b`) 4K editions to YouTube Data API v3.
    Strictly enforces the Mandatory Human Approval Gate and defaults `privacy_status` to `"unlisted"`.
    """
    _require_human_approval(human_approved_token, "YouTube")
    cat_dir = resolve_project_catalog_dir(project_ref)
    meta_path = cat_dir / "youtube_metadata.json"
    if not meta_path.exists():
        raise FileNotFoundError(f"youtube_metadata.json not found in {cat_dir}; run stage_release_bundle() first.")

    argv = ["--metadata", str(meta_path), "--privacy", privacy_status or DEFAULT_YOUTUBE_PRIVACY_STATUS]
    if option_b:
        argv.append("--option-b")
    if update_video_id:
        argv.extend(["--update-video-id", update_video_id])

    on_progress(ProgressEvent("publish", "youtube_upload", 40.0, f"Uploading {cat_dir.name} to YouTube ({privacy_status})"))
    upload_cli_main(argv)
    on_progress(ProgressEvent("publish", "youtube_complete", 100.0, f"YouTube release complete for {cat_dir.name}"))
    return meta_path


def publish_flickr(
    project_ref: str | Path,
    human_approved_token: Optional[str] = None,
    edition: str = "ru",
    privacy: str = "public",
    album: Optional[str] = None,
    on_progress: ProgressCallback = noop_progress,
) -> dict[str, Any]:
    """Uploads `<project>_RU.mp4` (or English master) to Flickr after explicit human approval."""
    _require_human_approval(human_approved_token, "Flickr")
    cat_dir = resolve_project_catalog_dir(project_ref)
    meta = extract_project_metadata(cat_dir, edition=edition)
    on_progress(ProgressEvent("publish", "flickr_upload", 40.0, f"Uploading {cat_dir.name} ({edition}) to Flickr"))
    photo_id = upload_video_to_flickr(
        video_path=Path(meta["video_path"]),
        title=meta["title"],
        description=meta["description"],
        tags=meta["tags"],
        privacy=privacy,
    )
    on_progress(ProgressEvent("publish", "flickr_complete", 100.0, f"Flickr upload complete (photo_id={photo_id})"))
    return {"photo_id": photo_id, "album": album, "metadata": meta}
