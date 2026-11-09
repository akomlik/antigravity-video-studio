#!/usr/bin/env python3
"""
build_timeline.py — Universal Declarative 4K Timeline Builder (AGVS Studio v2)

Eliminates per-project `assemble_<project>.py` and `build_<project>_overlays.py` scripts!
Reads declarative project data from `<project_dir>/timeline_spec.json` and `<project_dir>/Storyboard.md`,
enforces the Mandatory Music Non-Reuse Law, renders Warm Vintage Parchment overlays & AGVS bookends,
paces trilingual voice-overs, mixes 4-track broadcast audio, builds `.fcproj`, polishes via `assemble_engine.py`,
and exports/remuxes 4K Master & Russian (`_RU.mp4`) editions.

Usage:
  python3 .agents/skills/build-timeline/scripts/build_timeline.py --project-dir 04_Project_Catalog/2026/<project> [--render-export] [--mux-audio-only]
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

TICKS_PER_SEC = 254016000000

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
if str(STUDIO_ROOT) not in sys.path:
    sys.path.insert(0, str(STUDIO_ROOT))

import studio_config

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from assemble_engine import calculate_bgm_gains, measure_mean_volume_db, verify_music_non_reuse
from gpx_widgets import render_declarative_overlays


def get_duration(p: Path) -> float:
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(p),
    ]
    out = subprocess.check_output(cmd).decode().strip()
    return float(out)


def probe_media_dimensions(p: Path, is_still: bool) -> tuple[int, int]:
    """Dynamically probes width & height of any image or video file without hardcoded filename checks."""
    if is_still:
        try:
            with Image.open(p) as im:
                return im.size
        except Exception:
            return (3840, 2160)
    try:
        cmd = [
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(p),
        ]
        info = json.loads(subprocess.check_output(cmd).decode())
        streams = info.get("streams", [])
        if streams:
            return int(streams[0].get("width", 3840)), int(streams[0].get("height", 2160))
    except Exception:
        pass
    return (3840, 2160)


def fmt_srt_tc(sec: float) -> str:
    sec = max(0.0, float(sec))
    whole = int(sec)
    ms = int(round((sec - whole) * 1000))
    if ms >= 1000:
        whole += 1
        ms -= 1000
    hh = whole // 3600
    mm = (whole % 3600) // 60
    ss = whole % 60
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"


def check_zero_project_scripts_preflight(proj_dir: Path):
    """Enforces the Zero-Script Project Law: no per-project assemble_*.py or build_*_overlays.py scripts allowed."""
    rogue_scripts = list(proj_dir.glob("assemble_*.py")) + list(proj_dir.glob("build_*_overlays.py"))
    if rogue_scripts:
        names = ", ".join(p.name for p in rogue_scripts)
        raise RuntimeError(
            f"\n🚨 FATAL PRE-FLIGHT ERROR: Zero-Script Project Law Violation!\n"
            f"Found per-project Python script(s) in {proj_dir.name}: {names}\n"
            f"Delete all per-project scripts and use declarative `timeline_spec.json` + `build_timeline.py` exclusively."
        )


def check_bgm_non_reuse_preflight(proj_dir: Path, bgm_relpath: str, allow_used: bool = False):
    """Pre-flight check before any audio mixing or timeline assembly."""
    bgm_name = Path(bgm_relpath).name
    catalog_dir = STUDIO_ROOT / "04_Project_Catalog"
    curr_resolved = proj_dir.resolve()

    conflicts = []
    for other_proj in catalog_dir.glob("*/*"):
        if not other_proj.is_dir() or other_proj.resolve() == curr_resolved:
            continue
        for ext in ("*.fcproj", "Storyboard.md", "timeline_spec.json"):
            for f in other_proj.glob(ext):
                text = f.read_text(errors="ignore")
                if bgm_name in text:
                    conflicts.append((bgm_name, other_proj.name, f.name))

    if conflicts and not allow_used:
        lines = [f"  - '{c[0]}' already used in {c[1]} ({c[2]})" for c in conflicts]
        raise ValueError(
            f"\n🚨 FATAL PRE-FLIGHT ERROR: Article I Music Non-Reuse Law Violation!\n"
            f"Track '{bgm_name}' in {proj_dir.name} was already used in past projects:\n"
            + "\n".join(lines)
            + "\nSelect a fresh track using `/find-music` or `fetch_creatormix_catalog.py`."
        )
    print(f"✅ Pre-Flight Music Non-Reuse Check Passed: '{bgm_name}' is unique to {proj_dir.name}.")


def prepare_paced_voiceovers(proj_dir: Path, raw_dir: Path, vo_cues: list[dict]):
    print("Pacing & normalizing voiceover stems (-16.0 dB mean target)...")
    base_fc = (
        "silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB,"
        "areverse,silenceremove=start_periods=1:start_duration=0.05:start_threshold=-45dB,areverse,"
        "highpass=f=90,dynaudnorm=f=150:g=9:p=0.90,volume=2.0dB,alimiter=limit=0.92"
    )
    for lang in ("en", "ua", "ru"):
        for cue in vo_cues:
            cue_key = cue["id"]
            start_s = float(cue["start_s"])
            max_dur = float(cue.get("max_dur_s", 25.0))
            raw_wav = proj_dir / f"voiceover_{lang}_{cue_key}.wav"
            if not raw_wav.exists():
                continue
            paced_wav = proj_dir / f"voiceover_{lang}_{cue_key}_paced.wav"
            tmp_wav = proj_dir / f"voiceover_{lang}_{cue_key}_tmp.wav"
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(raw_wav), "-filter:a", base_fc, "-ar", "48000", "-ac", "2", str(tmp_wav)],
                check=True, capture_output=True,
            )
            dur = get_duration(tmp_wav)
            if dur > max_dur:
                tempo = min(1.35, max(1.01, (dur / max_dur) * 1.01))
                subprocess.run(
                    ["ffmpeg", "-y", "-i", str(tmp_wav), "-filter:a", f"atempo={tempo:.4f}", "-ar", "48000", "-ac", "2", str(paced_wav)],
                    check=True, capture_output=True,
                )
                tmp_wav.unlink(missing_ok=True)
                final_dur = get_duration(paced_wav)
                print(f"  [{lang}] {cue_key}: {dur:.2f}s -> {final_dur:.2f}s (atempo={tempo:.2f}x, window={start_s:.1f}s..{start_s+final_dur:.1f}s)")
            else:
                tmp_wav.replace(paced_wav)
                print(f"  [{lang}] {cue_key}: {dur:.2f}s (1.00x natural, window={start_s:.1f}s..{start_s+dur:.1f}s)")
            if raw_dir.exists():
                shutil.copy2(paced_wav, raw_dir / paced_wav.name)


def generate_srt_subtitles(proj_dir: Path, vo_cues: list[dict], live_subtitles: list[dict]):
    print("Generating scene-synced .srt subtitle tracks...")
    scripts_path = proj_dir / "narration_scripts.json"
    scripts = json.loads(scripts_path.read_text(encoding="utf-8")) if scripts_path.exists() else {"en": {}, "ua": {}, "ru": {}}

    for lang, suf in (("en", "en"), ("ua", "ua"), ("ru", "ru")):
        entries = []
        for lsub in live_subtitles:
            txt = lsub.get("text", {}).get(lang)
            if txt:
                entries.append((float(lsub["start_s"]), float(lsub["end_s"]), txt))

        for cue in vo_cues:
            cue_key = cue["id"]
            start_s = float(cue["start_s"])
            text = scripts.get(lang, {}).get(cue_key, "")
            paced_wav = proj_dir / f"voiceover_{lang}_{cue_key}_paced.wav"
            dur = get_duration(paced_wav) if paced_wav.exists() else float(cue.get("max_dur_s", 10.0))
            if text:
                entries.append((start_s, start_s + dur, text))

        entries.sort(key=lambda x: x[0])
        lines = []
        for idx, (st, et, txt) in enumerate(entries, 1):
            lines.append(str(idx))
            lines.append(f"{fmt_srt_tc(st)} --> {fmt_srt_tc(et)}")
            lines.append(txt)
            lines.append("")

        srt_path = proj_dir / f"captions.{suf}.srt"
        srt_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"  Generated -> {srt_path.name}")


def prepare_boosted_dialog_stems(proj_dir: Path, raw_dir: Path, boosted_dialogs: list[dict]):
    if not boosted_dialogs:
        return
    print("Preparing boosted camera dialogue stems...")
    for bd in boosted_dialogs:
        src = raw_dir / bd["source"]
        dst = proj_dir / bd["stem_file"]
        af = bd.get(
            "filter",
            "highpass=f=110,lowpass=f=7000,volume=18.0dB,dynaudnorm=f=100:g=7:p=0.92,volume=4.0dB,alimiter=limit=0.96",
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-ss", str(bd.get("src_in", 0.0)), "-t", str(bd["dur"]),
                "-i", str(src), "-filter:a", af, "-ar", "48000", "-ac", "2", str(dst),
            ],
            check=True, capture_output=True,
        )
        if raw_dir.exists():
            shutil.copy2(dst, raw_dir / dst.name)
        print(f"  Generated -> {dst.name}")


def build_broadcast_audio_mixes(
    proj_dir: Path,
    raw_dir: Path,
    overlays_dir: Path,
    bgm_track: Path,
    total_dur: float,
    cuts_spec: list[dict],
    boosted_dialogs: list[dict],
    sfx_cues: list[dict],
    vo_cues: list[dict],
):
    print("Building sample-accurate 4-track broadcast audio mixes...")
    bd_by_cut = {int(bd["cut_num"]): bd for bd in boosted_dialogs}

    cam_inputs = []
    cam_filter_parts = []
    dialog_parts = []
    dialog_inputs = []
    curr_t = 0.0
    input_idx = 0
    d_idx = 0

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
                f"[{input_idx}:a]volume={gain_db:.1f}dB,atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,adelay={int(curr_t*1000)}|{int(curr_t*1000)},apad=whole_dur={total_dur}s[c{cut_num}]"
            )
            input_idx += 1

            dialog_inputs.extend(["-i", str(stem_p)])
            dialog_parts.append(
                f"[{d_idx}:a]atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,adelay={int(curr_t*1000)}|{int(curr_t*1000)},apad=whole_dur={total_dur}s[d{d_idx}]"
            )
            d_idx += 1
        else:
            src = cut["source"]
            src_in = float(cut.get("src_in", 0.0))
            p = overlays_dir / src if (overlays_dir / src).exists() else raw_dir / src
            cam_inputs.extend(["-ss", f"{src_in:.2f}", "-t", f"{dur:.2f}", "-i", str(p)])
            gain_val = float(cut.get("a1_gain") if cut.get("a1_gain") is not None else -14.0)
            cam_filter_parts.append(
                f"[{input_idx}:a]highpass=f=90,volume={gain_val:.1f}dB,asetpts=PTS-STARTPTS,adelay={int(curr_t*1000)}|{int(curr_t*1000)},apad=whole_dur={total_dur}s[c{cut_num}]"
            )
            input_idx += 1
        curr_t += dur

    cam_mix_inputs = "".join(f"[c{c['cut_num']}]" for c in cuts_spec if not c.get("is_still", False))
    cam_fc = ";".join(cam_filter_parts) + f";{cam_mix_inputs}amix=inputs={input_idx}:duration=first:dropout_transition=0:normalize=0[cam_master]"
    cam_stem = proj_dir / "camera_audio_master.wav"
    subprocess.run(
        ["ffmpeg", "-y", *cam_inputs, "-filter_complex", cam_fc, "-map", "[cam_master]", "-t", str(total_dur), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(cam_stem)],
        check=True, capture_output=True,
    )
    print(f"  Created camera audio master stem -> {cam_stem.name}")

    dialog_key_stem = proj_dir / "dialog_key.wav"
    if d_idx > 0:
        d_mix = "".join(f"[d{i}]" for i in range(d_idx))
        d_fc = ";".join(dialog_parts) + f";{d_mix}amix=inputs={d_idx}:duration=first:dropout_transition=0:normalize=0[dialog_key]"
        subprocess.run(
            ["ffmpeg", "-y", *dialog_inputs, "-filter_complex", d_fc, "-map", "[dialog_key]", "-t", str(total_dur), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(dialog_key_stem)],
            check=True, capture_output=True,
        )
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(total_dur), "-c:a", "pcm_s16le", str(dialog_key_stem)],
            check=True, capture_output=True,
        )
    print(f"  Created dialogue ducking key stem -> {dialog_key_stem.name}")

    sfx_inputs = []
    sfx_parts = []
    for idx, sc in enumerate(sfx_cues):
        p = STUDIO_ROOT / "03_Audio_Library/02_SFX" / sc["file"]
        sfx_inputs.extend(["-i", str(p)])
        sgain = float(sc.get("gain_db", -10.0))
        st_s = float(sc["start_s"])
        sfx_parts.append(
            f"[{idx}:a]volume={sgain:.1f}dB,asetpts=PTS-STARTPTS,adelay={int(st_s*1000)}|{int(st_s*1000)},apad=whole_dur={total_dur}s[sfx{idx}]"
        )
    sfx_stem = proj_dir / "sfx_master.wav"
    if sfx_cues:
        sfx_mix = "".join(f"[sfx{i}]" for i in range(len(sfx_cues)))
        sfx_fc = ";".join(sfx_parts) + f";{sfx_mix}amix=inputs={len(sfx_cues)}:duration=first:dropout_transition=0:normalize=0[sfx_master]"
        subprocess.run(
            ["ffmpeg", "-y", *sfx_inputs, "-filter_complex", sfx_fc, "-map", "[sfx_master]", "-t", str(total_dur), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(sfx_stem)],
            check=True, capture_output=True,
        )
    else:
        subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-t", str(total_dur), "-c:a", "pcm_s16le", str(sfx_stem)],
            check=True, capture_output=True,
        )
    print(f"  Created SFX master stem -> {sfx_stem.name}")

    # Dynamic Midrange-Weighted RMS Loudness Calibration for BGM track (never hardcode -19.0 dB!)
    bgm_calib = calculate_bgm_gains(bgm_track, target_riding_db=-15.5, target_ducked_db=-21.5)
    raw_bgm_mean_db = bgm_calib["raw_mean_db"]
    ducked_gain_db = bgm_calib["ducked_gain_db"]
    riding_gain_db = bgm_calib["riding_gain_db"]
    swell_boost_db = bgm_calib["swell_boost_db"]
    eq_filter = bgm_calib["eq_filter"]
    eq_prefix = f"{eq_filter}," if eq_filter else ""
    mellow_tag = f" [Mellow/Chillhop +{bgm_calib['mellow_boost_db']:.1f} dB & 1.8kHz EQ]" if bgm_calib["is_mellow"] else ""
    print(
        f"  BGM Loudness Calibration ({bgm_track.name}){mellow_tag}: 180Hz-mean={raw_bgm_mean_db:.1f} dB -> "
        f"riding_gain={riding_gain_db:+.1f} dB (target {bgm_calib['target_riding_db']:.1f} dB RMS) | "
        f"ducked_gain={ducked_gain_db:+.1f} dB (target {bgm_calib['target_ducked_db']:.1f} dB RMS, {swell_boost_db:.1f} dB duck)"
    )

    for lang in ("en", "ua", "ru"):
        vo_inputs = []
        vo_parts = []
        for vidx, cue in enumerate(vo_cues):
            p = proj_dir / f"voiceover_{lang}_{cue['id']}_paced.wav"
            vo_inputs.extend(["-i", str(p)])
            st_s = float(cue["start_s"])
            vo_parts.append(
                f"[{4+vidx}:a]volume=2.0dB,asetpts=PTS-STARTPTS,adelay={int(st_s*1000)}|{int(st_s*1000)},apad=whole_dur={total_dur}s[vo{vidx}]"
            )
        vo_mix = "".join(f"[vo{i}]" for i in range(len(vo_cues)))
        vo_fc = ";".join(vo_parts) + f";{vo_mix}amix=inputs={len(vo_cues)}:duration=first:dropout_transition=0:normalize=0[vo_raw];[vo_raw]asplit=2[vo_duck_key][vo_mix_out]"

        duck_fc = (
            f"{vo_fc};"
            f"[3:a][vo_duck_key]amix=inputs=2:duration=first:dropout_transition=0:normalize=0[all_speech];"
            f"[0:a]{eq_prefix}volume={riding_gain_db:.1f}dB,afade=t=in:st=0.0:d=1.5:curve=hsin,afade=t=out:st={total_dur - 2.5:.1f}:d=2.5:curve=hsin[bgm_base];"
            f"[bgm_base][all_speech]sidechaincompress=threshold=0.10:ratio=1.8:attack=100:release=500[bgm_ducked];"
            f"[1:a][2:a][bgm_ducked][vo_mix_out]amix=inputs=4:duration=first:dropout_transition=0:normalize=0[out_master];"
            f"[out_master]alimiter=limit=0.95[norm_master]"
        )

        out_wav = proj_dir / f"full_audio_{lang}.wav"
        out_m4a = proj_dir / f"full_audio_{lang}.m4a"
        subprocess.run(
            [
                "ffmpeg", "-y", "-i", str(bgm_track), "-i", str(cam_stem), "-i", str(sfx_stem),
                "-i", str(dialog_key_stem), *vo_inputs, "-filter_complex", duck_fc,
                "-map", "[norm_master]", "-t", str(total_dur), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out_wav),
            ],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(out_wav), "-c:a", "aac", "-b:a", "192k", str(out_m4a)],
            check=True, capture_output=True,
        )
        print(f"  Generated Broadcast Audio Mix -> {out_m4a.name} ({out_m4a.stat().st_size // 1024} KB)")
    return riding_gain_db


def make_static_motion(src_w, src_h, pos_x=1920.0, pos_y=1080.0, scale=100.0):
    return {
        "effect": "motion",
        "enabled": True,
        "params": {
            "position": {"value": {"Vec2": {"x": pos_x, "y": pos_y}}},
            "scale": {"value": {"Float": scale}},
            "scale_width": {"value": {"Float": 100.0}},
            "uniform_scale": {"value": {"Bool": True}},
            "rotation": {"value": {"Float": 0.0}},
            "anchor": {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}},
            "anti_flicker": {"value": {"Float": 0.0}},
        },
    }


def make_opacity_in_out(duration_s: float, fade_in_s: float = 0.25, fade_out_s: float = 0.30):
    dur_ticks = int(round(duration_s * 30)) * (TICKS_PER_SEC // 30)
    in_ticks = int(round(fade_in_s * 30)) * (TICKS_PER_SEC // 30)
    out_ticks = int(round(fade_out_s * 30)) * (TICKS_PER_SEC // 30)
    out_start_ticks = max(in_ticks, dur_ticks - out_ticks)

    kfs = []
    if in_ticks > 0:
        kfs.append({"time": 0, "value": {"Float": 0.0}, "interp": "EaseIn", "in_influence": 0.33, "out_influence": 0.33})
        kfs.append({"time": in_ticks, "value": {"Float": 100.0}, "interp": "EaseOut", "in_influence": 0.33, "out_influence": 0.33})
    else:
        kfs.append({"time": 0, "value": {"Float": 100.0}, "interp": "Linear", "in_influence": 0.33, "out_influence": 0.33})

    if out_ticks > 0:
        kfs.append({"time": out_start_ticks, "value": {"Float": 100.0}, "interp": "EaseIn", "in_influence": 0.33, "out_influence": 0.33})
        kfs.append({"time": dur_ticks, "value": {"Float": 0.0}, "interp": "EaseOut", "in_influence": 0.33, "out_influence": 0.33})
    else:
        kfs.append({"time": dur_ticks, "value": {"Float": 100.0}, "interp": "Linear", "in_influence": 0.33, "out_influence": 0.33})

    return {
        "effect": "opacity",
        "enabled": True,
        "params": {
            "opacity": {
                "value": {"Float": 100.0},
                "keyframes": kfs,
            },
            "blend": {"value": {"Choice": 0}},
        },
    }


def build_fcproj_from_spec(
    proj_dir: Path,
    raw_dir: Path,
    overlays_dir: Path,
    fcproj_path: Path,
    bgm_track: Path,
    total_dur: float,
    cuts_spec: list[dict],
    expanded_overlays: list[dict],
    boosted_dialogs: list[dict],
    sfx_cues: list[dict],
    vo_cues: list[dict],
    riding_gain_db: float = -8.0,
):
    print(f"Building complete 4K .fcproj project -> {fcproj_path}")
    next_id = 1
    items = {}
    root_children = []

    def register_media(path: Path, kind_type: str, width=None, height=None, dur_s=180.0, rgba_png=False):
        nonlocal next_id
        mid = next_id
        next_id += 1
        root_children.append({"Item": mid})
        file_sz = path.stat().st_size
        fp = hashlib.md5(path.name.encode()).hexdigest()[:16]

        if kind_type == "Still":
            is_png = path.suffix.lower() == ".png"
            media_info = {
                "name": path.name,
                "kind": "Still",
                "duration": int(round(dur_s * 30)) * (TICKS_PER_SEC // 30),
                "video": {
                    "width": width or 3840,
                    "height": height or 2160,
                    "frame_rate": {"num": 30, "den": 1},
                    "par": [1, 1],
                    "codec": "PNG" if is_png else "JPG",
                    "pixel_format": "RGBA 8-bit" if (is_png and rgba_png) else "RGB 8-bit",
                    "color": {"matrix": "Bt709", "transfer": "Srgb", "primaries": "Bt709", "range": "Full"},
                    "has_alpha": bool(is_png and rgba_png),
                    "bitrate": None,
                },
                "audio_streams": [],
                "container": "Image",
                "start_timecode": None,
                "file_size": file_sz,
            }
            lbl = "Lavender"
        elif kind_type == "Movie":
            media_info = {
                "name": path.name,
                "kind": "Movie",
                "duration": int(round(dur_s * 30)) * (TICKS_PER_SEC // 30),
                "video": {
                    "width": width or 3840,
                    "height": height or 2160,
                    "frame_rate": {"num": 30, "den": 1},
                    "par": [1, 1],
                    "codec": "HEVC" if "MOV" in path.name.upper() else "H.264",
                    "pixel_format": "YUV 4:2:0 8-bit",
                    "color": {"matrix": "Bt709", "transfer": "Bt709", "primaries": "Bt709", "range": "Limited"},
                    "has_alpha": False,
                    "bitrate": 75000000,
                },
                "audio_streams": [{"sample_rate": 48000, "channels": 2, "codec": "AAC", "bits_per_sample": None}],
                "container": "QuickTime",
                "start_timecode": None,
                "file_size": file_sz,
            }
            lbl = "Iris"
        else:
            is_wav = path.suffix.lower() == ".wav"
            media_info = {
                "name": path.name,
                "kind": "AudioOnly",
                "duration": int(round(dur_s * 30)) * (TICKS_PER_SEC // 30),
                "audio_streams": [{
                    "sample_rate": 48000 if is_wav else 44100,
                    "channels": 2,
                    "codec": "PCM" if is_wav else "MP3",
                    "bits_per_sample": 16 if is_wav else None,
                }],
                "container": "WAV" if is_wav else "MP3",
                "start_timecode": None,
                "file_size": file_sz,
            }
            lbl = "Teal"

        items[str(mid)] = {
            "id": mid,
            "name": path.name,
            "label": lbl,
            "kind": {
                "Media": {
                    "media": {"File": {"path": str(path.resolve())}},
                    "info": media_info,
                    "interpret": {"frame_rate": None, "par": None, "ignore_alpha": False, "invert_alpha": False},
                    "mark_in": None,
                    "mark_out": None,
                    "markers": [],
                    "offline": False,
                    "proxy": None,
                    "identity": {"size": file_sz, "fingerprint": fp},
                }
            },
            "metadata": {},
            "created": mid,
        }
        return mid

    bgm_media_id = register_media(bgm_track, "AudioOnly", dur_s=total_dur)

    bd_aids = {}
    bd_by_cut = {}
    for bd in boosted_dialogs:
        cnum = int(bd["cut_num"])
        bd_by_cut[cnum] = bd
        bd_aids[cnum] = register_media(proj_dir / bd["stem_file"], "AudioOnly", dur_s=float(bd["dur"]))

    vo_en_ids = {}
    vo_ru_ids = {}
    for cue in vo_cues:
        ckey = cue["id"]
        p_en = proj_dir / f"voiceover_en_{ckey}_paced.wav"
        p_ru = proj_dir / f"voiceover_ru_{ckey}_paced.wav"
        vo_en_ids[ckey] = register_media(p_en, "AudioOnly", dur_s=get_duration(p_en))
        vo_ru_ids[ckey] = register_media(p_ru, "AudioOnly", dur_s=get_duration(p_ru))

    sfx_ids = {}
    for sc in sfx_cues:
        sname = sc["file"]
        if sname not in sfx_ids:
            p = STUDIO_ROOT / "03_Audio_Library/02_SFX" / sname
            sfx_ids[sname] = register_media(p, "AudioOnly", dur_s=get_duration(p))

    overlay_ids = {}
    for ov in expanded_overlays:
        oname = ov["file"]
        if oname not in overlay_ids:
            p = overlays_dir / oname
            overlay_ids[oname] = register_media(p, "Still", width=3840, height=2160, dur_s=total_dur, rgba_png=True)

    cuts_media_ids = {}
    cuts_dims = {}
    for cut in cuts_spec:
        cnum = int(cut["cut_num"])
        src = cut["source"]
        is_still = bool(cut.get("is_still", False))
        dur = float(cut["dur"])
        src_in = float(cut.get("src_in", 0.0))
        p = overlays_dir / src if (overlays_dir / src).exists() else raw_dir / src
        w, h = probe_media_dimensions(p, is_still)
        cuts_dims[cnum] = (w, h)
        if is_still:
            cuts_media_ids[cnum] = register_media(p, "Still", width=w, height=h, dur_s=dur)
        else:
            cuts_media_ids[cnum] = register_media(p, "Movie", width=w, height=h, dur_s=src_in + dur + 10.0)

    ticks_per_frame = TICKS_PER_SEC // 30
    v1_items, a1_items, v2_items, v3_items, v4_items, a2_items, a3_items, a4_items, a5_items = [], [], [], [], [], [], [], [], []

    curr_frame = 0
    for cut in cuts_spec:
        cnum = int(cut["cut_num"])
        src = cut["source"]
        is_still = bool(cut.get("is_still", False))
        src_in = float(cut.get("src_in", 0.0))
        dur = float(cut["dur"])
        a1_gain = cut.get("a1_gain")

        dur_frames = int(round(dur * 30))
        start_ticks = curr_frame * ticks_per_frame
        dur_ticks = dur_frames * ticks_per_frame
        in_ticks = int(round(src_in * 30)) * ticks_per_frame
        mid = cuts_media_ids[cnum]
        w, h = cuts_dims[cnum]

        v1_items.append({
            "id": next_id,
            "item": mid,
            "name": src,
            "label": "Iris" if not is_still else "Lavender",
            "start": start_ticks,
            "duration": dur_ticks,
            "source_in": in_ticks,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [make_static_motion(w, h)],
            "markers": [],
            "gain_db": 0.0,
            "essential_sound": None,
            "frame_hold": None,
            "scale_to_frame": True,
        })
        next_id += 1

        if not is_still:
            cid_a1 = next_id
            next_id += 1
            if cnum in bd_by_cut:
                bd = bd_by_cut[cnum]
                a1_items.append({
                    "id": cid_a1,
                    "item": bd_aids[cnum],
                    "name": bd["stem_file"],
                    "label": "Caribbean",
                    "start": start_ticks,
                    "duration": dur_ticks,
                    "source_in": 0,
                    "speed": 1.0,
                    "reverse": False,
                    "enabled": True,
                    "link": None,
                    "group": None,
                    "effects": [],
                    "markers": [],
                    "gain_db": float(bd.get("mix_gain_db", 0.0)),
                    "frame_hold": None,
                    "scale_to_frame": False,
                })
            else:
                a1_items.append({
                    "id": cid_a1,
                    "item": mid,
                    "name": src,
                    "label": "Iris",
                    "start": start_ticks,
                    "duration": dur_ticks,
                    "source_in": in_ticks,
                    "speed": 1.0,
                    "reverse": False,
                    "enabled": True,
                    "link": None,
                    "group": None,
                    "effects": [],
                    "markers": [],
                    "gain_db": float(a1_gain if a1_gain is not None else -14.0),
                    "frame_hold": None,
                    "scale_to_frame": False,
                })
        curr_frame += dur_frames

    for ov in expanded_overlays:
        oname = ov["file"]
        st_s = float(ov["start_s"])
        dur_s = float(ov["dur_s"])
        fade_in_s = float(ov.get("fade_in_s", 0.25))
        fade_out_s = float(ov.get("fade_out_s", 0.30))
        target_track = ov.get("track", "V2")
        item_dict = {
            "id": next_id,
            "item": overlay_ids[oname],
            "name": Path(oname).name,
            "label": "Cerulean" if target_track == "V2" else ("Mango" if target_track == "V3" else "Lavender"),
            "start": int(round(st_s * 30)) * ticks_per_frame,
            "duration": int(round(dur_s * 30)) * ticks_per_frame,
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [
                make_static_motion(3840, 2160),
                make_opacity_in_out(dur_s, fade_in_s=fade_in_s, fade_out_s=fade_out_s),
            ],
            "markers": [],
            "gain_db": 0.0,
            "frame_hold": None,
            "scale_to_frame": True,
        }
        if target_track == "V4":
            v4_items.append(item_dict)
        elif target_track == "V3":
            v3_items.append(item_dict)
        else:
            v2_items.append(item_dict)
        next_id += 1

    bgm_clip_id = next_id
    next_id += 1
    a2_items.append({
        "id": bgm_clip_id,
        "item": bgm_media_id,
        "name": bgm_track.name,
        "label": "Caribbean",
        "start": 0,
        "duration": int(round(total_dur * 30)) * ticks_per_frame,
        "source_in": 0,
        "speed": 1.0,
        "reverse": False,
        "enabled": True,
        "link": None,
        "group": None,
        "effects": [],
        "markers": [],
        "gain_db": float(riding_gain_db),
        "frame_hold": None,
        "scale_to_frame": False,
    })
    tid_outro = next_id
    next_id += 1
    a2_transitions = [{
        "id": tid_outro,
        "effect": {"effect": "constant_power", "enabled": True, "params": {}},
        "start": int(round((total_dur - 2.5) * 30)) * ticks_per_frame,
        "duration": int(round(2.5 * 30)) * ticks_per_frame,
        "from": bgm_clip_id,
        "to": None,
        "align": "EndAtCut",
        "reverse": False,
    }]

    for sc in sfx_cues:
        sname = sc["file"]
        st_s = float(sc["start_s"])
        sgain = float(sc.get("gain_db", -10.0))
        dur = get_duration(STUDIO_ROOT / "03_Audio_Library/02_SFX" / sname)
        a3_items.append({
            "id": next_id,
            "item": sfx_ids[sname],
            "name": Path(sname).name,
            "label": "Mango",
            "start": int(round(st_s * 30)) * ticks_per_frame,
            "duration": int(round(dur * 30)) * ticks_per_frame,
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": sgain,
            "frame_hold": None,
            "scale_to_frame": False,
        })
        next_id += 1

    for cue in vo_cues:
        ckey = cue["id"]
        st_s = float(cue["start_s"])
        dur_en = get_duration(proj_dir / f"voiceover_en_{ckey}_paced.wav")
        a4_items.append({
            "id": next_id,
            "item": vo_en_ids[ckey],
            "name": f"voiceover_en_{ckey}_paced.wav",
            "label": "Forest",
            "start": int(round(st_s * 30)) * ticks_per_frame,
            "duration": int(round(dur_en * 30)) * ticks_per_frame,
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": 2.0,
            "frame_hold": None,
            "scale_to_frame": False,
        })
        next_id += 1

        dur_ru = get_duration(proj_dir / f"voiceover_ru_{ckey}_paced.wav")
        a5_items.append({
            "id": next_id,
            "item": vo_ru_ids[ckey],
            "name": f"voiceover_ru_{ckey}_paced.wav",
            "label": "Forest",
            "start": int(round(st_s * 30)) * ticks_per_frame,
            "duration": int(round(dur_ru * 30)) * ticks_per_frame,
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": 2.0,
            "frame_hold": None,
            "scale_to_frame": False,
        })
        next_id += 1

    def parse_srt(srt_file):
        caps = []
        nonlocal next_id
        if not srt_file.exists():
            return caps
        content = srt_file.read_text(encoding="utf-8")
        for b in content.strip().split("\n\n"):
            b_lines = [l.strip() for l in b.splitlines() if l.strip()]
            if len(b_lines) >= 3 and "-->" in b_lines[1]:
                t_parts = b_lines[1].split("-->")
                st = int(t_parts[0].split(":")[0]) * 3600 + int(t_parts[0].split(":")[1]) * 60 + float(t_parts[0].split(":")[2].replace(",", "."))
                et = int(t_parts[1].split(":")[0]) * 3600 + int(t_parts[1].split(":")[1]) * 60 + float(t_parts[1].split(":")[2].replace(",", "."))
                cid = next_id
                next_id += 1
                caps.append({
                    "id": cid,
                    "text": " ".join(b_lines[2:]),
                    "speaker": None,
                    "cue_id": None,
                    "settings": "",
                    "start": int(round(st * 30)) * ticks_per_frame,
                    "duration": int(round((et - st) * 30)) * ticks_per_frame,
                })
        return caps

    c1_en = parse_srt(proj_dir / "captions.en.srt")
    c2_ua = parse_srt(proj_dir / "captions.ua.srt")
    c3_ru = parse_srt(proj_dir / "captions.ru.srt")

    cap_style = {
        "font": "Inter",
        "size": 54.0,
        "color": [255, 255, 255, 255],
        "background": True,
        "background_color": [0, 0, 0, 191],
        "align": "Center",
        "anchor": "Bottom",
        "margin": 0.08,
        "line_spacing": 1.25,
        "outline": 0.0,
        "outline_color": [0, 0, 0, 255],
        "font_style": "SemiBold",
    }

    seq_id = next_id
    next_id += 1
    root_children.append({"Item": seq_id})

    def make_track(tid, kind, name, track_items, transitions=None, muted=False):
        return {
            "id": tid,
            "kind": kind,
            "name": name,
            "enabled": True,
            "locked": False,
            "sync_lock": True,
            "muted": muted,
            "solo": False,
            "channels": "Stereo",
            "volume_db": 0.0,
            "pan": 0.0,
            "effects": [],
            "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
            "items": track_items,
            "transitions": transitions or [],
        }

    items[str(seq_id)] = {
        "id": seq_id,
        "name": proj_dir.name,
        "label": "Iris",
        "kind": {
            "Sequence": {
                "settings": {
                    "width": 3840,
                    "height": 2160,
                    "frame_rate": {"num": 30, "den": 1},
                    "par": [1, 1],
                    "sample_rate": 48000,
                    "drop_frame": False,
                    "preset": "3840x2160 30",
                    "audio_master": "Stereo",
                    "preview_codec": "ProRes 422",
                    "max_bit_depth": False,
                    "max_render_quality": False,
                    "working_space": "Rec. 709",
                    "color": {"working": "Rec709", "wide_gamut": False, "auto_tone_map": True},
                },
                "start_timecode": 0,
                "video_tracks": [
                    make_track(1, "Video", "Video 1", v1_items),
                    make_track(2, "Video", "V2 (Overlays / Badges)", v2_items),
                    make_track(3, "Video", "V3 (Bilingual Speech Cards)", v3_items),
                    make_track(4, "Video", "V4 (Live Telemetry HUD & Maps)", v4_items),
                ],
                "audio_tracks": [
                    make_track(1, "Audio", "A1 - Camera Audio", a1_items),
                    make_track(2, "Audio", f"A2 - Music ({bgm_track.stem})", a2_items, transitions=a2_transitions),
                    make_track(3, "Audio", "A3 - Cinematic SFX", a3_items),
                    make_track(4, "Audio", "Voice-Over (EN)", a4_items),
                    make_track(5, "Audio", "Russian Voice-Over (Alt)", a5_items, muted=True),
                ],
                "caption_tracks": [
                    {"id": 1, "name": "English", "format": "Subtitle", "language": "en", "style": cap_style, "enabled": True, "locked": False, "sync_lock": True, "captions": c1_en, "vtt_blocks": []},
                    {"id": 2, "name": "Українська", "format": "Subtitle", "language": "uk", "style": cap_style, "enabled": True, "locked": False, "sync_lock": True, "captions": c2_ua, "vtt_blocks": []},
                    {"id": 3, "name": "Русский", "format": "Subtitle", "language": "ru", "style": cap_style, "enabled": True, "locked": False, "sync_lock": True, "captions": c3_ru, "vtt_blocks": []},
                ],
                "markers": [],
                "mark_in": None,
                "mark_out": None,
                "work_area": None,
                "master_volume_db": 0.0,
                "master_effects": [],
                "master_mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                "submix_tracks": [],
            }
        },
        "metadata": {},
        "created": seq_id,
    }

    fcproj_data = {
        "format": "filmcraft.project",
        "schema_version": 17,
        "generator": "FilmCraft 0.18.0",
        "project": {
            "name": proj_dir.name,
            "settings": {
                "renderer": "FilmCraft GPU Acceleration (wgpu)",
                "video_display": "Timecode",
                "audio_display_samples": True,
                "default_still_duration": 1270080000000,
                "default_transition_duration_frames": 24,
                "default_audio_transition_duration": 254016000000,
                "ingest": {"enabled": False, "action": "createProxies", "destination": None, "preset": ""},
                "title_safe": [20.0, 20.0],
                "action_safe": [10.0, 10.0],
                "capture_format": "DV",
                "scratch": {"captured": None, "videoPreviews": None, "audioPreviews": None, "autoSave": None},
            },
            "root": {"id": 0, "name": proj_dir.name, "children": root_children},
            "items": items,
            "next_id": next_id + 50,
        },
        "view": {
            "open_sequences": [seq_id],
            "active_sequence": seq_id,
            "sequences": {str(seq_id): {"pps": 50.0, "scroll": 0.0, "v_scroll": 0.0, "a_scroll": 0.0, "video_track_h": 60.0, "audio_track_h": 56.0}},
            "playheads": {str(seq_id): 0},
        },
    }

    fcproj_path.write_text(json.dumps(fcproj_data, indent=2), encoding="utf-8")
    print(f"Project .fcproj written successfully ({fcproj_path.stat().st_size // 1024} KB)")


def remux_editions(proj_dir: Path, master_mp4: Path, ru_edition_mp4: Path):
    srt_en = proj_dir / "captions.en.srt"
    srt_ua = proj_dir / "captions.ua.srt"
    srt_ru = proj_dir / "captions.ru.srt"

    print("Losslessly remuxing Master EN 4K MP4 with custom VO & 3 soft subtitle streams...")
    temp_en = master_mp4.with_suffix(".tmp_en.mp4")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(master_mp4), "-i", str(proj_dir / "full_audio_en.m4a"),
            "-i", str(srt_en), "-i", str(srt_ua), "-i", str(srt_ru),
            "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0", "-map", "3:s:0", "-map", "4:s:0",
            "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
            "-metadata:s:a:0", "language=eng", "-metadata:s:a:0", "title=English",
            "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
            "-metadata:s:s:1", "language=ukr", "-metadata:s:s:1", "title=Українська",
            "-metadata:s:s:2", "language=rus", "-metadata:s:s:2", "title=Русский",
            str(temp_en),
        ],
        check=True, capture_output=True,
    )
    temp_en.replace(master_mp4)

    print("Losslessly remuxing Russian-voiced 4K Edition (_RU.mp4)...")
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(master_mp4), "-i", str(proj_dir / "full_audio_ru.m4a"),
            "-i", str(srt_en), "-i", str(srt_ua), "-i", str(srt_ru),
            "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0", "-map", "3:s:0", "-map", "4:s:0",
            "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
            "-metadata:s:a:0", "language=rus", "-metadata:s:a:0", "title=Русский",
            "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
            "-metadata:s:s:1", "language=ukr", "-metadata:s:s:1", "title=Українська",
            "-metadata:s:s:2", "language=rus", "-metadata:s:s:2", "title=Русский",
            str(ru_edition_mp4),
        ],
        check=True, capture_output=True,
    )
    print(f"Exported Master EN: {master_mp4}")
    print(f"Exported Russian Edition (_RU.mp4): {ru_edition_mp4}")


def main():
    p = argparse.ArgumentParser(description="Universal Declarative 4K Timeline Builder (AGVS Studio v2)")
    p.add_argument("--project-dir", required=True, help="Path to project directory in 04_Project_Catalog/YEAR/<project>")
    p.add_argument("--render-export", action="store_true", help="Render 4K MP4 via filmcraft-cli and remux EN/RU editions")
    p.add_argument("--mux-audio-only", action="store_true", help="Losslessly remux updated audio/subtitles into existing 4K MP4 in 0.4s without re-rendering video frames")
    p.add_argument("--allow-used-music", action="store_true", help="Override Music Non-Reuse Law check")
    args = p.parse_args()

    proj_dir = Path(args.project_dir).expanduser().resolve()
    spec_path = proj_dir / "timeline_spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"Missing declarative timeline_spec.json in {proj_dir}")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    year_str = proj_dir.parent.name
    raw_dir = studio_config.get_hot_media_dir() / year_str / proj_dir.name
    overlays_dir = proj_dir / "overlays"
    exports_dir = studio_config.get_exports_dir() / year_str
    fcproj_path = proj_dir / f"{proj_dir.name}.fcproj"
    master_mp4 = exports_dir / f"{proj_dir.name}.mp4"
    ru_edition_mp4 = exports_dir / f"{proj_dir.name}_RU.mp4"

    # 0. Pre-Flight Zero-Script Law & Music Non-Reuse Checks
    check_zero_project_scripts_preflight(proj_dir)
    bgm_rel = spec["bgm_track"]
    check_bgm_non_reuse_preflight(proj_dir, bgm_rel, allow_used=args.allow_used_music)
    bgm_track = STUDIO_ROOT / bgm_rel

    cuts_spec = spec["cuts"]
    total_dur = round(sum(float(c["dur"]) for c in cuts_spec), 2)
    overlays_spec = spec.get("overlays", [])
    boosted_dialogs = spec.get("boosted_dialogs", [])
    sfx_cues = spec.get("sfx_cues", [])
    vo_cues = spec.get("vo_cues", [])
    live_subtitles = spec.get("live_subtitles", [])

    # 2. Render Signature AGVS Bookends & Declarative Overlays (skip PNG rendering if mux-audio-only)
    if not args.mux_audio_only:
        bookends_cfg = spec.get("bookends", {})
        if bookends_cfg.get("enabled", True):
            bookends_script = SCRIPTS_DIR / "agvs_bookends.py"
            subprocess.run([
                sys.executable, str(bookends_script),
                "--project-dir", str(proj_dir),
                "--first-clip", str(raw_dir / bookends_cfg["first_clip"]),
                "--last-clip", str(raw_dir / bookends_cfg["last_clip"]),
            ], check=True)
        print("Rendering declarative Warm Vintage Parchment overlays & 1Hz Live Telemetry HUDs...")
    expanded_overlays = render_declarative_overlays(
        overlays_spec, overlays_dir, raw_dir=raw_dir, skip_render=args.mux_audio_only
    )

    # 3. Audio & Subtitles Pipeline
    prepare_paced_voiceovers(proj_dir, raw_dir, vo_cues)
    generate_srt_subtitles(proj_dir, vo_cues, live_subtitles)
    prepare_boosted_dialog_stems(proj_dir, raw_dir, boosted_dialogs)
    riding_gain_db = build_broadcast_audio_mixes(
        proj_dir, raw_dir, overlays_dir, bgm_track, total_dur,
        cuts_spec, boosted_dialogs, sfx_cues, vo_cues,
    )

    # 4. Build .fcproj & Polish via assemble_engine.py
    build_fcproj_from_spec(
        proj_dir, raw_dir, overlays_dir, fcproj_path, bgm_track, total_dur,
        cuts_spec, expanded_overlays, boosted_dialogs, sfx_cues, vo_cues,
        riding_gain_db=riding_gain_db,
    )
    engine_script = SCRIPTS_DIR / "assemble_engine.py"
    engine_cmd = [sys.executable, str(engine_script), "--project", str(fcproj_path)]
    if args.allow_used_music:
        engine_cmd.append("--allow-used-music")
    subprocess.run(engine_cmd, check=True)

    # 5. Open live in FilmCraft GUI
    cache_dir = Path("~/Movies/Cache_And_Previews").expanduser()
    cache_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(["open", "-a", "FilmCraft", "--args", "--control", "9876", str(fcproj_path)], cwd=str(cache_dir))

    # 6. Export or Fast Audio Remux
    if args.mux_audio_only and master_mp4.exists():
        remux_editions(proj_dir, master_mp4, ru_edition_mp4)
        print("Fast 0.4s audio/subtitle remux completed successfully!")
    elif args.render_export:
        exports_dir.mkdir(parents=True, exist_ok=True)
        print(f"Rendering 4K UHD Master Video via filmcraft-cli -> {master_mp4}")
        subprocess.run([
            "filmcraft-cli", "--project", str(fcproj_path), "export", str(master_mp4),
            "--preset", "Match Source – Adaptive High Bitrate",
            "--settings", '{"burnCaptions": false}',
        ], check=True)
        remux_editions(proj_dir, master_mp4, ru_edition_mp4)
        print("Declarative Studio v2 assembly and 4K MP4 export completed successfully!")


if __name__ == "__main__":
    main()
