"""Pydantic v2 schema for `project_manifest.json` (`agvs_core/schemas/manifest.py`)."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from agvs_core.config import ensure_no_raw_voice_id, ensure_relative_studio_path


class SecuritySchemaError(RuntimeError):
    """Raised when an absolute machine path or raw biometric voice_id secret is detected in a project schema."""


def _check_rel_path(val: Optional[str]) -> Optional[str]:
    if val is None or val == "":
        return val
    try:
        return ensure_relative_studio_path(val)
    except ValueError as exc:
        raise SecuritySchemaError(str(exc)) from exc


def _check_no_voice_secret(val: Optional[str]) -> Optional[str]:
    if val is None:
        return val
    try:
        return ensure_no_raw_voice_id(val)
    except ValueError as exc:
        raise SecuritySchemaError(str(exc)) from exc


class SubClipSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    start_s: float = 0.0
    end_s: Optional[float] = None
    dur_s: Optional[float] = None
    label: str = ""
    proxy_thumb: Optional[str] = None

    @field_validator("proxy_thumb")
    @classmethod
    def _validate_rel(cls, v: Optional[str]) -> Optional[str]:
        return _check_rel_path(v)


class LandmarkWindowSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    name: str
    timestamp_range: list[float] = Field(default_factory=list)


class EditorialTelemetry(BaseModel):
    model_config = ConfigDict(extra="allow")

    in_gpx_ride_window: Optional[bool] = None
    matched_gpx_utc: Optional[str] = None
    distance_km: Optional[float] = None
    distance_mi: Optional[float] = None
    elevation_m: Optional[float] = None
    elevation_ft: Optional[float] = None
    speed_mph: Optional[float] = None
    grade_pct: Optional[float] = None
    heart_rate_bpm: Optional[int] = None
    power_w: Optional[int] = None


class MediaInventoryItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    filename: str
    relpath: Optional[str] = None
    media_type: str
    source_device: Optional[str] = None
    creation_time_utc: Optional[str] = None
    camera_tz_offset: Optional[str] = None
    duration_s: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    aspect_ratio: Optional[str] = None
    fps: Optional[float] = None
    color_space: Optional[str] = None
    qt_lat: Optional[float] = None
    qt_lon: Optional[float] = None
    proxy_thumb: Optional[str] = None
    calibration_clock_only: bool = False
    exclude_from_timeline: bool = False
    editorial: Optional[EditorialTelemetry] = None
    landmarks: list[LandmarkWindowSpec] = Field(default_factory=list)
    subclips: list[SubClipSpec] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_sub_clips(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "sub_clips" in data and "subclips" not in data:
                data = dict(data)
                data["subclips"] = data.pop("sub_clips") or []
        return data

    @field_validator("relpath", "proxy_thumb")
    @classmethod
    def _validate_item_relpaths(cls, v: Optional[str]) -> Optional[str]:
        return _check_rel_path(v)


class ProjectManifest(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_name: str
    year_bucket: Optional[str] = None
    raw_media_folder: str
    catalog_project_dir: str
    storyboard_file: Optional[str] = None
    storyboard_status: Optional[str] = None
    proxy_thumbnails_dir: Optional[str] = None
    detected_genre: str = "cycling_ride"
    gpx_file: Optional[str] = None
    archival_gpx_files: list[str] = Field(default_factory=list)
    music_library_root: Optional[str] = None
    recommended_music_candidates: list[Any] = Field(default_factory=list)
    project_summary: dict[str, Any] = Field(default_factory=dict)
    media_inventory: list[MediaInventoryItem] = Field(default_factory=list)

    @field_validator(
        "raw_media_folder",
        "catalog_project_dir",
        "storyboard_file",
        "proxy_thumbnails_dir",
        "gpx_file",
        "music_library_root",
    )
    @classmethod
    def _validate_manifest_relpaths(cls, v: Optional[str]) -> Optional[str]:
        return _check_rel_path(v)

    @model_validator(mode="after")
    def _scan_for_raw_secrets(self) -> "ProjectManifest":
        blob = json.dumps(self.project_summary, ensure_ascii=False)
        if re.search(r"\bvoice_[A-Za-z0-9]{6,}\b", blob):
            raise SecuritySchemaError("Raw GEMINI_VOICE_ID found in project_summary!")
        return self

    @classmethod
    def from_file(cls, path: Path) -> "ProjectManifest":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)
