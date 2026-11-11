"""YouTube API v3 boundary (`ua -> uk`), SHA-256 .srt caching, `unlisted` default, and Flickr cross-link tests (Commits 1 & 9)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from conftest import load_script_module


def test_ua_to_uk_wire_mapping_and_srt_sha256_skip(tmp_path: Path):
    yt = load_script_module("legacy_upload_yt", ".agents/skills/publish-youtube/scripts/upload_youtube_api.py")

    srt_en = tmp_path / "captions.en.srt"
    srt_ua = tmp_path / "captions.ua.srt"
    srt_en.write_text("1\n00:00:01,000 --> 00:00:03,000\nHello Mallorca\n\n", encoding="utf-8")
    srt_ua.write_text("1\n00:00:01,000 --> 00:00:03,000\nПривіт Майорка\n\n", encoding="utf-8")

    en_hash = hashlib.sha256(srt_en.read_bytes()).hexdigest()
    meta_path = tmp_path / "youtube_metadata.json"
    meta = {
        "playlists": [],
        "srt_files": {"en": "captions.en.srt", "ua": "captions.ua.srt"},
        "caption_hashes": {"VID123:en": en_hash},
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")

    mock_yt = MagicMock()
    mock_yt.captions().list().execute.return_value = {
        "items": [
            {"id": "cap_en_1", "snippet": {"language": "en", "trackKind": "standard"}},
        ]
    }
    inserted_bodies = []

    def fake_insert(**kwargs):
        inserted_bodies.append(kwargs["body"])
        m = MagicMock()
        m.execute.return_value = {"id": "cap_uk_new"}
        return m

    mock_yt.captions().insert.side_effect = fake_insert

    yt.assign_playlists_and_captions(mock_yt, "VID123", meta, meta_path=meta_path)

    # EN was skipped because SHA-256 matched; UA was uploaded mapped strictly to wire code 'uk'!
    assert len(inserted_bodies) == 1
    assert inserted_bodies[0]["snippet"]["language"] == "uk"
    assert (tmp_path / "captions.ua.srt").exists(), "Local file must remain captions.ua.srt!"


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 9")
def test_youtube_default_privacy_unlisted_and_storyboard_headline_and_flickr_cat_dir(
    femenia_dir: Path, tmp_path: Path
):
    from agvs_core.flickr_pub import extract_project_metadata
    from agvs_core.youtube_pub import (
        DEFAULT_YOUTUBE_PRIVACY_STATUS,
        resolve_thumbnail_headline,
        should_skip_video_insert_on_resume,
    )

    # 1. Default privacy status is strictly "unlisted" (never "private", which causes HTTP 403 on comments!)
    assert DEFAULT_YOUTUBE_PRIVACY_STATUS == "unlisted"

    # 2. Omitting CLI --thumb-text honors Storyboard.md Section 5 headline_text instead of hardcoded "SAVED AT THE GATE"
    headline = resolve_thumbnail_headline(
        cli_thumb_text=None,
        storyboard_thumb_cfg={"headline_text": "ZERO-T CLIMBING TAX"},
    )
    assert headline == "ZERO-T CLIMBING TAX"

    # 3. Idempotent resume check prevents duplicate 1,600-unit videos.insert when published_video_id exists
    assert should_skip_video_insert_on_resume({"published_video_id": "abc123xyz"}, force_reupload=False) is True
    assert should_skip_video_insert_on_resume({}, force_reupload=False) is False

    # 4. Flickr metadata extractor sets cat_dir so cross_link_flickr_on_youtube() actually runs!
    fmeta = extract_project_metadata(femenia_dir, tmp_path / "2026-11-05_Femenia_Climbing_RU.mp4")
    assert fmeta.get("cat_dir") == str(femenia_dir)
