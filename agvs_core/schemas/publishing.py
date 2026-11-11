"""Pydantic v2 schemas for YouTube & Flickr release metadata (`agvs_core/schemas/publishing.py`)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class YoutubeChapterSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    start_sec: float
    timecode: str
    title: str


class ThumbnailSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    mode: Literal["composite_ai", "preserve", "frame"] = "composite_ai"
    headline_text: str = "THE 140 BPM RULE"
    headline_text_ua: Optional[str] = None
    headline_text_ru: Optional[str] = None
    hero_image: Optional[str] = None
    prop_image: Optional[str] = None


class YoutubeMetadataSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_name: str
    recording_date: Optional[str] = None
    video_file: str
    thumbnail_file: Optional[str] = None
    thumbnail_timestamp_sec: float = 15.0
    title: str
    title_ua: Optional[str] = None
    title_ru: Optional[str] = None
    title_alternatives: list[str] = Field(default_factory=list)
    playlists: list[str] = Field(default_factory=list)
    description: str
    localizations: dict[str, dict[str, str]] = Field(default_factory=dict)
    srt_files: dict[str, str] = Field(default_factory=dict)
    narration_scripts: dict[str, dict[str, str]] = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)
    category_id: str = "17"
    privacy_status: Literal["unlisted", "public", "private"] = "unlisted"
    made_for_kids: bool = False
    chapters: list[YoutubeChapterSpec] = Field(default_factory=list)
    music_credits: list[str] = Field(default_factory=list)
    related_youtube_links: list[str] = Field(default_factory=list)
    published_youtube_url: Optional[str] = None
    published_video_id: Optional[str] = None
    edition_urls: dict[str, str] = Field(default_factory=dict)
    caption_hashes: dict[str, str] = Field(default_factory=dict)

    @classmethod
    def from_file(cls, path: Path) -> "YoutubeMetadataSpec":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))


class FlickrReleaseSpec(BaseModel):
    model_config = ConfigDict(extra="allow")

    project_name: str
    cat_dir: str
    video_file: str
    title: str
    description: str
    tags: list[str] = Field(default_factory=list)
    album_title: Optional[str] = None
    lat: Optional[float] = None
    lon: Optional[float] = None
    is_public: bool = False
    is_friend: bool = True
    is_family: bool = True
    extra: dict[str, Any] = Field(default_factory=dict)
