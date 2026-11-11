"""40m GPX grade smoothing, ride-date primary GPX selector, HUD toggle, and Mallorca toponym tests (Commits 1 & 5)."""

from __future__ import annotations

import datetime as dt
import math
from pathlib import Path

import pytest

from conftest import load_script_module


def _write_synthetic_climb_gpx(path: Path, date_iso: str = "2026-11-05", n_points: int = 40) -> Path:
    """Writes a 1Hz GPX climbing at steady ~7.5% (3.2 m/s horizontal, quantized 1m integer barometric steps)."""
    start_ts = dt.datetime.fromisoformat(f"{date_iso}T09:00:00+00:00")
    lat0, lon0 = 39.880000, 3.010000
    # 1 deg lat ~ 111,320 m -> 3.2 m/s northward = 3.2 / 111320 deg/s
    dlat_per_sec = 3.2 / 111320.0
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gpx version="1.1" creator="TestGarmin"><trk><trkseg>',
    ]
    for i in range(n_points):
        lat = lat0 + i * dlat_per_sec
        # True elevation rises 0.24 m/s (7.5% of 3.2 m/s), quantized to 1.0m barometric steps!
        quantized_ele = math.floor(100.0 + i * 0.24)
        ts = (start_ts + dt.timedelta(seconds=i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        lines.append(
            f'<trkpt lat="{lat:.7f}" lon="{lon0:.7f}"><ele>{quantized_ele:.1f}</ele><time>{ts}</time></trkpt>'
        )
    lines.append("</trkseg></trk></gpx>")
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def test_hud_mode_off_with_single_cut_override():
    gw = load_script_module("legacy_gw_hud", ".agents/skills/build-timeline/scripts/gpx_widgets.py")
    assert gw.should_show_telemetry_hud("VIDEO_1762770000000.MP4", rolling_speed_mph=18.0, mode="off") is False
    assert gw.should_show_telemetry_hud("VIDEO_1762770000000.MP4", rolling_speed_mph=18.0, mode="auto") is True
    assert gw.should_show_telemetry_hud("VIDEO_1762770000000.MP4", rolling_speed_mph=1.2, mode="auto") is False


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 5")
def test_40m_grade_smoothing_eliminates_1m_barometric_spikes(tmp_path: Path):
    from agvs_core.telemetry_gpx import load_gpx_track

    gpx_file = _write_synthetic_climb_gpx(tmp_path / "climb.gpx", n_points=50)
    pts = load_gpx_track(gpx_file, min_grade_window_m=40.0)
    assert len(pts) == 50
    # After 40m of travel (idx >= 15), smoothed gradient must stay realistic (6.0%..9.0%), never spiking >12%!
    steady_grades = [p["grad_pct"] for p in pts[15:]]
    assert max(steady_grades) <= 9.5
    assert min(steady_grades) >= 5.5


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 5")
def test_ride_date_primary_gpx_selector(tmp_path: Path):
    from agvs_core.telemetry_gpx import select_primary_ride_gpx

    raw_dir = tmp_path / "2026-11-05_Femenia_Climbing"
    raw_dir.mkdir()
    # Alphabetically first AND more points, but from 2017 flashback!
    _write_synthetic_climb_gpx(raw_dir / "2017_Mallorca312_167km_route.gpx", date_iso="2017-04-29", n_points=80)
    ride_gpx = _write_synthetic_climb_gpx(raw_dir / "garmin_femenia_ride.gpx", date_iso="2026-11-05", n_points=40)

    primary, archival = select_primary_ride_gpx(raw_dir, project_name="2026-11-05_Femenia_Climbing")
    assert primary == ride_gpx
    assert [p.name for p in archival] == ["2017_Mallorca312_167km_route.gpx"]


@pytest.mark.xfail(strict=True, reason="Fixed in Commit 5")
def test_mallorca_phonetic_toponym_linter():
    from agvs_core.telemetry_gpx import normalize_mallorca_toponyms, validate_mallorca_toponyms

    valid_ru = "Подъем из Пойенса к монастырю Йук и спуск в Сойер через Валдемоса на острове Майорка."
    valid_ua = "Підйом із Поєнса до монастиря Йук та спуск у Соєр на острові Майорка."
    assert validate_mallorca_toponyms(valid_ru) == []
    assert validate_mallorca_toponyms(valid_ua) == []

    bad_ru = "Поездка на Мальорка через Польенса, Сольер и монастырь Льюк."
    violations = validate_mallorca_toponyms(bad_ru)
    assert len(violations) >= 4
    fixed = normalize_mallorca_toponyms(bad_ru, lang="ru")
    assert validate_mallorca_toponyms(fixed) == []
    assert "Майорка" in fixed and "Пойенса" in fixed and "Сойер" in fixed and "Йук" in fixed
