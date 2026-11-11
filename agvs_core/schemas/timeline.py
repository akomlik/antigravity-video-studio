"""Pydantic v2 schema for declarative `timeline_spec.json` (`agvs_core/schemas/timeline.py`)."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .manifest import ProjectManifest, SecuritySchemaError, _check_no_voice_secret, _check_rel_path


class CalibrationMediaInTimelineError(ValueError):
    """Raised when a timeline cut references media marked `calibration_clock_only` or `exclude_from_timeline`."""


class RouteContinuityError(ValueError):
    """Raised when non-flashback timeline cuts regress along GPX distance or camera chronology."""


class BgmPhaseSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    file: str
    start_s: float = 0.0
    end_s: Optional[float] = None

    @field_validator("file")
    @classmethod
    def _val_file(cls, v: str) -> str:
        return _check_rel_path(v) or v


class BookendsSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    enabled: bool = True
    first_clip: Optional[str] = None
    last_clip: Optional[str] = None
    intro_dur_s: float = 3.5
    outro_dur_s: float = 4.5
    place_name: Optional[str] = None
    place_name_ru: Optional[str] = None
    route_subtitle: Optional[str] = None
    route_subtitle_ru: Optional[str] = None
    short_title: Optional[str] = None
    short_title_ru: Optional[str] = None
    studio_motto: Optional[str] = None
    studio_motto_ru: Optional[str] = None
    cast_credits: list[str] = Field(default_factory=list)
    cast_credits_ru: list[str] = Field(default_factory=list)
    steed_credit: Optional[str] = None
    steed_credit_ru: Optional[str] = None
    fuel_sponsors: Optional[str] = None
    fuel_sponsors_ru: Optional[str] = None


class VoCueSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    start_s: float
    max_dur_s: float = 25.0


class LiveSubtitleSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    start_s: float
    end_s: float
    spoken_lang: Optional[str] = None
    text: dict[str, str] = Field(default_factory=dict)


class BoostedDialogSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    cut_num: int
    source: str
    src_in: float = 0.0
    dur: float
    stem_file: str
    filter: Optional[str] = None
    mix_gain_db: float = 0.0

    @field_validator("source", "stem_file")
    @classmethod
    def _val_rel(cls, v: str) -> str:
        return _check_rel_path(v) or v


class SfxCueSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    file: str
    start_s: float
    gain_db: float = -10.0
    align_peak: bool = False

    @field_validator("file")
    @classmethod
    def _val_rel(cls, v: str) -> str:
        return _check_rel_path(v) or v


class CutSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    cut_num: int
    source: str
    src_in: float = 0.0
    dur: float
    is_still: bool = False
    a1_gain: Optional[float] = None
    desc: str = ""
    framing: Optional[str] = None
    hud: Optional[bool] = None
    allow_out_of_order: bool = False
    ken_burns: Optional[dict[str, Any]] = None

    @field_validator("source")
    @classmethod
    def _val_source(cls, v: str) -> str:
        return _check_rel_path(v) or v

    @field_validator("dur")
    @classmethod
    def _val_dur(cls, v: float) -> float:
        if v <= 0:
            raise ValueError(f"Cut duration must be > 0, got {v}")
        return v


class CharacterBadgeOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["character_badge", "context_card", "stat_callout"]
    file: str
    start_s: float
    dur_s: float
    title: str
    subtitle: str
    title_ru: Optional[str] = None
    subtitle_ru: Optional[str] = None
    position: str = "bottom_left"
    accent: str = "crimson"


class FlashbackBadgeOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["flashback_badge"]
    file: str
    start_s: float
    dur_s: float
    date_event: str
    title: str
    detail: str
    date_event_ru: Optional[str] = None
    title_ru: Optional[str] = None
    detail_ru: Optional[str] = None
    position: str = "top_left"
    accent: str = "crimson"


class StravaComparisonOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["strava_comparison"]
    file: str
    start_s: float
    dur_s: float
    header: Optional[str] = None
    subheader: Optional[str] = None
    badge1: Optional[str] = None
    badge2: Optional[str] = None
    header_ru: Optional[str] = None
    subheader_ru: Optional[str] = None
    badge1_ru: Optional[str] = None
    badge2_ru: Optional[str] = None


class TranslationSubtitleOverlay(BaseModel):
    """Normalizes both Femenia (`spoken`/`translation`/`english`) and Paradise (`spoken_lang`/`english`/`russian`)."""

    model_config = ConfigDict(extra="allow")

    kind: Literal["translation_subtitle"]
    file: str = "sub_card.png"
    start_s: float = 0.0
    dur_s: float = 3.0
    spoken_lang: Optional[str] = None
    spoken: Optional[str] = None
    english: Optional[str] = None
    russian: Optional[str] = None
    translation: Optional[str] = None
    pages: Optional[list[dict[str, Any]]] = None


class LiveTelemetryHudOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["live_telemetry_hud", "telemetry_hud"]
    start_s: float
    dur_s: float
    gpx_file: Optional[str] = None
    gpx_start_idx: Optional[int] = None
    metrics_profile: Optional[dict[str, Any]] = None
    desc: Optional[str] = None


class CornerMapOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["corner_map"]
    file: str
    start_s: float
    dur_s: float
    gpx_file: Optional[str] = None
    target_idx: Optional[int] = None
    scene_label: str = "Route Progress"
    scene_label_ru: str = "Маршрут"


class StaticPngOverlay(BaseModel):
    model_config = ConfigDict(extra="allow")

    kind: Literal["static_png"]
    file: str
    start_s: float
    dur_s: float


OverlaySpec = Annotated[
    Union[
        CharacterBadgeOverlay,
        FlashbackBadgeOverlay,
        StravaComparisonOverlay,
        TranslationSubtitleOverlay,
        LiveTelemetryHudOverlay,
        CornerMapOverlay,
        StaticPngOverlay,
    ],
    Field(discriminator="kind"),
]


class TimelineSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_name: str
    bgm_track: Optional[str] = None
    bgm_tracks: list[BgmPhaseSpec] = Field(default_factory=list)
    hud_mode: Literal["auto", "off", "always"] = "auto"
    edition_visual_mode: Literal["universal_4k_remux", "localized_4k_render"] = "universal_4k_remux"
    voiceover_persona: Optional[str] = None
    bookends: BookendsSpec = Field(default_factory=BookendsSpec)
    vo_cues: list[VoCueSpec] = Field(default_factory=list)
    live_subtitles: list[LiveSubtitleSpec] = Field(default_factory=list)
    boosted_dialogs: list[BoostedDialogSpec] = Field(default_factory=list)
    sfx_cues: list[SfxCueSpec] = Field(default_factory=list)
    cuts: list[CutSpec] = Field(default_factory=list)
    overlays: list[OverlaySpec] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _normalize_bgm_and_overlays(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        bgm_single = out.get("bgm_track")
        bgm_list = out.get("bgm_tracks")
        if bgm_single and not bgm_list:
            out["bgm_tracks"] = [{"file": bgm_single, "start_s": 0.0}]
        elif bgm_list and not bgm_single:
            first = bgm_list[0]
            out["bgm_track"] = first["file"] if isinstance(first, dict) else getattr(first, "file", None)

        if "overlays" in out and isinstance(out["overlays"], list):
            norm_ovs = []
            for ov in out["overlays"]:
                if isinstance(ov, dict) and "kind" not in ov:
                    ov = dict(ov, kind="character_badge")
                norm_ovs.append(ov)
            out["overlays"] = norm_ovs
        return out

    @field_validator("bgm_track")
    @classmethod
    def _val_bgm_rel(cls, v: Optional[str]) -> Optional[str]:
        return _check_rel_path(v)

    @field_validator("voiceover_persona")
    @classmethod
    def _val_voice_persona(cls, v: Optional[str]) -> Optional[str]:
        return _check_no_voice_secret(v)

    @model_validator(mode="after")
    def _check_contiguous_cuts_and_secrets(self) -> "TimelineSpec":
        for expected_num, cut in enumerate(self.cuts, start=1):
            if cut.cut_num != expected_num:
                raise ValueError(
                    f"Contiguous cut_num invariant violated: expected cut_num={expected_num}, got {cut.cut_num}"
                )
        return self

    @staticmethod
    def _parse_iso_utc_ts(val: Optional[str]) -> Optional[float]:
        if not val:
            return None
        s = val.strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        elif re.search(r"[+-]\d{4}$", s):
            s = s[:-2] + ":" + s[-2:]
        try:
            return dt.datetime.fromisoformat(s).astimezone(dt.timezone.utc).timestamp()
        except ValueError:
            return None

    def verify_against_manifest(self, manifest: ProjectManifest) -> None:
        """Cross-checks calibration exclusion and GPX/timestamp monotonicity against ProjectManifest."""
        items_by_name = {m.filename.lower(): m for m in manifest.media_inventory}
        inv_order = {m.filename.lower(): idx for idx, m in enumerate(manifest.media_inventory)}

        last_gpx_km = -1.0
        last_gpx_src = ""
        last_video_ts: Optional[float] = None
        last_ride_idx = -1
        last_ride_src = ""

        for cut in self.cuts:
            src_lower = cut.source.lower()
            item = items_by_name.get(src_lower)
            if item and (item.calibration_clock_only or item.exclude_from_timeline):
                raise CalibrationMediaInTimelineError(
                    f"Cut {cut.cut_num} references '{cut.source}', which is marked "
                    "calibration_clock_only/exclude_from_timeline in project_manifest.json."
                )

            exempt = bool(
                cut.allow_out_of_order
                or "flashback" in cut.desc.lower()
                or src_lower.startswith(("ai_", "bookend_"))
            )
            ed = item.editorial if item else None
            if item and not exempt and ed and ed.in_gpx_ride_window and ed.distance_km is not None:
                curr_km = float(ed.distance_km)
                if last_gpx_km >= 0.0 and curr_km < last_gpx_km - 0.15:
                    raise RouteContinuityError(
                        f"Cut {cut.cut_num} ({cut.source} @ {curr_km:.2f} km) regresses before "
                        f"'{last_gpx_src}' ({last_gpx_km:.2f} km) without allow_out_of_order=True."
                    )
                if curr_km > last_gpx_km:
                    last_gpx_km = curr_km
                    last_gpx_src = cut.source

            if item and item.media_type == "video" and not exempt:
                curr_ts = self._parse_iso_utc_ts(item.creation_time_utc)
                if curr_ts is not None:
                    if last_video_ts is not None and curr_ts < last_video_ts - 1.0:
                        raise RouteContinuityError(
                            f"Cut {cut.cut_num} ({cut.source}) is chronologically earlier than '{last_ride_src}'."
                        )
                    if last_video_ts is None or curr_ts >= last_video_ts:
                        last_video_ts = curr_ts
                        last_ride_src = cut.source
                else:
                    curr_idx = inv_order.get(src_lower, -1)
                    if curr_idx >= 0 and curr_idx < last_ride_idx:
                        raise RouteContinuityError(
                            f"Cut {cut.cut_num} ({cut.source}) is chronologically earlier than '{last_ride_src}'."
                        )
                    if curr_idx >= 0:
                        last_ride_idx = curr_idx
                        last_ride_src = cut.source

    @classmethod
    def validate_with_manifest(cls, raw_data: dict[str, Any], manifest: ProjectManifest) -> "TimelineSpec":
        spec = cls.model_validate(raw_data)
        spec.verify_against_manifest(manifest)
        return spec

    @classmethod
    def from_file(cls, path: Path, manifest: Optional[ProjectManifest] = None) -> "TimelineSpec":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        spec = cls.model_validate(raw)
        if manifest is not None:
            spec.verify_against_manifest(manifest)
        return spec
