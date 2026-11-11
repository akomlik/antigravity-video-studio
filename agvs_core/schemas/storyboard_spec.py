"""Canonical `Storyboard.md` Section 5 YAML parser & serializer (`agvs_core/schemas/storyboard_spec.py`)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .manifest import SecuritySchemaError, _check_no_voice_secret, _check_rel_path


class StoryboardTuningSpec(BaseModel):
    """Canonical representation of Section 5 in `Storyboard.md` across Studio v2.0, v2.1, and v3.0."""

    model_config = ConfigDict(extra="allow")

    version: str = "3.0.0"
    project: Optional[str] = None
    genre: str = "cycling_ride"
    resolution: str = "3840x2160"
    fps: float = 30.0
    hud_mode: Literal["auto", "off", "always"] = "auto"
    primary_language: Literal["en", "ua", "ru", "none"] = "en"
    voiceover_persona: str = "$GEMINI_VOICE_ID"
    reference_voice_sample: Optional[str] = None
    bgm_tracks: list[str] = Field(default_factory=list)
    publishing_mode: Literal["en_only", "option_a", "option_b"] = "option_a"
    default_privacy: Literal["unlisted", "public", "private"] = "unlisted"
    thumbnail_headline: Optional[str] = None
    thumbnail_headline_ua: Optional[str] = None
    thumbnail_headline_ru: Optional[str] = None
    raw_yaml: dict[str, Any] = Field(default_factory=dict)

    @field_validator("voiceover_persona")
    @classmethod
    def _val_persona(cls, v: str) -> str:
        return _check_no_voice_secret(v) or "$GEMINI_VOICE_ID"

    @field_validator("reference_voice_sample")
    @classmethod
    def _val_ref_sample(cls, v: Optional[str]) -> Optional[str]:
        return _check_rel_path(v)

    @field_validator("bgm_tracks")
    @classmethod
    def _val_bgms(cls, tracks: list[str]) -> list[str]:
        return [_check_rel_path(t) or t for t in tracks]

    @classmethod
    def from_yaml_dict(cls, data: dict[str, Any]) -> "StoryboardTuningSpec":
        video_specs = data.get("video_specs") or {}
        gpx_hud = data.get("gpx_hud") or {}
        gpx_tel = data.get("gpx_telemetry") or {}
        hud_ov = gpx_tel.get("hud_overlay") or {}
        audio_mix = data.get("audio_mix") or {}
        yt_pub = data.get("youtube_publishing") or {}
        thumb = data.get("thumbnail") or {}

        raw_lang = (
            audio_mix.get("primary_voiceover_language")
            or yt_pub.get("primary_language")
            or "en"
        )
        lang_norm = str(raw_lang).strip().lower()
        if lang_norm not in ("en", "ua", "ru", "none"):
            lang_norm = "en"

        bgm_list: list[str] = []
        if isinstance(audio_mix.get("bgm_track"), str):
            bgm_list.append(audio_mix["bgm_track"])
        elif isinstance(audio_mix.get("bgm_tracks"), dict):
            bgm_list.extend(str(v) for v in audio_mix["bgm_tracks"].values() if v)
        elif isinstance(audio_mix.get("bgm_tracks"), list):
            bgm_list.extend(str(v) for v in audio_mix["bgm_tracks"] if v)

        hud_val = str(hud_ov.get("mode") or gpx_hud.get("gpx_telemetry_hud") or "auto").strip().lower()
        if hud_val not in ("auto", "off", "always"):
            hud_val = "auto"

        pub_mode = str(yt_pub.get("publishing_mode") or "option_a").strip().lower()
        if pub_mode not in ("en_only", "option_a", "option_b"):
            pub_mode = "option_a"

        priv = str(yt_pub.get("default_privacy") or "unlisted").strip().lower()
        if priv not in ("unlisted", "public", "private"):
            priv = "unlisted"

        return cls(
            version=str(data.get("version") or "3.0.0"),
            project=data.get("project"),
            genre=str(data.get("genre") or "cycling_ride"),
            resolution=str(data.get("resolution") or video_specs.get("resolution") or "3840x2160"),
            fps=float(data.get("fps") or video_specs.get("timeline_fps") or 30.0),
            hud_mode=hud_val,  # type: ignore[arg-type]
            primary_language=lang_norm,  # type: ignore[arg-type]
            voiceover_persona=str(audio_mix.get("voiceover_persona") or "$GEMINI_VOICE_ID"),
            reference_voice_sample=audio_mix.get("reference_voice_sample"),
            bgm_tracks=bgm_list,
            publishing_mode=pub_mode,  # type: ignore[arg-type]
            default_privacy=priv,  # type: ignore[arg-type]
            thumbnail_headline=thumb.get("headline_text"),
            thumbnail_headline_ua=thumb.get("headline_text_ua"),
            thumbnail_headline_ru=thumb.get("headline_text_ru"),
            raw_yaml=data,
        )

    @classmethod
    def from_storyboard_markdown(cls, markdown_text: str) -> "StoryboardTuningSpec":
        # Check entire markdown for leaked voice_* IDs in YAML blocks
        yaml_blocks = re.findall(r"```yaml\s*\n(.*?)```", markdown_text, flags=re.DOTALL)
        if not yaml_blocks:
            return cls()
        raw_block = yaml_blocks[-1]
        if re.search(r"\bvoice_[A-Za-z0-9]{6,}\b", raw_block):
            raise SecuritySchemaError("Raw GEMINI_VOICE_ID found inside Storyboard.md YAML block!")
        parsed = yaml.safe_load(raw_block) or {}
        if not isinstance(parsed, dict):
            return cls()
        return cls.from_yaml_dict(parsed)

    @classmethod
    def from_storyboard_file(cls, path: Path) -> "StoryboardTuningSpec":
        return cls.from_storyboard_markdown(Path(path).read_text(encoding="utf-8"))

    def to_canonical_yaml(self) -> str:
        payload = {
            "version": "3.0.0",
            "project": self.project,
            "genre": self.genre,
            "resolution": self.resolution,
            "fps": self.fps,
            "gpx_telemetry": {"hud_overlay": {"mode": self.hud_mode}},
            "audio_mix": {
                "primary_voiceover_language": self.primary_language,
                "voiceover_persona": "$GEMINI_VOICE_ID",
                "bgm_tracks": self.bgm_tracks,
            },
            "youtube_publishing": {
                "publishing_mode": self.publishing_mode,
                "default_privacy": self.default_privacy,
                "primary_language": self.primary_language.upper(),
            },
            "thumbnail": {
                "headline_text": self.thumbnail_headline,
                "headline_text_ua": self.thumbnail_headline_ua,
                "headline_text_ru": self.thumbnail_headline_ru,
            },
        }
        return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
