"""
Phase 2/3 Golden Regression Tests — `agvs_core.services`, Thin CLI Shims & Human Approval Gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agvs_core.config import get_studio_root
from agvs_core.services import (
    HumanApprovalRequiredError,
    ProgressEvent,
    inspect_project,
    list_projects,
    preview_bgm_command,
    publish_flickr,
    publish_youtube,
    validate_spec,
)

GOLDEN_PROJECTS = [
    "2026-11-05_Femenia_Climbing",
    "2026-11-10_Another_Day_In_Paradise",
]


def test_project_service_discovers_and_validates_golden_projects() -> None:
    projects = list_projects(year="2026")
    ids = {p["project_id"] for p in projects}
    for proj_id in GOLDEN_PROJECTS:
        assert proj_id in ids
        summary = inspect_project(proj_id)
        assert summary["project_id"] == proj_id
        assert summary["catalog_relpath"] == f"04_Project_Catalog/2026/{proj_id}"
        assert summary["manifest"] is not None
        assert summary["timeline_spec"] is not None
        manifest, spec = validate_spec(proj_id)
        assert manifest is not None
        assert len(spec.cuts) in (27, 61)


def test_publish_service_enforces_mandatory_human_approval_gate() -> None:
    for bad_token in (None, "", "   "):
        with pytest.raises(HumanApprovalRequiredError):
            publish_youtube("2026-11-05_Femenia_Climbing", human_approved_token=bad_token)
        with pytest.raises(HumanApprovalRequiredError):
            publish_flickr("2026-11-05_Femenia_Climbing", human_approved_token=bad_token)


def test_preview_bgm_command_and_progress_event_contract() -> None:
    cmd = preview_bgm_command("04_Warm_Social_And_Retro/085bpm_WarmChillhop_Snails_Creatormix.mp3", seconds=10)
    assert cmd[1:3] == ["-t", "10"]
    assert cmd[3].endswith("03_Audio_Library/01_Curated_BGM/04_Warm_Social_And_Retro/085bpm_WarmChillhop_Snails_Creatormix.mp3")

    ev = ProgressEvent(stage="build", step="validate", pct=10.0, message="Validating spec")
    assert ev.stage == "build"
    assert ev.pct == 10.0


def test_all_skill_scripts_are_thin_shims_and_legacy_v1_removed() -> None:
    root = get_studio_root()
    skills_dir = root / ".agents" / "skills"
    assert not (skills_dir / "publish-youtube/scripts/upload_youtube_studio_chrome.py").exists()
    assert not (skills_dir / "publish-youtube/scripts/extract_facebook_stills.py").exists()

    scripts = sorted(skills_dir.glob("*/scripts/*.py"))
    assert len(scripts) == 20
    for script in scripts:
        txt = script.read_text(encoding="utf-8")
        lines = txt.splitlines()
        assert len(lines) <= 40, f"{script} exceeds 40-line thin shim limit ({len(lines)} lines)"
        assert "/Users/" not in txt, f"Hardcoded /Users/ path in {script}"
        assert "/Volumes/" not in txt, f"Hardcoded /Volumes/ path in {script}"
        assert "/opt/homebrew" not in txt, f"Hardcoded /opt/homebrew path in {script}"
        assert "agvs_core." in txt, f"Shim {script} does not delegate to agvs_core"
