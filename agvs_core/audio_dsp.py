"""Broadcast 4-track audio DSP: 180Hz midrange BGM calibration, keyframed ducking, single-pass Studio-Dry VO, and SFX peak alignment."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from agvs_core.config import find_binary, get_studio_root

TRIM_ONLY_VO_FILTER = (
    "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB,"
    "areverse,silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB,areverse"
)

STUDIO_DRY_CORE_FILTER = (
    "highpass=f=95,"
    "equalizer=f=380:width_type=q:w=1.4:g=-4.5,"
    "equalizer=f=600:width_type=q:w=1.6:g=-2.5,"
    "afftdn=nr=12:nf=-38:tn=1,"
    "agate=range=0.06:threshold=0.040:ratio=3.5:attack=10:release=90,"
    "loudnorm=I=-16:TP=-1.5:LRA=9"
)

STUDIO_DRY_VO_FILTER = f"{TRIM_ONLY_VO_FILTER},{STUDIO_DRY_CORE_FILTER}"


class VoiceoverDurationOverflowError(RuntimeError):
    """Raised when a narration cue exceeds max_dur_s (never stretch voice with atempo > 1.0)."""


class SameLanguageAudioOverlapError(RuntimeError):
    """Raised when synthetic narration on A4 overlaps same-language live speech on A1."""


def _norm_lang(lang: str) -> str:
    clean = (lang or "en").strip().lower()
    return "ua" if clean == "uk" else clean


def get_audio_duration(path: Path) -> float:
    ffprobe_bin = find_binary("ffprobe") or "ffprobe"
    out = subprocess.check_output(
        [
            ffprobe_bin, "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    ).decode("utf-8", errors="replace").strip()
    return float(out)


def has_studio_dry_marker(wav_path: Path) -> bool:
    """Check whether a WAV stem was already processed through STUDIO_DRY_CORE_FILTER."""
    sidecar = wav_path.with_suffix(wav_path.suffix + ".studio_dry")
    if sidecar.exists():
        return True
    ffprobe_bin = find_binary("ffprobe") or "ffprobe"
    try:
        out = subprocess.check_output(
            [
                ffprobe_bin, "-v", "error",
                "-show_entries", "format_tags=comment",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(wav_path),
            ],
            stderr=subprocess.DEVNULL,
        ).decode("utf-8", errors="replace")
        return "agvs_studio_dry=1" in out
    except Exception:
        return False


def pace_and_normalize_vo_cue(
    raw_wav: Path,
    out_wav: Path,
    max_dur_s: float,
    already_studio_dry: bool | None = None,
) -> tuple[Path, str]:
    """
    Trim leading/trailing silence and normalize VO cue to -16 LUFS in a SINGLE Studio-Dry pass.
    Raises VoiceoverDurationOverflowError if trimmed duration exceeds max_dur_s (zero atempo > 1.0).
    """
    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    is_dry = has_studio_dry_marker(raw_wav) if already_studio_dry is None else bool(already_studio_dry)
    applied_filter = TRIM_ONLY_VO_FILTER if is_dry else STUDIO_DRY_VO_FILTER

    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tmp_wav = out_wav.with_name(f"{out_wav.stem}.tmp_vo.wav")
    subprocess.run(
        [
            ffmpeg_bin, "-y",
            "-i", str(raw_wav),
            "-filter:a", applied_filter,
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
            "-metadata", "comment=agvs_studio_dry=1",
            str(tmp_wav),
        ],
        check=True,
        capture_output=True,
    )

    dur = get_audio_duration(tmp_wav)
    if dur > float(max_dur_s) + 0.05:
        tmp_wav.unlink(missing_ok=True)
        raise VoiceoverDurationOverflowError(
            f"Voiceover cue '{raw_wav.name}' trimmed duration ({dur:.2f}s) exceeds max_dur_s ({max_dur_s:.2f}s). "
            "Shorten narration copy or widen the cut window instead of time-stretching speech."
        )

    tmp_wav.replace(out_wav)
    return out_wav, applied_filter


def master_outro_fade_filter(total_dur_s: float, fade_dur_s: float = 2.2) -> str:
    """Return the synchronized Half-Sine S-curve outro audio fade filter."""
    st = max(0.0, float(total_dur_s) - float(fade_dur_s))
    return f"afade=t=out:st={st:.2f}:d={fade_dur_s:.2f}:curve=hsin"


def measure_volume_stats(audio_path: Path, highpass_hz: int | None = None) -> dict[str, float]:
    """
    Measure mean_volume and max_volume in dB via ffmpeg volumedetect.
    When highpass_hz is specified, cascades two 2-pole Butterworth high-pass stages (24 dB/oct)
    so heavy sub-bass (< 80 Hz) cannot skew midrange perceived loudness.
    """
    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    af = f"highpass=f={int(highpass_hz)},highpass=f={int(highpass_hz)},volumedetect" if highpass_hz else "volumedetect"
    out = subprocess.check_output(
        [ffmpeg_bin, "-i", str(audio_path), "-af", af, "-f", "null", "-"],
        stderr=subprocess.STDOUT,
    ).decode("utf-8", errors="replace")

    mean_vol = -16.0
    max_vol = -1.0
    for line in out.splitlines():
        if "mean_volume:" in line:
            try:
                mean_vol = float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except ValueError:
                pass
        elif "max_volume:" in line:
            try:
                max_vol = float(line.split("max_volume:")[1].split("dB")[0].strip())
            except ValueError:
                pass
    return {"mean_volume": mean_vol, "max_volume": max_vol}


def measure_mean_volume_db(audio_path: Path, highpass_hz: int | None = 180) -> float:
    return measure_volume_stats(audio_path, highpass_hz=highpass_hz)["mean_volume"]


def measure_integrated_lufs(audio_path: Path) -> float | None:
    """Measure EBU R128 integrated loudness (LUFS) via ffmpeg `ebur128`."""
    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    try:
        out = subprocess.check_output(
            [ffmpeg_bin, "-i", str(audio_path), "-af", "ebur128", "-f", "null", "-"],
            stderr=subprocess.STDOUT,
        ).decode("utf-8", errors="replace")
        summary_lines = [ln.strip() for ln in out.splitlines() if "I:" in ln and "LUFS" in ln]
        if summary_lines:
            val = float(summary_lines[-1].split("I:")[1].split("LUFS")[0].strip())
            if -70.0 < val <= 0.0:
                return val
    except Exception:
        pass
    return None


def is_mellow_bgm_track(bgm_path: Path) -> bool:
    """Detect mellow/chillhop/ambient tracks via keywords or BPM < 95."""
    s = str(bgm_path).lower()
    keywords = ("chillhop", "chill", "ambient", "warm", "scenic", "lofi")
    if any(kw in s for kw in keywords):
        return True
    m = re.search(r"(\d{2,3})\s*bpm", s)
    if m:
        try:
            if int(m.group(1)) < 95:
                return True
        except ValueError:
            pass
    return False


def calculate_bgm_gains(
    bgm_path: Path,
    target_riding_db: float | None = None,
    target_ducked_db: float | None = None,
    max_peak_headroom_db: float = -1.5,
    base_riding_db: float = -17.5,
    duck_amount_db: float = 11.5,
    mellow_boost_db: float = 1.5,
    max_riding_lufs: float = -15.5,
    max_ducked_lufs: float = -26.5,
) -> dict[str, Any]:
    """
    Calculate broadcast-balanced BGM fader gains, 180Hz midrange RMS, EBU R128 LUFS ceiling,
    1.8kHz presence EQ, and peak headroom guard:
    - Measures midrange loudness behind a 180 Hz high-pass filter so sub-bass does not starve sparse mellow tracks.
    - Enforces an EBU R128 integrated loudness ceiling (`max_riding_lufs = -15.5 LUFS`, `max_ducked_lufs = -26.5 LUFS`)
      so modern Brickwall-mastered chillhop/pop tracks (`-10 LUFS` raw, like "Indigo") NEVER overpower `-16 LUFS` narration!
    - Ducks smoothly by `11.5 dB` (`duck_amount_db`) under narration and live speech, guaranteeing `>= 10.5 LU`
      broadcast separation below `-16 LUFS` voice-over while remaining warmly audible on speakers.
    """
    raw_stats = measure_volume_stats(bgm_path, highpass_hz=None)
    mid_stats = measure_volume_stats(bgm_path, highpass_hz=180)
    raw_lufs = measure_integrated_lufs(bgm_path)
    raw_mean_db = raw_stats["mean_volume"]
    raw_max_db = raw_stats["max_volume"]
    midrange_mean_db = mid_stats["mean_volume"]

    is_mellow = is_mellow_bgm_track(bgm_path)
    applied_mellow_boost = round(float(mellow_boost_db), 2) if is_mellow else 0.0
    eq_filter = "equalizer=f=1800:t=q:w=1.2:g=2.0" if is_mellow else ""

    eff_riding_db = (
        round(float(base_riding_db) + applied_mellow_boost, 2)
        if target_riding_db is None
        else float(target_riding_db)
    )
    eff_ducked_db = (
        round(eff_riding_db - float(duck_amount_db), 2)
        if target_ducked_db is None
        else float(target_ducked_db)
    )

    safe_peak_ceiling = -2.0 if is_mellow else float(max_peak_headroom_db)
    max_allowed_gain_db = round(safe_peak_ceiling - raw_max_db, 1)

    desired_riding_gain_db = round(eff_riding_db - midrange_mean_db, 1)
    riding_gain_db = min(desired_riding_gain_db, max_allowed_gain_db)

    # EBU R128 LUFS Ceiling Guard: prevent hot-mastered tracks (-8..-11 LUFS) from overpowering narration
    eq_lufs_bump = 0.8 if is_mellow else 0.0
    if raw_lufs is not None and target_riding_db is None:
        lufs_riding_cap_gain = round(float(max_riding_lufs) - (raw_lufs + eq_lufs_bump), 1)
        riding_gain_db = min(riding_gain_db, lufs_riding_cap_gain)

    actual_duck_db = round(eff_riding_db - eff_ducked_db, 1)
    ducked_gain_db = round(riding_gain_db - actual_duck_db, 1)

    if raw_lufs is not None and target_ducked_db is None:
        lufs_ducked_cap_gain = round(float(max_ducked_lufs) - (raw_lufs + eq_lufs_bump), 1)
        ducked_gain_db = min(ducked_gain_db, lufs_ducked_cap_gain)

    swell_boost_db = round(riding_gain_db - ducked_gain_db, 1)

    return {
        "raw_mean_db": raw_mean_db,
        "raw_lufs": raw_lufs,
        "midrange_mean_db": midrange_mean_db,
        "raw_max_db": raw_max_db,
        "is_mellow": is_mellow,
        "mellow_boost_db": applied_mellow_boost,
        "target_riding_db": eff_riding_db,
        "target_ducked_db": eff_ducked_db,
        "base_target_riding_db": float(base_riding_db),
        "base_target_ducked_db": round(float(base_riding_db) - float(duck_amount_db), 2),
        "max_allowed_gain_db": max_allowed_gain_db,
        "riding_gain_db": riding_gain_db,
        "ducked_gain_db": ducked_gain_db,
        "swell_boost_db": swell_boost_db,
        "eq_filter": eq_filter,
    }


def compute_bgm_ducked_gain_db(bgm_path: Path, target_ducked_mean_db: float | None = None) -> float:
    res = calculate_bgm_gains(bgm_path, target_ducked_db=target_ducked_mean_db)
    return float(res["ducked_gain_db"])


def merge_speech_windows(windows: list[tuple[float, float]], min_gap_s: float = 0.45) -> list[tuple[float, float]]:
    """Merge overlapping or closely spaced speech windows to prevent BGM pumping between sentences."""
    cleaned = sorted((max(0.0, float(s)), max(0.0, float(e))) for s, e in windows if float(e) > float(s))
    if not cleaned:
        return []
    merged: list[tuple[float, float]] = [cleaned[0]]
    for st, ed in cleaned[1:]:
        prev_st, prev_ed = merged[-1]
        if st <= prev_ed + min_gap_s:
            merged[-1] = (prev_st, max(prev_ed, ed))
        else:
            merged.append((st, ed))
    return merged


def build_bgm_ducking_volume_expr(
    speech_windows: list[tuple[float, float]],
    duck_db: float = 11.5,
    ramp_s: float = 0.35,
) -> str:
    """
    Build a deterministic FFmpeg keyframed `volume` expression that smoothly ducks BGM by `duck_db`
    across merged speech windows (`vo_cues` + `boosted_dialogs`) with zero compressor pumping.
    """
    merged = merge_speech_windows(speech_windows)
    if not merged or duck_db <= 0:
        return "1.0"

    duck_lin = round(10.0 ** (-abs(float(duck_db)) / 20.0), 4)
    ramp = max(0.05, float(ramp_s))

    terms: list[str] = []
    for st, ed in merged:
        a0 = max(0.0, round(st - ramp, 2))
        a1 = round(st, 2)
        b0 = round(ed, 2)
        b1 = round(ed + ramp, 2)
        down_span = max(0.05, round(a1 - a0, 2))
        term = (
            f"if(between(t,{a0:.2f},{a1:.2f}),1.0-(1.0-{duck_lin})*(t-{a0:.2f})/{down_span:.2f},"
            f"if(between(t,{a1:.2f},{b0:.2f}),{duck_lin},"
            f"if(between(t,{b0:.2f},{b1:.2f}),{duck_lin}+(1.0-{duck_lin})*(t-{b0:.2f})/{ramp:.2f},1.0)))"
        )
        terms.append(term)

    expr = terms[0]
    for nxt in terms[1:]:
        expr = f"min({expr},{nxt})"
    return expr


def verify_no_same_language_vo_dialog_overlap(
    vo_cues: list[dict[str, Any]],
    live_dialogs: list[dict[str, Any]],
    edition_lang: str = "en",
    tolerance_s: float = 0.15,
) -> None:
    """
    Enforce Same-Language Live Dialogue Honor Law:
    A4 narration in `edition_lang` must never overlap live A1 camera speech in the SAME language.
    Foreign-language camera speech under translated VO is allowed (camera speech is ducked).
    """
    ed_norm = _norm_lang(edition_lang)
    for cue in vo_cues:
        vo_st = float(cue["start_s"])
        vo_ed = float(cue["end_s"]) if "end_s" in cue else vo_st + float(cue.get("dur_s", cue.get("max_dur_s", 0.0)))
        for dlg in live_dialogs:
            dlg_lang = _norm_lang(str(dlg.get("spoken_lang", "")))
            if not dlg_lang or dlg_lang != ed_norm:
                continue
            d_st = float(dlg["start_s"])
            d_ed = float(dlg["end_s"]) if "end_s" in dlg else d_st + float(dlg.get("dur", dlg.get("dur_s", 0.0)))
            overlap = min(vo_ed, d_ed) - max(vo_st, d_st)
            if overlap > tolerance_s:
                raise SameLanguageAudioOverlapError(
                    f"Edition [{edition_lang}] VO cue '{cue.get('id', '?')}' [{vo_st:.2f}s..{vo_ed:.2f}s] overlaps "
                    f"same-language live camera speech [{d_st:.2f}s..{d_ed:.2f}s] by {overlap:.2f}s."
                )


def filter_vo_cues_for_same_language_dialog(vo_cues: list, dialog_windows_by_lang: dict, lang: str) -> list:
    same_lang_windows = dialog_windows_by_lang.get(_norm_lang(lang), dialog_windows_by_lang.get(lang, []))
    if not same_lang_windows:
        return vo_cues
    filtered = []
    for cue in vo_cues:
        st, ed = cue[1], cue[2]
        overlaps = any(max(st, d_st) < min(ed, d_ed) - 0.15 for d_st, d_ed in same_lang_windows)
        if not overlaps:
            filtered.append(cue)
    return filtered


def load_sfx_catalog(sfx_catalog_path: Path | None = None) -> list[dict[str, Any]]:
    if sfx_catalog_path is None:
        sfx_catalog_path = get_studio_root() / "03_Audio_Library" / "02_SFX" / "catalog.json"
    if not sfx_catalog_path.exists():
        return []
    raw = json.loads(sfx_catalog_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return list(raw.get("effects") or raw.get("items") or [])
    return []


def resolve_sfx_start_s(
    sfx_relpath: str,
    target_s: float,
    align_peak: bool = False,
    sfx_catalog_path: Path | None = None,
) -> float:
    """
    Resolve timeline start_s for an A3 SFX cue.
    When align_peak=True, shifts start_s earlier by catalog `peak_ms` so the acoustic transient lands on `target_s`.
    """
    if not align_peak:
        return round(float(target_s), 3)

    entries = load_sfx_catalog(sfx_catalog_path)
    norm_rel = sfx_relpath.strip().lstrip("./")
    fname = Path(norm_rel).name
    for entry in entries:
        if entry.get("relpath") == norm_rel or entry.get("path") == norm_rel or entry.get("file") == fname:
            peak_ms = float(entry.get("peak_ms", 0.0))
            return max(0.0, round(float(target_s) - (peak_ms / 1000.0), 3))
    return round(float(target_s), 3)


def prepare_paced_voiceovers(
    proj_dir: Path,
    vo_cues: list[dict[str, Any]],
    languages: tuple[str, ...] = ("en", "ua", "ru"),
) -> dict[str, list[tuple[str, float, float, Path]]]:
    """
    Normalize and trim synthesized voiceover stems for each available language without double-dereverb or atempo stretching,
    and enforce non-overlap between adjacent cues.
    """
    resolved_by_lang: dict[str, list[tuple[str, float, float, Path]]] = {}
    if not vo_cues:
        return resolved_by_lang

    for lang in languages:
        lang_items: list[tuple[str, float, float, Path]] = []
        for cue in vo_cues:
            cue_key = cue["id"]
            start_s = float(cue["start_s"])
            max_dur = float(cue.get("max_dur_s", 25.0))
            raw_wav = proj_dir / f"voiceover_{lang}_{cue_key}.wav"
            paced_wav = proj_dir / f"voiceover_{lang}_{cue_key}_paced.wav"
            if raw_wav.exists():
                pace_and_normalize_vo_cue(raw_wav, paced_wav, max_dur_s=max_dur)
            if paced_wav.exists():
                dur = get_audio_duration(paced_wav)
                lang_items.append((cue_key, start_s, dur, paced_wav))

        for idx in range(len(lang_items) - 1):
            curr_id, curr_st, curr_dur, _ = lang_items[idx]
            next_id, next_st, _, _ = lang_items[idx + 1]
            curr_end = curr_st + curr_dur
            if curr_end > next_st + 0.05:
                raise VoiceoverDurationOverflowError(
                    f"Overlapping voiceover cues in [{lang}]: '{curr_id}' ends at {curr_end:.2f}s, "
                    f"colliding with '{next_id}' at {next_st:.2f}s."
                )
        if lang_items:
            resolved_by_lang[lang] = lang_items

    return resolved_by_lang


def prepare_boosted_dialog_stems(proj_dir: Path, raw_dir: Path, boosted_dialogs: list[dict[str, Any]]) -> None:
    """Extract sample-accurate boosted live dialogue stems (using filter-level atrim after -i)."""
    if not boosted_dialogs:
        return
    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    default_af = "highpass=f=120,lowpass=f=7000,volume=18.0dB,dynaudnorm=f=100:g=7:p=0.92,volume=4.0dB,alimiter=limit=0.96"
    for bd in boosted_dialogs:
        src = raw_dir / bd["source"]
        dst = proj_dir / bd["stem_file"]
        src_in = float(bd.get("src_in", 0.0))
        dur = float(bd["dur"])
        af = bd.get("filter", default_af)
        chain = f"atrim=start={src_in:.3f}:duration={dur:.3f},asetpts=PTS-STARTPTS,{af}"
        subprocess.run(
            [
                ffmpeg_bin, "-y",
                "-i", str(src),
                "-filter:a", chain,
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
                str(dst),
            ],
            check=True,
            capture_output=True,
        )


def build_broadcast_audio_mixes(
    proj_dir: Path,
    raw_dir: Path,
    overlays_dir: Path,
    bgm_track: Path,
    total_dur: float,
    cuts_spec: list[dict[str, Any]],
    boosted_dialogs: list[dict[str, Any]],
    sfx_cues: list[dict[str, Any]],
    vo_cues: list[dict[str, Any]],
    bgm_tracks_spec: list[dict[str, Any]] | None = None,
    languages: tuple[str, ...] = ("en", "ua", "ru"),
) -> float:
    """
    Build sample-accurate 4-track broadcast audio masters (`full_audio_{lang}.m4a`) with:
    - A1 camera audio + boosted live dialogue stems
    - A2 BGM calibrated via 180 Hz midrange RMS + keyframed 6.5 dB speech ducking (supports multi-phase bgm_tracks)
    - A3 peak-aligned SFX cues
    - A4 single-pass Studio-Dry narration cues (gracefully handling 0-VO or 0-video slideshows)
    """
    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    studio_root = get_studio_root()
    bd_by_cut = {int(bd["cut_num"]): bd for bd in boosted_dialogs}

    cam_inputs: list[str] = []
    cam_filter_parts: list[str] = []
    dialog_windows: list[tuple[float, float]] = []
    curr_t = 0.0
    input_idx = 0

    for cut in cuts_spec:
        cut_num = int(cut["cut_num"])
        dur = float(cut["dur"])
        if cut.get("is_still", False):
            curr_t += dur
            continue

        if cut_num in bd_by_cut:
            bd = bd_by_cut[cut_num]
            stem_p = proj_dir / bd["stem_file"]
            gain_db = float(bd.get("mix_gain_db", 0.0))
            cam_inputs.extend(["-i", str(stem_p)])
            cam_filter_parts.append(
                f"[{input_idx}:a]volume={gain_db:.1f}dB,atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,"
                f"adelay={int(curr_t * 1000)}|{int(curr_t * 1000)},apad=whole_dur={total_dur}s[c{cut_num}]"
            )
            dialog_windows.append((curr_t, curr_t + dur))
            input_idx += 1
        else:
            src = cut["source"]
            src_in = float(cut.get("src_in", 0.0))
            p = overlays_dir / src if (overlays_dir / src).exists() else raw_dir / src
            cam_inputs.extend(["-ss", f"{src_in:.2f}", "-t", f"{dur:.2f}", "-i", str(p)])
            gain_val = float(cut.get("a1_gain") if cut.get("a1_gain") is not None else -14.0)
            cam_filter_parts.append(
                f"[{input_idx}:a]highpass=f=90,volume={gain_val:.1f}dB,asetpts=PTS-STARTPTS,"
                f"adelay={int(curr_t * 1000)}|{int(curr_t * 1000)},apad=whole_dur={total_dur}s[c{cut_num}]"
            )
            input_idx += 1
        curr_t += dur

    cam_stem = proj_dir / "camera_audio_master.wav"
    if input_idx > 0:
        cam_mix_inputs = "".join(f"[c{c['cut_num']}]" for c in cuts_spec if not c.get("is_still", False))
        cam_fc = ";".join(cam_filter_parts) + f";{cam_mix_inputs}amix=inputs={input_idx}:duration=first:dropout_transition=0:normalize=0[cam_master]"
        subprocess.run(
            [
                ffmpeg_bin, "-y", *cam_inputs,
                "-filter_complex", cam_fc,
                "-map", "[cam_master]", "-t", str(total_dur),
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(cam_stem),
            ],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            [ffmpeg_bin, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(total_dur), "-c:a", "pcm_s16le", str(cam_stem)],
            check=True,
            capture_output=True,
        )

    sfx_stem = proj_dir / "sfx_master.wav"
    if sfx_cues:
        sfx_inputs: list[str] = []
        sfx_parts: list[str] = []
        for idx, sc in enumerate(sfx_cues):
            p = studio_root / "03_Audio_Library" / "02_SFX" / sc["file"]
            sfx_inputs.extend(["-i", str(p)])
            sgain = float(sc.get("gain_db", -10.0))
            st_s = resolve_sfx_start_s(sc["file"], float(sc["start_s"]), align_peak=bool(sc.get("align_peak", False)))
            sfx_parts.append(
                f"[{idx}:a]volume={sgain:.1f}dB,asetpts=PTS-STARTPTS,"
                f"adelay={int(st_s * 1000)}|{int(st_s * 1000)},apad=whole_dur={total_dur}s[sfx{idx}]"
            )
        sfx_mix = "".join(f"[sfx{i}]" for i in range(len(sfx_cues)))
        sfx_fc = ";".join(sfx_parts) + f";{sfx_mix}amix=inputs={len(sfx_cues)}:duration=first:dropout_transition=0:normalize=0[sfx_master]"
        subprocess.run(
            [
                ffmpeg_bin, "-y", *sfx_inputs,
                "-filter_complex", sfx_fc,
                "-map", "[sfx_master]", "-t", str(total_dur),
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(sfx_stem),
            ],
            check=True,
            capture_output=True,
        )
    else:
        subprocess.run(
            [ffmpeg_bin, "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(total_dur), "-c:a", "pcm_s16le", str(sfx_stem)],
            check=True,
            capture_output=True,
        )

    bgm_calib = calculate_bgm_gains(bgm_track)
    riding_gain_db = float(bgm_calib["riding_gain_db"])
    duck_amount_db = float(bgm_calib["swell_boost_db"])
    eq_filter = str(bgm_calib["eq_filter"])
    eq_prefix = f"{eq_filter}," if eq_filter else ""

    # Pre-render continuous (or multi-phase crossfaded) un-ducked BGM bed at riding_gain_db
    bgm_bed_stem = proj_dir / "bgm_bed_master.wav"
    if bgm_tracks_spec and len(bgm_tracks_spec) > 1:
        b_inputs: list[str] = []
        b_parts: list[str] = []
        for b_idx, b_item in enumerate(bgm_tracks_spec):
            bp = studio_root / b_item["file"]
            bc = calculate_bgm_gains(bp)
            bg_gain = float(bc["riding_gain_db"])
            beq = f"{bc['eq_filter']}," if bc["eq_filter"] else ""
            bst = float(b_item.get("start_s", 0.0))
            bed_end = float(b_item.get("end_s", total_dur))
            bdur = max(0.5, bed_end - bst)
            fin = 1.5 if b_idx == 0 else 1.8
            fout = 2.2 if b_idx == len(bgm_tracks_spec) - 1 else 1.8
            b_inputs.extend(["-stream_loop", "-1", "-t", f"{bdur:.2f}", "-i", str(bp)])
            b_parts.append(
                f"[{b_idx}:a]{beq}volume={bg_gain:.1f}dB,"
                f"afade=t=in:st=0:d={fin:.2f}:curve=hsin,"
                f"afade=t=out:st={max(0.0, bdur - fout):.2f}:d={fout:.2f}:curve=hsin,"
                f"adelay={int(bst * 1000)}|{int(bst * 1000)},apad=whole_dur={total_dur}s[bgm{b_idx}]"
            )
        bmix = "".join(f"[bgm{i}]" for i in range(len(bgm_tracks_spec)))
        bfc = ";".join(b_parts) + f";{bmix}amix=inputs={len(bgm_tracks_spec)}:duration=first:dropout_transition=0:normalize=0[bgm_bed]"
        subprocess.run(
            [
                ffmpeg_bin, "-y", *b_inputs,
                "-filter_complex", bfc,
                "-map", "[bgm_bed]", "-t", str(total_dur),
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(bgm_bed_stem),
            ],
            check=True,
            capture_output=True,
        )
    else:
        outro_st = max(0.0, total_dur - 2.2)
        subprocess.run(
            [
                ffmpeg_bin, "-y", "-stream_loop", "-1", "-i", str(bgm_track),
                "-af", f"{eq_prefix}volume={riding_gain_db:.1f}dB,afade=t=in:st=0.0:d=1.5:curve=hsin,afade=t=out:st={outro_st:.2f}:d=2.2:curve=hsin",
                "-t", str(total_dur), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(bgm_bed_stem),
            ],
            check=True,
            capture_output=True,
        )

    for lang in languages:
        avail_vo: list[tuple[float, float, Path]] = []
        for cue in vo_cues:
            p = proj_dir / f"voiceover_{lang}_{cue['id']}_paced.wav"
            if p.exists():
                avail_vo.append((float(cue["start_s"]), get_audio_duration(p), p))

        # Skip optional secondary languages if vo_cues were specified but not synthesized for that language
        if vo_cues and not avail_vo and lang != "en":
            continue

        speech_wins = list(dialog_windows) + [(st, st + dur) for st, dur, _ in avail_vo]
        vol_expr = build_bgm_ducking_volume_expr(speech_wins, duck_db=duck_amount_db, ramp_s=0.35)

        vo_inputs: list[str] = []
        vo_parts: list[str] = []
        for vidx, (st_s, _, p) in enumerate(avail_vo):
            vo_inputs.extend(["-i", str(p)])
            vo_parts.append(
                f"[{3 + vidx}:a]volume=0.0dB,asetpts=PTS-STARTPTS,"
                f"adelay={int(st_s * 1000)}|{int(st_s * 1000)},apad=whole_dur={total_dur}s[vo{vidx}]"
            )

        bgm_duck_chain = f"[0:a]volume='{vol_expr}':eval=frame[bgm_ducked]"
        if avail_vo:
            vo_mix = "".join(f"[vo{i}]" for i in range(len(avail_vo)))
            vo_fc = ";".join(vo_parts) + f";{vo_mix}amix=inputs={len(avail_vo)}:duration=first:dropout_transition=0:normalize=0[vo_master]"
            mix_fc = (
                f"{vo_fc};{bgm_duck_chain};"
                f"[1:a][2:a][bgm_ducked][vo_master]amix=inputs=4:duration=first:dropout_transition=0:normalize=0[out_master];"
                f"[out_master]alimiter=limit=0.89:level=false:attack=2[norm_master]"
            )
        else:
            mix_fc = (
                f"{bgm_duck_chain};"
                f"[1:a][2:a][bgm_ducked]amix=inputs=3:duration=first:dropout_transition=0:normalize=0[out_master];"
                f"[out_master]alimiter=limit=0.89:level=false:attack=2[norm_master]"
            )

        out_wav = proj_dir / f"full_audio_{lang}.wav"
        out_m4a = proj_dir / f"full_audio_{lang}.m4a"
        subprocess.run(
            [
                ffmpeg_bin, "-y",
                "-i", str(bgm_bed_stem),
                "-i", str(cam_stem),
                "-i", str(sfx_stem),
                *vo_inputs,
                "-filter_complex", mix_fc,
                "-map", "[norm_master]",
                "-t", str(total_dur),
                "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
                str(out_wav),
            ],
            check=True,
            capture_output=True,
        )
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(out_wav), "-c:a", "aac", "-b:a", "192k", str(out_m4a)],
            check=True,
            capture_output=True,
        )

    return riding_gain_db
