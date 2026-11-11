"""V1 visual continuity, post-bookend zero-gap repair, and 4K edition remux tests (Commits 1 & 8)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import load_script_module

TICKS_PER_SEC = 254016000000


def test_femenia_fcproj_v1_zero_gap_continuity(femenia_dir: Path):
    fcproj_path = femenia_dir / "2026-11-05_Femenia_Climbing.fcproj"
    data = json.loads(fcproj_path.read_text(encoding="utf-8"))
    items = data["project"]["items"]
    seq_id = str(data["view"]["active_sequence"])
    seq = items[seq_id]["kind"]["Sequence"]
    v1_items = sorted(seq["video_tracks"][0]["items"], key=lambda x: x["start"])
    assert len(v1_items) == 27
    assert v1_items[0]["start"] == 0
    for i in range(len(v1_items) - 1):
        curr_end = v1_items[i]["start"] + v1_items[i]["duration"]
        nxt_start = v1_items[i + 1]["start"]
        assert curr_end == nxt_start, f"Gap/overlap at cut {i+1}: {curr_end} != {nxt_start}"


def test_simulated_rounding_drift_repaired():
    ae = load_script_module("legacy_assemble_engine", ".agents/skills/build-timeline/scripts/assemble_engine.py")
    seq = {
        "video_tracks": [
            {
                "items": [
                    {"id": 1, "name": "c1.mp4", "start": 5, "duration": TICKS_PER_SEC * 3},
                    {"id": 2, "name": "c2.mp4", "start": TICKS_PER_SEC * 3 + 3, "duration": TICKS_PER_SEC * 4},
                    {"id": 3, "name": "c3.mp4", "start": TICKS_PER_SEC * 7 - 2, "duration": TICKS_PER_SEC * 2},
                ]
            }
        ]
    }
    ae.verify_and_repair_v1_continuity(seq)
    v1 = seq["video_tracks"][0]["items"]
    assert v1[0]["start"] == 0
    for i in range(len(v1) - 1):
        assert v1[i]["start"] + v1[i]["duration"] == v1[i + 1]["start"]


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 8")
def test_post_bookend_continuity_and_disabled_burn_captions_and_4k_editions(tmp_path: Path):
    from agvs_core.timeline_builder import (
        attach_bookend_cuts_if_needed,
        build_edition_export_plan,
        build_fcproj_document,
        verify_and_repair_v1_continuity,
    )

    # 1. Bookends enabled -> prepends intro & appends outro, then V1 has 0 tick gaps and C1..C3 enabled == False
    raw_dir = tmp_path / "raw"
    overlays_dir = tmp_path / "overlays"
    proj_dir = tmp_path / "proj"
    raw_dir.mkdir()
    overlays_dir.mkdir()
    proj_dir.mkdir()

    for name in ("bookend_intro_4K.mp4", "bookend_outro_4K.mp4", "clip1.mp4", "bgm.mp3"):
        target = (overlays_dir if name.startswith("bookend_") else raw_dir) / name
        target.write_bytes(b"\x00" * 1024)

    cuts = [{"cut_num": 1, "source": "clip1.mp4", "dur": 4.0, "src_in": 0.0}]
    full_cuts = attach_bookend_cuts_if_needed(
        cuts,
        bookends_cfg={"enabled": True, "intro_dur_s": 3.5, "outro_dur_s": 4.5},
        overlays_dir=overlays_dir,
        raw_dir=raw_dir,
    )
    assert len(full_cuts) == 3
    assert full_cuts[0]["source"] == "bookend_intro_4K.mp4"
    assert full_cuts[-1]["source"] == "bookend_outro_4K.mp4"

    fcproj = build_fcproj_document(
        proj_dir=proj_dir,
        raw_dir=raw_dir,
        overlays_dir=overlays_dir,
        bgm_track=raw_dir / "bgm.mp3",
        cuts_spec=full_cuts,
        expanded_overlays=[],
        boosted_dialogs=[],
        sfx_cues=[],
        vo_cues=[],
        riding_gain_db=-10.0,
        edition="en",
        dimension_lookup=lambda _p, _s: (3840, 2160),
        duration_lookup=lambda _p: 30.0,
    )
    seq_id = str(fcproj["view"]["active_sequence"])
    seq = fcproj["project"]["items"][seq_id]["kind"]["Sequence"]
    verify_and_repair_v1_continuity(seq)
    v1 = seq["video_tracks"][0]["items"]
    assert len(v1) == 3
    for idx in range(len(v1) - 1):
        assert v1[idx]["start"] + v1[idx]["duration"] == v1[idx + 1]["start"]

    for cap_track in seq["caption_tracks"]:
        assert cap_track["enabled"] is False, "Caption track must default to enabled=False (no double burn-in)"

    # 2. Mandatory Refinement #2: Edition export plan — zero -f concat splicing; 4K UHD for both modes!
    plan_universal = build_edition_export_plan(
        proj_dir=proj_dir,
        exports_dir=tmp_path / "exports",
        edition_visual_mode="universal_4k_remux",
        available_audio_langs=("en", "ua", "ru"),
    )
    assert plan_universal["filmcraft_renders"] == [
        {"edition": "en", "resolution": (3840, 2160), "preset": "Match Source – Adaptive High Bitrate"}
    ]
    for remux in plan_universal["ffmpeg_remuxes"]:
        assert "-f" not in remux["cmd"] or "concat" not in remux["cmd"]
        assert "-c:v" in remux["cmd"] and "copy" in remux["cmd"]
    assert {r["edition"] for r in plan_universal["ffmpeg_remuxes"]} == {"en", "ua", "ru"}

    plan_localized = build_edition_export_plan(
        proj_dir=proj_dir,
        exports_dir=tmp_path / "exports",
        edition_visual_mode="localized_4k_render",
        available_audio_langs=("en", "ua", "ru"),
    )
    assert len(plan_localized["filmcraft_renders"]) == 2
    for r in plan_localized["filmcraft_renders"]:
        assert r["resolution"] == (3840, 2160), "Localized RU render must be 4K UHD (3840x2160), never 1080p!"
        assert "1080p" not in r["preset"]
