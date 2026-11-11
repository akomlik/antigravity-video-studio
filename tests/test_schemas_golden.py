"""Golden schema, pre-flight, and security contract tests (Commits 1, 2, 3)."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

from conftest import load_script_module


def test_zero_project_scripts_guard(femenia_dir: Path, paradise_dir: Path, tmp_path: Path):
    bt = load_script_module("legacy_build_timeline", ".agents/skills/build-timeline/scripts/build_timeline.py")
    bt.check_zero_project_scripts_preflight(femenia_dir)
    bt.check_zero_project_scripts_preflight(paradise_dir)

    rogue_proj = tmp_path / "2026-11-12_Rogue_Project"
    rogue_proj.mkdir()
    (rogue_proj / "assemble_rogue.py").write_text("print('illegal')\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="Zero-Script Project Law"):
        bt.check_zero_project_scripts_preflight(rogue_proj)


def test_calibration_media_rejected_in_cuts(paradise_dir: Path):
    bt = load_script_module("legacy_build_timeline_cal", ".agents/skills/build-timeline/scripts/build_timeline.py")
    spec = json.loads((paradise_dir / "timeline_spec.json").read_text(encoding="utf-8"))
    bad_cuts = copy.deepcopy(spec["cuts"])
    bad_cuts.append({
        "cut_num": len(bad_cuts) + 1,
        "source": "IMG_1794306860718.JPG",
        "is_still": True,
        "dur": 3.0,
        "desc": "Accidental calibration clock frame",
    })
    with pytest.raises(ValueError, match="calibration_clock_only"):
        bt.check_landmark_synchronization_preflight(paradise_dir, bad_cuts, [])


def test_non_monotonic_gpx_milepost_rejected(tmp_path: Path):
    bt = load_script_module("legacy_build_timeline_mono", ".agents/skills/build-timeline/scripts/build_timeline.py")
    proj = tmp_path / "2026-11-05_Synthetic_Ride"
    proj.mkdir()
    manifest = {
        "project_name": proj.name,
        "media_inventory": [
            {
                "filename": "clip_early.mp4",
                "media_type": "video",
                "creation_time_utc": "2026-11-05T09:10:00Z",
                "editorial": {"in_gpx_ride_window": True, "distance_km": 5.0, "distance_mi": 3.11},
            },
            {
                "filename": "clip_summit.mp4",
                "media_type": "video",
                "creation_time_utc": "2026-11-05T10:20:00Z",
                "editorial": {"in_gpx_ride_window": True, "distance_km": 22.4, "distance_mi": 13.92},
            },
        ],
    }
    (proj / "project_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    bad_cuts = [
        {"cut_num": 1, "source": "clip_summit.mp4", "dur": 4.0, "desc": "Summit"},
        {"cut_num": 2, "source": "clip_early.mp4", "dur": 4.0, "desc": "Base climb"},
    ]
    with pytest.raises(ValueError, match="GPX Route Sequence Violation"):
        bt.check_landmark_synchronization_preflight(proj, bad_cuts, [])

    # Flashback exemption must pass cleanly
    exempt_cuts = [
        {"cut_num": 1, "source": "clip_summit.mp4", "dur": 4.0, "desc": "Summit"},
        {"cut_num": 2, "source": "clip_early.mp4", "dur": 4.0, "desc": "Flashback to base", "allow_out_of_order": True},
    ]
    bt.check_landmark_synchronization_preflight(proj, exempt_cuts, [])


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 2")
def test_storyboard_has_no_raw_voice_id_or_abs_path(femenia_dir: Path):
    from agvs_core import config as agvs_config

    sb_text = (femenia_dir / "Storyboard.md").read_text(encoding="utf-8")
    assert not re.search(r"\bvoice_[A-Za-z0-9]{6,}\b", sb_text), "Raw GEMINI_VOICE_ID leaked in Storyboard.md!"
    assert "/" + "Users/" not in sb_text, "Frozen machine-specific user path in Storyboard.md!"

    ffmpeg_bin = agvs_config.find_binary("ffmpeg")
    assert Path(ffmpeg_bin).is_file()
    with pytest.raises(ValueError, match="Absolute machine path forbidden"):
        agvs_config.ensure_relative_studio_path("/" + "Users/example/Movies/clip.mp4")


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 3")
def test_golden_pydantic_schemas_validate_femenia_and_paradise(femenia_dir: Path, paradise_dir: Path):
    from agvs_core.schemas import (
        CalibrationMediaInTimelineError,
        ProjectManifest,
        SecuritySchemaError,
        StoryboardTuningSpec,
        TimelineSpec,
    )

    fem_manifest = ProjectManifest.from_file(femenia_dir / "project_manifest.json")
    fem_spec = TimelineSpec.from_file(femenia_dir / "timeline_spec.json", manifest=fem_manifest)
    assert len(fem_spec.cuts) == 27
    assert len(fem_spec.bgm_tracks) >= 1

    par_manifest = ProjectManifest.from_file(paradise_dir / "project_manifest.json")
    par_spec = TimelineSpec.from_file(paradise_dir / "timeline_spec.json", manifest=par_manifest)
    assert len(par_spec.cuts) == 61
    assert par_spec.hud_mode == "off"
    assert any(c.hud is True for c in par_spec.cuts)

    fem_sb = StoryboardTuningSpec.from_storyboard_file(femenia_dir / "Storyboard.md")
    par_sb = StoryboardTuningSpec.from_storyboard_file(paradise_dir / "Storyboard.md")
    assert fem_sb.primary_language == "en"
    assert par_sb.primary_language == "en"

    # Injecting calibration photo raises CalibrationMediaInTimelineError
    bad_raw = json.loads((paradise_dir / "timeline_spec.json").read_text(encoding="utf-8"))
    bad_raw["cuts"].append({
        "cut_num": len(bad_raw["cuts"]) + 1,
        "source": "IMG_1794306860718.JPG",
        "is_still": True,
        "dur": 2.5,
    })
    with pytest.raises(CalibrationMediaInTimelineError):
        TimelineSpec.validate_with_manifest(bad_raw, par_manifest)

    # Injecting raw biometric voice_id or absolute path raises SecuritySchemaError
    sec_raw = json.loads((femenia_dir / "timeline_spec.json").read_text(encoding="utf-8"))
    sec_raw["voiceover_persona"] = "voice_" + "abc987654321"
    with pytest.raises(SecuritySchemaError):
        TimelineSpec.model_validate(sec_raw)

    bad_manifest_raw = json.loads((femenia_dir / "project_manifest.json").read_text(encoding="utf-8"))
    bad_manifest_raw["raw_media_folder"] = "/" + "Users/someone/Movies/2026/test"
    with pytest.raises(SecuritySchemaError):
        ProjectManifest.model_validate(bad_manifest_raw)
