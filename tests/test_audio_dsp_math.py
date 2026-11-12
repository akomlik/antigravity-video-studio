"""Broadcast 4-track audio DSP, 180Hz BGM RMS, ear-tested ducking, VO single-pass, and SFX peak tests (Commits 1 & 7)."""

from __future__ import annotations

import math
import struct
import wave
from pathlib import Path

import pytest

from conftest import load_script_module


def _write_synthetic_wav(path: Path, samples_fn, dur_s: float = 1.0, sr: int = 48000) -> Path:
    n_frames = int(round(dur_s * sr))
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        buf = bytearray()
        for i in range(n_frames):
            t = i / sr
            val = max(-0.98, min(0.98, float(samples_fn(t))))
            s = int(round(val * 32767))
            buf.extend(struct.pack("<hh", s, s))
        wf.writeframes(bytes(buf))
    return path


def test_mellow_bgm_detection_and_presence_eq(tmp_path: Path):
    ae = load_script_module("legacy_ae_audio", ".agents/skills/build-timeline/scripts/assemble_engine.py")
    assert ae.is_mellow_bgm_track(Path("90bpm_Chillhop_Snails_CreatorMix.mp3")) is True
    assert ae.is_mellow_bgm_track(Path("88bpm_Warm_Morning_Coffee.mp3")) is True
    assert ae.is_mellow_bgm_track(Path("128bpm_Punchy_Summit_Sprint.mp3")) is False

    mellow_wav = _write_synthetic_wav(
        tmp_path / "90bpm_Chillhop_Test.wav",
        lambda t: 0.20 * math.sin(2.0 * math.pi * 440.0 * t),
    )
    calib = ae.calculate_bgm_gains(mellow_wav)
    assert calib["is_mellow"] is True
    assert "equalizer=f=1800" in calib["eq_filter"]


def test_bgm_180hz_highpass_rms_and_ear_tested_ducking(tmp_path: Path):
    from agvs_core.audio_dsp import build_bgm_ducking_volume_expr, calculate_bgm_gains

    # Synthetic track with heavy 55 Hz sub-bass (0.75 amp) + quiet 1 kHz midrange (0.08 amp)
    sub_heavy = _write_synthetic_wav(
        tmp_path / "88bpm_Chillhop_Snails_SubHeavy.wav",
        lambda t: 0.75 * math.sin(2.0 * math.pi * 55.0 * t) + 0.08 * math.sin(2.0 * math.pi * 1000.0 * t),
    )
    mid_only = _write_synthetic_wav(
        tmp_path / "88bpm_Chillhop_Snails_MidOnly.wav",
        lambda t: 0.08 * math.sin(2.0 * math.pi * 1000.0 * t),
    )

    c_sub = calculate_bgm_gains(sub_heavy)
    c_mid = calculate_bgm_gains(mid_only)

    # 180 Hz high-pass ensures 55 Hz sub-bass does NOT skew midrange loudness measurement (> 8 dB difference otherwise!)
    assert abs(c_sub["midrange_mean_db"] - c_mid["midrange_mean_db"]) < 1.5

    # Mandatory Refinement #3 + EBU R128 LUFS Ceiling: Mellow +1.5 dB offset keeps riding target in [-18.0, -15.5] dB
    # and smooth 11.5 dB broadcast duck guarantees >= 10.5 LU separation under -16 LUFS narration!
    assert c_sub["mellow_boost_db"] == pytest.approx(1.5, abs=0.1)
    assert -18.0 <= c_sub["target_riding_db"] <= -15.5
    assert -29.5 <= c_sub["target_ducked_db"] <= -26.5
    duck_amount = c_sub["target_riding_db"] - c_sub["target_ducked_db"]
    assert 10.5 <= duck_amount <= 13.0

    expr = build_bgm_ducking_volume_expr(
        speech_windows=[(4.0, 9.0), (15.0, 20.0)],
        duck_db=duck_amount,
    )
    assert "between(t," in expr or "min(" in expr


def test_vo_single_pass_studio_dry_and_no_atempo_stretch(tmp_path: Path):
    from agvs_core.audio_dsp import (
        STUDIO_DRY_VO_FILTER,
        VoiceoverDurationOverflowError,
        pace_and_normalize_vo_cue,
    )

    assert STUDIO_DRY_VO_FILTER.count("equalizer=f=380") == 1
    assert "atempo" not in STUDIO_DRY_VO_FILTER

    raw_vo = _write_synthetic_wav(
        tmp_path / "voiceover_en_cue01.wav",
        lambda t: 0.25 * math.sin(2.0 * math.pi * 220.0 * t),
        dur_s=3.2,
    )
    # Overflowing max_dur_s must raise VoiceoverDurationOverflowError instead of applying atempo > 1.0!
    with pytest.raises(VoiceoverDurationOverflowError):
        pace_and_normalize_vo_cue(raw_vo, tmp_path / "out.wav", max_dur_s=2.0, already_studio_dry=True)

    # Already Studio-Dry stem runs trim-only without re-applying the -4.5 dB 380Hz notch a second time
    out_wav, applied_filters = pace_and_normalize_vo_cue(
        raw_vo, tmp_path / "paced.wav", max_dur_s=5.0, already_studio_dry=True
    )
    assert out_wav.exists()
    assert "equalizer=f=380" not in applied_filters
    assert "atempo" not in applied_filters


def test_same_language_vo_dialog_collision_and_sfx_peak_alignment(studio_root: Path):
    from agvs_core.audio_dsp import (
        SameLanguageAudioOverlapError,
        resolve_sfx_start_s,
        verify_no_same_language_vo_dialog_overlap,
    )

    vo_cues = [{"id": "cue_01", "start_s": 10.0, "dur_s": 5.0}]
    live_en = [{"start_s": 12.0, "end_s": 16.0, "spoken_lang": "en"}]
    with pytest.raises(SameLanguageAudioOverlapError):
        verify_no_same_language_vo_dialog_overlap(vo_cues, live_en, edition_lang="en")

    # Foreign language speech (Spanish/Russian) under English VO is allowed (camera speech is ducked -12 dB)
    live_es = [{"start_s": 12.0, "end_s": 16.0, "spoken_lang": "es"}]
    verify_no_same_language_vo_dialog_overlap(vo_cues, live_es, edition_lang="en")

    # SFX peak_ms alignment against 03_Audio_Library/02_SFX/catalog.json
    catalog_path = studio_root / "03_Audio_Library" / "02_SFX" / "catalog.json"
    import json

    cat = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = cat if isinstance(cat, list) else cat["effects"]
    sample_entry = next(e for e in entries if e.get("peak_ms", 0) > 50)
    cut_boundary_s = 10.0
    aligned_start = resolve_sfx_start_s(
        sfx_relpath=sample_entry["relpath"],
        target_s=cut_boundary_s,
        align_peak=True,
        sfx_catalog_path=catalog_path,
    )
    expected = round(cut_boundary_s - (sample_entry["peak_ms"] / 1000.0), 3)
    assert aligned_start == pytest.approx(expected, abs=0.005)
