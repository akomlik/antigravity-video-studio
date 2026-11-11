"""BleeqUP Ranger AI timestamp sync, Epoch 1.8B rollover, <250ms photo batch, and RTC brownout tests (Commits 1 & 4)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from ranger_sync.anomaly import PhysicalOverlapError, assert_physical_continuity
from ranger_sync.models import MediaItem, MediaKind
from ranger_sync.parser import classify_filename


def _make_item(
    filename: str,
    kind: MediaKind,
    epoch_ms: int,
    dur_s: float = 15.0,
    shift_s: float = 0.0,
    internal_create_utc: datetime | None = None,
) -> MediaItem:
    raw_utc = datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc)
    corr_utc = raw_utc + timedelta(seconds=shift_s)
    kwargs = dict(
        path=Path(filename),
        filename=filename,
        kind=kind,
        raw_epoch_ms=epoch_ms,
        raw_utc=raw_utc,
        corrected_utc=corr_utc,
        time_shift_sec=shift_s,
        duration_sec=dur_s,
    )
    if internal_create_utc is not None:
        kwargs["internal_create_utc"] = internal_create_utc
    return MediaItem(**kwargs)


def test_ranger_sync_epoch_1_8b_photo_classification():
    # 1,800,000,000,123 ms = 2027-01-15T08:00:00.123Z
    res = classify_filename("IMG_1800000000123.JPG")
    assert res == (MediaKind.BLEEQUP_PHOTO, 1800000000123)


def test_oct29_and_oct31_sleep_oscillator_shifts_still_solve():
    base_ms = 1761730000000
    # Oct 29 uniform +2482s shift & Oct 31 mid-ride +3837s shift without physical overlap
    items = [
        _make_item("VIDEO_1761730000000.MP4", MediaKind.BLEEQUP_VIDEO, base_ms, dur_s=18.0, shift_s=2482.0),
        _make_item("VIDEO_1761730120000.MP4", MediaKind.BLEEQUP_VIDEO, base_ms + 120_000, dur_s=20.0, shift_s=2482.0),
        _make_item("VIDEO_1761730600000.MP4", MediaKind.BLEEQUP_VIDEO, base_ms + 600_000, dur_s=16.0, shift_s=3837.0),
    ]
    assert_physical_continuity(items, use_raw=False)


def test_subsecond_photo_batch_collision_raises_physical_overlap():
    base_ms = 1762770000000
    items = [
        _make_item("IMG_1762770000000.JPG", MediaKind.BLEEQUP_PHOTO, base_ms, dur_s=0.0),
        _make_item("IMG_1762770000091.JPG", MediaKind.BLEEQUP_PHOTO, base_ms + 91, dur_s=0.0),
    ]
    with pytest.raises(PhysicalOverlapError):
        assert_physical_continuity(items, use_raw=True)


def test_backward_rtc_brownout_into_silent_cafe_pause_detected():
    # Ride starts 09:00..09:30, 60-min silent cafe stop 09:30..10:30, ride resumes 10:30..11:00.
    # Clip 3 was recorded at 10:45 (QuickTime internal atom = 10:45), but a -55m RTC brownout stamped
    # its filename epoch at 09:50 right inside the silent cafe pause (zero overlap with 09:00..09:30 clips!).
    t0 = datetime(2026, 11, 10, 9, 0, 0, tzinfo=timezone.utc)
    ms = lambda mins: int((t0 + timedelta(minutes=mins)).timestamp() * 1000)

    c1 = _make_item(
        f"VIDEO_{ms(0)}.MP4", MediaKind.BLEEQUP_VIDEO, ms(0), dur_s=20.0,
        internal_create_utc=t0 + timedelta(minutes=0),
    )
    c2 = _make_item(
        f"VIDEO_{ms(25)}.MP4", MediaKind.BLEEQUP_VIDEO, ms(25), dur_s=20.0,
        internal_create_utc=t0 + timedelta(minutes=25),
    )
    # Brownout clip: internal_create_utc is 10:45 (+105m), but filename epoch jumped back -55m to 09:50 (+50m)!
    c3_brownout = _make_item(
        f"VIDEO_{ms(50)}.MP4", MediaKind.BLEEQUP_VIDEO, ms(50), dur_s=20.0,
        internal_create_utc=t0 + timedelta(minutes=105),
    )
    with pytest.raises(PhysicalOverlapError, match="brownout|monotonic|atom"):
        assert_physical_continuity([c1, c2, c3_brownout], use_raw=True)


def test_ingest_epoch_1_8b_and_non_destructive_storyboard_sync(tmp_path: Path):
    from agvs_core.ingest_sync import has_bleequp_files, parse_media_utc, sync_storyboard_non_destructive

    raw_dir = tmp_path / "raw_2027"
    raw_dir.mkdir()
    (raw_dir / "IMG_1800000000123.JPG").write_bytes(b"\xff\xd8\xff\xd9")
    assert has_bleequp_files(raw_dir) is True

    dt_parsed = parse_media_utc("2026-11-10T12:09:53+00:00")
    assert dt_parsed is not None and dt_parsed.year == 2026

    # Non-destructive Storyboard sync: existing rich catalog Storyboard.md must NEVER be overwritten by stale raw draft
    cat_dir = tmp_path / "catalog"
    cat_dir.mkdir()
    rich_sb = cat_dir / "Storyboard.md"
    stale_sb = raw_dir / "Storyboard.md"
    stale_sb.write_text("# Draft stub\n", encoding="utf-8")
    rich_sb.write_text("# Final Co-Created Storyboard\n\nDetailed 61-cut production spec.\n", encoding="utf-8")

    sync_storyboard_non_destructive(raw_dir, cat_dir)
    assert "Detailed 61-cut production spec." in rich_sb.read_text(encoding="utf-8")
