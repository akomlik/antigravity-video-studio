"""Declarative 4K `.fcproj` v17 timeline assembly, zero-gap V1 continuity, Ken Burns motion, and 4K edition exports."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps

from agvs_core.audio_dsp import (
    build_broadcast_audio_mixes,
    get_audio_duration,
    prepare_boosted_dialog_stems,
    prepare_paced_voiceovers,
    resolve_sfx_start_s,
)
from agvs_core.bookends import generate_project_bookends
from agvs_core.config import (
    find_binary,
    get_cache_dir,
    get_exports_dir,
    get_hot_media_dir,
    get_studio_root,
)
from agvs_core.filmcraft_env import verify_filmcraft_environment
from agvs_core.schemas import CalibrationMediaInTimelineError, RouteContinuityError
from agvs_core.vintage_cards import render_declarative_overlays, strip_unicode_emojis

TICKS_PER_SEC = 254016000000
PRESET_4K_MATCH_SOURCE = "Match Source – Adaptive High Bitrate"


def sanitize_caption_text(text: str) -> str:
    """Strip emoji glyphs that fail to render in Inter font, preserving standard punctuation and accents."""
    return strip_unicode_emojis(text)


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


def probe_media_dimensions(p: Path, is_still: bool) -> tuple[int, int]:
    """Probe width & height of an image or video file and enforce upright JPEG pixel orientation."""
    if is_still:
        try:
            if p.suffix.lower() in (".jpg", ".jpeg") and not p.is_symlink():
                with Image.open(p) as im:
                    ori = im.getexif().get(274, 1)
                    if ori != 1:
                        st = p.stat()
                        upright = ImageOps.exif_transpose(im)
                        exif_bytes = upright.info.get("exif")
                        save_kw: dict[str, Any] = {"quality": 95, "subsampling": 0}
                        if exif_bytes:
                            save_kw["exif"] = exif_bytes
                        upright.save(p, "JPEG", **save_kw)
                        exiftool_bin = find_binary("exiftool")
                        if exiftool_bin:
                            subprocess.run(
                                [exiftool_bin, "-overwrite_original", "-Orientation=1", "-n", str(p)],
                                check=False,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                        os.utime(p, (st.st_atime, st.st_mtime))
                        return upright.size
                    return im.size
            with Image.open(p) as im:
                return im.size
        except Exception:
            return (3840, 2160)
    try:
        ffprobe_bin = find_binary("ffprobe") or "ffprobe"
        cmd = [
            ffprobe_bin, "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height", "-of", "json", str(p),
        ]
        info = json.loads(subprocess.check_output(cmd).decode())
        streams = info.get("streams", [])
        if streams:
            return int(streams[0].get("width", 3840)), int(streams[0].get("height", 2160))
    except Exception:
        pass
    return (3840, 2160)


def ensure_blur_pillarbox_still(src_path: Path, overlays_dir: Path, seq_w: int = 3840, seq_h: int = 2160) -> Path:
    """Render non-destructive 4K composite in overlays/ with ambient blurred backdrop and uncropped photo."""
    overlays_dir.mkdir(parents=True, exist_ok=True)
    out_p = overlays_dir / f"pillarbox_{src_path.stem}.jpg"
    if out_p.exists() and out_p.stat().st_size > 50_000:
        return out_p

    with Image.open(src_path) as raw_im:
        im = ImageOps.exif_transpose(raw_im).convert("RGB")

    iw, ih = im.size
    low_w, low_h = 960, 540
    cover_scale = max(low_w / max(1, iw), low_h / max(1, ih))
    cw, ch = max(low_w, int(round(iw * cover_scale))), max(low_h, int(round(ih * cover_scale)))
    bg_low = im.resize((cw, ch), Image.Resampling.BILINEAR)
    left = (cw - low_w) // 2
    top = (ch - low_h) // 2
    bg_low = bg_low.crop((left, top, left + low_w, top + low_h))
    bg_low = bg_low.filter(ImageFilter.GaussianBlur(radius=22))
    bg_low = ImageEnhance.Brightness(bg_low).enhance(0.62)
    canvas = bg_low.resize((seq_w, seq_h), Image.Resampling.BICUBIC).convert("RGBA")

    margin_y = 32
    margin_x = 64
    fit_scale = min((seq_w - 2 * margin_x) / max(1, iw), (seq_h - 2 * margin_y) / max(1, ih))
    fw = int(round(iw * fit_scale))
    fh = int(round(ih * fit_scale))
    fx = (seq_w - fw) // 2
    fy = (seq_h - fh) // 2
    fg = im.resize((fw, fh), Image.Resampling.LANCZOS)

    pad = 44
    sh = Image.new("RGBA", (fw + 2 * pad, fh + 2 * pad), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rectangle([pad - 4, pad - 4, pad + fw + 4, pad + fh + 4], fill=(15, 12, 10, 125))
    sh = sh.filter(ImageFilter.GaussianBlur(radius=18))
    canvas.alpha_composite(sh, (fx - pad + 4, fy - pad + 8))

    framed = Image.new("RGBA", (fw + 8, fh + 8), (250, 246, 238, 255))
    framed.paste(fg.convert("RGBA"), (4, 4))
    canvas.alpha_composite(framed, (fx - 4, fy - 4))

    canvas.convert("RGB").save(out_p, "JPEG", quality=95, subsampling=0)
    return out_p


def verify_and_repair_v1_continuity(seq: dict[str, Any]) -> int:
    """
    Ensure V1 timeline items are strictly contiguous with zero black gaps or overlaps.
    Must run AFTER all clips and bookends are placed.
    """
    video_tracks = seq.get("video_tracks", [])
    if not video_tracks or not video_tracks[0].get("items"):
        return 0
    v1_items = video_tracks[0]["items"]
    v1_items.sort(key=lambda x: x.get("start", 0))

    current_ticks = 0
    repaired_gaps = 0
    for item in v1_items:
        start = item.get("start", 0)
        dur = item.get("duration", 0)
        if start != current_ticks:
            item["start"] = current_ticks
            repaired_gaps += 1
        current_ticks += dur
    return repaired_gaps


def attach_bookend_cuts_if_needed(
    cuts: list[dict[str, Any]],
    bookends_cfg: dict[str, Any] | None,
    overlays_dir: Path,
    raw_dir: Path,
) -> list[dict[str, Any]]:
    """
    Attach opening (`bookend_intro_4K.mp4`) and closing (`bookend_outro_4K.mp4`) cuts when
    `bookends.enabled` is true and they are not already explicitly listed in `cuts`.
    """
    out = [dict(c) for c in cuts]
    if not bookends_cfg or not bookends_cfg.get("enabled", False):
        return out

    intro_dur = float(bookends_cfg.get("intro_dur_s", bookends_cfg.get("intro_duration_s", 3.5)))
    outro_dur = float(bookends_cfg.get("outro_dur_s", bookends_cfg.get("outro_duration_s", 4.5)))

    has_intro = bool(out and str(out[0].get("source", "")).startswith("bookend_intro"))
    has_outro = bool(out and str(out[-1].get("source", "")).startswith("bookend_outro"))

    intro_exists = (overlays_dir / "bookend_intro_4K.mp4").exists() or (raw_dir / "bookend_intro_4K.mp4").exists()
    outro_exists = (overlays_dir / "bookend_outro_4K.mp4").exists() or (raw_dir / "bookend_outro_4K.mp4").exists()

    if not has_intro and intro_exists:
        out.insert(0, {
            "cut_num": 1,
            "source": "bookend_intro_4K.mp4",
            "is_still": False,
            "src_in": 0.0,
            "dur": intro_dur,
            "a1_gain": -14.0,
            "hud": False,
            "desc": "AGVS Opening Bookend",
        })
    if not has_outro and outro_exists:
        out.append({
            "cut_num": len(out) + 1,
            "source": "bookend_outro_4K.mp4",
            "is_still": False,
            "src_in": 0.0,
            "dur": outro_dur,
            "a1_gain": -14.0,
            "hud": False,
            "desc": "AGVS Closing Bookend",
        })

    for idx, c in enumerate(out, 1):
        c["cut_num"] = idx
    return out


def make_volume_effect(fade_in_s: float | None = None, fade_out_s: float | None = None, duration_s: float = 0.0) -> list[dict[str, Any]]:
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    keyframes = []
    if fade_in_s:
        in_ticks = int(fade_in_s * TICKS_PER_SEC)
        keyframes.append({"time": 0, "value": {"Float": -60.0}, "interp": "EaseIn", "in_influence": 1 / 3, "out_influence": 1 / 3})
        keyframes.append({"time": in_ticks, "value": {"Float": 0.0}, "interp": "EaseOut", "in_influence": 1 / 3, "out_influence": 1 / 3})
    if fade_out_s:
        out_start_ticks = max(0, dur_ticks - int(fade_out_s * TICKS_PER_SEC))
        keyframes.append({"time": out_start_ticks, "value": {"Float": 0.0}, "interp": "EaseIn", "in_influence": 1 / 3, "out_influence": 1 / 3})
        keyframes.append({"time": dur_ticks, "value": {"Float": -60.0}, "interp": "EaseOut", "in_influence": 1 / 3, "out_influence": 1 / 3})

    param_val: dict[str, Any] = {"value": {"Float": 0.0}}
    if keyframes:
        param_val["keyframes"] = keyframes
    return [
        {"effect": "volume", "enabled": True, "params": {"bypass": {"value": {"Bool": False}}, "level": param_val}},
        {"effect": "channel_volume", "enabled": True, "params": {"bypass": {"value": {"Bool": False}}, "left": {"value": {"Float": 0.0}}, "right": {"value": {"Float": 0.0}}}},
        {"effect": "panner", "enabled": True, "params": {"balance": {"value": {"Float": 0.0}}}},
    ]


def make_static_motion(src_w: int, src_h: int, seq_w: int = 3840, seq_h: int = 2160, scale: float = 100.0) -> dict[str, Any]:
    return {
        "effect": "motion",
        "enabled": True,
        "params": {
            "position": {"value": {"Vec2": {"x": seq_w / 2.0, "y": seq_h / 2.0}}},
            "scale": {"value": {"Float": float(scale)}},
            "scale_width": {"value": {"Float": 100.0}},
            "uniform_scale": {"value": {"Bool": True}},
            "rotation": {"value": {"Float": 0.0}},
            "anchor": {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}},
            "anti_flicker": {"value": {"Float": 0.0}},
        },
    }


def make_motion_ken_burns(
    duration_s: float,
    src_w: int,
    src_h: int,
    seq_w: int = 3840,
    seq_h: int = 2160,
    zoom_in: bool = True,
    start_pos: tuple[float, float] | list[float] | None = None,
    end_pos: tuple[float, float] | list[float] | None = None,
    start_scale: float | None = None,
    end_scale: float | None = None,
) -> dict[str, Any]:
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    cx = seq_w / 2.0
    cy = seq_h / 2.0
    min_cover_scale = max(seq_w / max(1, src_w), seq_h / max(1, src_h)) * 100.0

    if start_scale is None or end_scale is None:
        base_s = round(min_cover_scale * 1.03, 2)
        zoom_s = round(min_cover_scale * 1.11, 2)
        start_scale = base_s if zoom_in else zoom_s
        end_scale = zoom_s if zoom_in else base_s

    if start_pos is None or end_pos is None:
        if src_h > src_w:
            start_pos = (cx, cy + seq_h * 0.52)
            end_pos = (cx, cy + seq_h * 0.46)
        else:
            pan_x = seq_w * 0.025
            pan_y = seq_h * 0.03
            start_pos = (cx + (pan_x if zoom_in else -pan_x), cy + (pan_y if zoom_in else -pan_y))
            end_pos = (cx + (-pan_x if zoom_in else pan_x), cy + (-pan_y if zoom_in else pan_y))

    pos_keyframes = [
        {"time": 0, "value": {"Vec2": {"x": float(start_pos[0]), "y": float(start_pos[1])}}, "interp": "EaseOut", "in_influence": 1 / 3, "out_influence": 1 / 3},
        {"time": dur_ticks, "value": {"Vec2": {"x": float(end_pos[0]), "y": float(end_pos[1])}}, "interp": "EaseIn", "in_influence": 1 / 3, "out_influence": 1 / 3},
    ]
    scale_keyframes = [
        {"time": 0, "value": {"Float": float(start_scale)}, "interp": "EaseOut", "in_influence": 1 / 3, "out_influence": 1 / 3},
        {"time": dur_ticks, "value": {"Float": float(end_scale)}, "interp": "EaseIn", "in_influence": 1 / 3, "out_influence": 1 / 3},
    ]
    return {
        "effect": "motion",
        "enabled": True,
        "params": {
            "position": {"value": {"Vec2": {"x": float(start_pos[0]), "y": float(start_pos[1])}}, "keyframes": pos_keyframes},
            "scale": {"value": {"Float": float(start_scale)}, "keyframes": scale_keyframes},
            "scale_width": {"value": {"Float": 100.0}},
            "uniform_scale": {"value": {"Bool": True}},
            "rotation": {"value": {"Float": 0.0}},
            "anchor": {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}},
            "anti_flicker": {"value": {"Float": 0.0}},
        },
    }


def make_opacity_in_out(duration_s: float, fade_in_s: float = 0.25, fade_out_s: float = 0.30) -> dict[str, Any]:
    ticks_per_frame = TICKS_PER_SEC // 30
    dur_ticks = int(round(duration_s * 30)) * ticks_per_frame
    in_ticks = int(round(fade_in_s * 30)) * ticks_per_frame
    out_ticks = int(round(fade_out_s * 30)) * ticks_per_frame
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
        "params": {"opacity": {"value": {"Float": 100.0}, "keyframes": kfs}, "blend": {"value": {"Choice": 0}}},
    }


def verify_zero_project_scripts(proj_or_fcproj_path: Path) -> None:
    """Enforce Zero-Script Project Law across assemble_*.py, build_*.py, and render_*.py."""
    proj_dir = proj_or_fcproj_path.parent if proj_or_fcproj_path.is_file() or proj_or_fcproj_path.suffix == ".fcproj" else proj_or_fcproj_path
    rogue: list[Path] = []
    for pat in ("assemble_*.py", "build_*.py", "render_*.py"):
        rogue.extend(proj_dir.glob(pat))
    if rogue:
        names = ", ".join(sorted(p.name for p in rogue))
        raise RuntimeError(
            f"Zero-Script Project Law Violation in {proj_dir.name}: banned per-project script(s): {names}."
        )


check_zero_project_scripts_preflight = verify_zero_project_scripts


def check_bgm_non_reuse_preflight(proj_dir: Path, bgm_relpath: str, allow_used: bool = False) -> None:
    bgm_name = Path(bgm_relpath).name
    catalog_dir = get_studio_root() / "04_Project_Catalog"
    curr_resolved = proj_dir.resolve()

    conflicts = []
    for other_proj in catalog_dir.glob("*/*"):
        if not other_proj.is_dir() or other_proj.resolve() == curr_resolved:
            continue
        for ext in ("*.fcproj", "Storyboard.md", "timeline_spec.json"):
            for f in other_proj.glob(ext):
                if bgm_name in f.read_text(errors="ignore"):
                    conflicts.append((bgm_name, other_proj.name, f.name))

    if conflicts and not allow_used:
        lines = [f"  - '{c[0]}' already used in {c[1]} ({c[2]})" for c in conflicts]
        raise ValueError(
            f"Article I Music Non-Reuse Law Violation: '{bgm_name}' in {proj_dir.name} already used:\n" + "\n".join(lines)
        )


def verify_music_non_reuse(fcproj_path: Path, seq: dict[str, Any], items: dict[str, Any], strict: bool = True) -> None:
    bgm_names: set[str] = set()
    for idx, track in enumerate(seq.get("audio_tracks", [])):
        tname = (track.get("name") or "").lower()
        if idx == 1 or "music" in tname or "bgm" in tname:
            for it in track.get("items", []):
                name = it.get("name")
                if name and name.endswith(".mp3"):
                    bgm_names.add(name)
                mid = str(it.get("item", it.get("media_id")))
                file_p = items.get(mid, {}).get("kind", {}).get("Media", {}).get("media", {}).get("File", {}).get("path")
                if file_p and file_p.endswith(".mp3"):
                    bgm_names.add(Path(file_p).name)

    for bgm in bgm_names:
        try:
            check_bgm_non_reuse_preflight(fcproj_path.parent, bgm, allow_used=not strict)
        except ValueError:
            if strict:
                raise


def _parse_iso_utc(val: str | None) -> dt.datetime | None:
    if not val:
        return None
    try:
        parsed = dt.datetime.fromisoformat(str(val).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)
        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def check_landmark_synchronization_preflight(proj_dir: Path, cuts: list[dict[str, Any]], overlays: list[dict[str, Any]] | None = None) -> None:
    """Enforce calibration photo ban, monotonic GPX mileposts, and chronological UTC continuity."""
    manifest_path = proj_dir / "project_manifest.json"
    if not manifest_path.exists():
        return
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return

    items_by_name = {m.get("filename", "").lower(): m for m in (manifest.get("media_inventory") or [])}
    last_video_utc: dt.datetime | None = None
    last_ride_src = ""
    last_gpx_km = -1.0
    last_gpx_src = ""

    for c in cuts:
        src = str(c.get("source", ""))
        item = items_by_name.get(src.lower())
        if item and (item.get("exclude_from_timeline") or item.get("calibration_clock_only")):
            raise CalibrationMediaInTimelineError(
                f"Cut {c.get('cut_num')} references '{src}', flagged calibration_clock_only/exclude_from_timeline."
            )

        is_flashback_or_exempt = bool(
            c.get("allow_out_of_order")
            or "flashback" in str(c.get("desc", "")).lower()
            or src.lower().startswith(("ai_", "bookend_"))
        )

        ed = (item or {}).get("editorial") or {}
        if item and not is_flashback_or_exempt and ed.get("in_gpx_ride_window") and ed.get("distance_km") is not None:
            curr_km = float(ed["distance_km"])
            if last_gpx_km >= 0.0 and curr_km < last_gpx_km - 0.15:
                raise RouteContinuityError(
                    f"GPX Route Sequence Violation on Cut {c.get('cut_num')} ({src} at {curr_km:.2f} km < {last_gpx_src} at {last_gpx_km:.2f} km)."
                )
            if curr_km > last_gpx_km:
                last_gpx_km = curr_km
                last_gpx_src = src

        if item and item.get("media_type") == "video" and not is_flashback_or_exempt:
            curr_utc = _parse_iso_utc(item.get("creation_time_utc"))
            if curr_utc is not None and last_video_utc is not None and curr_utc < last_video_utc - dt.timedelta(seconds=2):
                raise RouteContinuityError(
                    f"Out-of-order chronological video cut {c.get('cut_num')} ({src}, {curr_utc.isoformat()} < {last_ride_src})."
                )
            if curr_utc is not None and (last_video_utc is None or curr_utc > last_video_utc):
                last_video_utc = curr_utc
                last_ride_src = src


def generate_srt_subtitles(proj_dir: Path, vo_cues: list[dict[str, Any]], live_subtitles: list[dict[str, Any]]) -> None:
    scripts_path = proj_dir / "narration_scripts.json"
    scripts = json.loads(scripts_path.read_text(encoding="utf-8")) if scripts_path.exists() else {"en": {}, "ua": {}, "ru": {}}

    for lang in ("en", "ua", "ru"):
        entries: list[tuple[float, float, str]] = []
        for lsub in live_subtitles:
            txt = (lsub.get("text") or {}).get(lang)
            if txt:
                entries.append((float(lsub["start_s"]), float(lsub["end_s"]), sanitize_caption_text(txt)))

        for cue in vo_cues:
            cue_key = cue["id"]
            start_s = float(cue["start_s"])
            text = (scripts.get(lang) or {}).get(cue_key, "") if isinstance(scripts.get(lang), dict) else ""
            paced_wav = proj_dir / f"voiceover_{lang}_{cue_key}_paced.wav"
            dur = get_audio_duration(paced_wav) if paced_wav.exists() else float(cue.get("max_dur_s", 10.0))
            if text:
                entries.append((start_s, start_s + dur, sanitize_caption_text(text)))

        entries.sort(key=lambda x: x[0])
        lines: list[str] = []
        for idx, (st, et, txt) in enumerate(entries, 1):
            lines.extend([str(idx), f"{fmt_srt_tc(st)} --> {fmt_srt_tc(et)}", txt, ""])
        (proj_dir / f"captions.{lang}.srt").write_text("\n".join(lines), encoding="utf-8")


def build_fcproj_document(
    proj_dir: Path,
    raw_dir: Path,
    overlays_dir: Path,
    bgm_track: Path,
    cuts_spec: list[dict[str, Any]],
    expanded_overlays: list[dict[str, Any]],
    boosted_dialogs: list[dict[str, Any]],
    sfx_cues: list[dict[str, Any]],
    vo_cues: list[dict[str, Any]],
    riding_gain_db: float = -8.0,
    edition: str = "en",
    total_dur: float | None = None,
    dimension_lookup: Callable[[Path, bool], tuple[int, int]] | None = None,
    duration_lookup: Callable[[Path], float] | None = None,
) -> dict[str, Any]:
    """
    Construct an in-memory FilmCraft schema v17 `.fcproj` JSON document with:
    - 4K UHD (3840x2160) 30fps sequence
    - Post-bookend zero-gap V1 continuity enforced automatically
    - Caption tracks C1 (`en`), C2 (`uk`), C3 (`ru`) created with `enabled=False` (clean 4K frames)
    - Unified 2.2s `constant_power` A2 outro fade
    """
    studio_root = get_studio_root()
    dim_fn = dimension_lookup or probe_media_dimensions
    dur_fn = duration_lookup or get_audio_duration

    if total_dur is None:
        total_dur = round(sum(float(c["dur"]) for c in cuts_spec), 2)

    next_id = 1
    items: dict[str, Any] = {}
    root_children: list[dict[str, int]] = []

    def register_media(path: Path, kind_type: str, width: int | None = None, height: int | None = None, dur_s: float = 180.0, rgba_png: bool = False) -> int:
        nonlocal next_id
        mid = next_id
        next_id += 1
        root_children.append({"Item": mid})
        file_sz = path.stat().st_size if path.exists() else 0
        fp = hashlib.md5(path.name.encode()).hexdigest()[:16]

        if kind_type == "Still":
            is_png = path.suffix.lower() == ".png"
            media_info: dict[str, Any] = {
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

    bd_aids: dict[int, int] = {}
    bd_by_cut: dict[int, dict[str, Any]] = {}
    for bd in boosted_dialogs:
        cnum = int(bd["cut_num"])
        bd_by_cut[cnum] = bd
        bd_aids[cnum] = register_media(proj_dir / bd["stem_file"], "AudioOnly", dur_s=float(bd["dur"]))

    vo_en_ids: dict[str, tuple[int, float]] = {}
    vo_ru_ids: dict[str, tuple[int, float]] = {}
    for cue in vo_cues:
        ckey = cue["id"]
        p_en = proj_dir / f"voiceover_en_{ckey}_paced.wav"
        p_ru = proj_dir / f"voiceover_ru_{ckey}_paced.wav"
        if p_en.exists():
            d_en = dur_fn(p_en)
            vo_en_ids[ckey] = (register_media(p_en, "AudioOnly", dur_s=d_en), d_en)
        if p_ru.exists():
            d_ru = dur_fn(p_ru)
            vo_ru_ids[ckey] = (register_media(p_ru, "AudioOnly", dur_s=d_ru), d_ru)

    sfx_ids: dict[str, tuple[int, float]] = {}
    for sc in sfx_cues:
        sname = sc["file"]
        if sname not in sfx_ids:
            p = studio_root / "03_Audio_Library" / "02_SFX" / sname
            d_sfx = dur_fn(p) if p.exists() else 0.6
            sfx_ids[sname] = (register_media(p, "AudioOnly", dur_s=d_sfx), d_sfx)

    overlay_ids: dict[str, int] = {}
    for ov in expanded_overlays:
        oname = ov["file"]
        if oname not in overlay_ids:
            p = overlays_dir / oname
            overlay_ids[oname] = register_media(p, "Still", width=3840, height=2160, dur_s=total_dur, rgba_png=True)

    cuts_media_ids: dict[int, int] = {}
    cuts_dims: dict[int, tuple[int, int]] = {}
    cuts_resolved_names: dict[int, str] = {}
    for cut in cuts_spec:
        cnum = int(cut["cut_num"])
        src = str(cut["source"])
        if edition == "ru" and src.endswith("_4K.mp4"):
            ru_src = src[:-7] + "_4K_RU.mp4"
            if (overlays_dir / ru_src).exists() or (raw_dir / ru_src).exists():
                src = ru_src
        is_still = bool(cut.get("is_still", False))
        dur = float(cut["dur"])
        src_in = float(cut.get("src_in", 0.0))
        p = overlays_dir / src if (overlays_dir / src).exists() else raw_dir / src
        if is_still and cut.get("framing") == "blur_pillarbox" and p.exists():
            dim_fn(p, is_still)
            p = ensure_blur_pillarbox_still(p, overlays_dir)
            src = p.name
        w, h = dim_fn(p, is_still)
        cuts_dims[cnum] = (w, h)
        cuts_resolved_names[cnum] = src
        if is_still:
            cuts_media_ids[cnum] = register_media(p, "Still", width=w, height=h, dur_s=dur)
        else:
            cuts_media_ids[cnum] = register_media(p, "Movie", width=w, height=h, dur_s=src_in + dur + 10.0)

    ticks_per_frame = TICKS_PER_SEC // 30
    v1_items: list[dict[str, Any]] = []
    a1_items: list[dict[str, Any]] = []
    v2_items: list[dict[str, Any]] = []
    v3_items: list[dict[str, Any]] = []
    v4_items: list[dict[str, Any]] = []
    a2_items: list[dict[str, Any]] = []
    a3_items: list[dict[str, Any]] = []
    a4_items: list[dict[str, Any]] = []
    a5_items: list[dict[str, Any]] = []

    curr_frame = 0
    for cut in cuts_spec:
        cnum = int(cut["cut_num"])
        src = cuts_resolved_names[cnum]
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

        if is_still and (cut.get("ken_burns") or cut.get("framing") == "blur_pillarbox"):
            kb = cut.get("ken_burns") or {
                "start_scale": 100.0,
                "end_scale": 103.2,
                "start_pos": [1920.0, 1080.0],
                "end_pos": [1920.0, 1080.0],
            }
            clip_effects = [
                make_motion_ken_burns(
                    dur,
                    w,
                    h,
                    3840,
                    2160,
                    start_pos=kb.get("start_pos"),
                    end_pos=kb.get("end_pos"),
                    start_scale=kb.get("start_scale"),
                    end_scale=kb.get("end_scale"),
                )
            ]
            clip_scale_to_frame = False
        else:
            clip_effects = [make_static_motion(w, h)]
            clip_scale_to_frame = True

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
            "effects": clip_effects,
            "markers": [],
            "gain_db": 0.0,
            "essential_sound": None,
            "frame_hold": None,
            "scale_to_frame": clip_scale_to_frame,
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

    bgm_file_dur = max(10.0, dur_fn(bgm_track)) if bgm_track.exists() else max(10.0, total_dur)
    rem_bgm = total_dur
    bgm_cursor_s = 0.0
    last_bgm_clip_id = None
    while rem_bgm > 0.05:
        seg_dur = min(bgm_file_dur, rem_bgm)
        bgm_clip_id = next_id
        next_id += 1
        last_bgm_clip_id = bgm_clip_id
        a2_items.append({
            "id": bgm_clip_id,
            "item": bgm_media_id,
            "name": bgm_track.name,
            "label": "Caribbean",
            "start": int(round(bgm_cursor_s * 30)) * ticks_per_frame,
            "duration": int(round(seg_dur * 30)) * ticks_per_frame,
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
        bgm_cursor_s += seg_dur
        rem_bgm -= seg_dur

    a2_transitions = []
    if last_bgm_clip_id is not None:
        tid_outro = next_id
        next_id += 1
        outro_fade_s = 2.2
        a2_transitions.append({
            "id": tid_outro,
            "effect": {"effect": "constant_power", "enabled": True, "params": {}},
            "start": int(round(max(0.0, total_dur - outro_fade_s) * 30)) * ticks_per_frame,
            "duration": int(round(outro_fade_s * 30)) * ticks_per_frame,
            "from": last_bgm_clip_id,
            "to": None,
            "align": "EndAtCut",
            "reverse": False,
        })

    for sc in sfx_cues:
        sname = sc["file"]
        st_s = resolve_sfx_start_s(sname, float(sc["start_s"]), align_peak=bool(sc.get("align_peak", False)))
        sgain = float(sc.get("gain_db", -10.0))
        sfx_mid, dur = sfx_ids[sname]
        a3_items.append({
            "id": next_id,
            "item": sfx_mid,
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
        if ckey in vo_en_ids:
            en_mid, dur_en = vo_en_ids[ckey]
            a4_items.append({
                "id": next_id,
                "item": en_mid,
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
                "gain_db": 0.0,
                "frame_hold": None,
                "scale_to_frame": False,
            })
            next_id += 1

        if ckey in vo_ru_ids:
            ru_mid, dur_ru = vo_ru_ids[ckey]
            a5_items.append({
                "id": next_id,
                "item": ru_mid,
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
                "gain_db": 0.0,
                "frame_hold": None,
                "scale_to_frame": False,
            })
            next_id += 1

    def parse_srt(srt_file: Path) -> list[dict[str, Any]]:
        caps = []
        nonlocal next_id
        if not srt_file.exists():
            return caps
        content = srt_file.read_text(encoding="utf-8")
        for b in content.strip().split("\n\n"):
            b_lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
            if len(b_lines) >= 3 and "-->" in b_lines[1]:
                t_parts = b_lines[1].split("-->")
                st = int(t_parts[0].split(":")[0]) * 3600 + int(t_parts[0].split(":")[1]) * 60 + float(t_parts[0].split(":")[2].replace(",", "."))
                et = int(t_parts[1].split(":")[0]) * 3600 + int(t_parts[1].split(":")[1]) * 60 + float(t_parts[1].split(":")[2].replace(",", "."))
                cid = next_id
                next_id += 1
                caps.append({
                    "id": cid,
                    "text": sanitize_caption_text(" ".join(b_lines[2:])),
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

    def make_track(tid: int, kind: str, name: str, track_items: list[dict[str, Any]], transitions: list[dict[str, Any]] | None = None, muted: bool = False) -> dict[str, Any]:
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

    seq_obj = {
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
            make_track(3, "Video", "V3 (Russian Speech Cards)" if edition == "ru" else "V3 (English Speech Cards)", v3_items),
            make_track(4, "Video", "V4 (Live Metric Telemetry HUD)" if edition == "ru" else "V4 (Live Imperial Telemetry HUD)", v4_items),
        ],
        "audio_tracks": [
            make_track(1, "Audio", "A1 - Camera Audio", a1_items),
            make_track(2, "Audio", f"A2 - Music ({bgm_track.stem})", a2_items, transitions=a2_transitions),
            make_track(3, "Audio", "A3 - Cinematic SFX", a3_items),
            make_track(4, "Audio", "Voice-Over (EN)", a4_items, muted=(edition == "ru")),
            make_track(5, "Audio", "Russian Voice-Over" if edition == "ru" else "Russian Voice-Over (Alt)", a5_items, muted=(edition != "ru")),
        ],
        "caption_tracks": [
            {"id": 1, "name": "English", "format": "Subtitle", "language": "en", "style": cap_style, "enabled": False, "locked": False, "sync_lock": True, "captions": c1_en, "vtt_blocks": []},
            {"id": 2, "name": "Українська", "format": "Subtitle", "language": "uk", "style": cap_style, "enabled": False, "locked": False, "sync_lock": True, "captions": c2_ua, "vtt_blocks": []},
            {"id": 3, "name": "Русский", "format": "Subtitle", "language": "ru", "style": cap_style, "enabled": False, "locked": False, "sync_lock": True, "captions": c3_ru, "vtt_blocks": []},
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

    # Post-bookend V1 zero-gap continuity enforcement
    verify_and_repair_v1_continuity(seq_obj)

    items[str(seq_id)] = {
        "id": seq_id,
        "name": proj_dir.name,
        "label": "Iris",
        "kind": {"Sequence": seq_obj},
        "metadata": {},
        "created": seq_id,
    }

    proj_name = f"{proj_dir.name}_RU" if edition == "ru" else proj_dir.name
    return {
        "format": "filmcraft.project",
        "schema_version": 17,
        "generator": "FilmCraft 0.18.0",
        "project": {
            "name": proj_name,
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
            "root": {"id": 0, "name": proj_name, "children": root_children},
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


def build_fcproj_from_spec(
    proj_dir: Path,
    raw_dir: Path,
    overlays_dir: Path,
    fcproj_path: Path,
    bgm_track: Path,
    total_dur: float,
    cuts_spec: list[dict[str, Any]],
    expanded_overlays: list[dict[str, Any]],
    boosted_dialogs: list[dict[str, Any]],
    sfx_cues: list[dict[str, Any]],
    vo_cues: list[dict[str, Any]],
    riding_gain_db: float = -8.0,
    edition: str = "en",
) -> Path:
    doc = build_fcproj_document(
        proj_dir=proj_dir,
        raw_dir=raw_dir,
        overlays_dir=overlays_dir,
        bgm_track=bgm_track,
        cuts_spec=cuts_spec,
        expanded_overlays=expanded_overlays,
        boosted_dialogs=boosted_dialogs,
        sfx_cues=sfx_cues,
        vo_cues=vo_cues,
        riding_gain_db=riding_gain_db,
        edition=edition,
        total_dur=total_dur,
    )
    fcproj_path.parent.mkdir(parents=True, exist_ok=True)
    fcproj_path.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    return fcproj_path


def apply_v017_essential_sound_via_cli(cli_bin: str, fcproj_path: Path, seq: dict[str, Any]) -> None:
    dialogue_ids, ambience_ids, music_ids, sfx_ids = [], [], [], []
    for idx, track in enumerate(seq.get("audio_tracks", [])):
        tname = (track.get("name") or "").lower()
        for it in track.get("items", []):
            cid = it.get("id")
            cname = (it.get("name") or "").lower()
            if idx >= 3 or "voiceover" in tname or "dialog" in cname or "voiceover" in cname:
                dialogue_ids.append(cid)
            elif idx == 1 or "music" in tname or "bgm" in tname:
                music_ids.append(cid)
            elif idx == 2 or "sfx" in tname:
                sfx_ids.append(cid)
            else:
                ambience_ids.append(cid)

    commands = []
    if dialogue_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": dialogue_ids, "type": "dialogue"}})
        commands.append({
            "id": "essentialSound.set",
            "params": {"clips": dialogue_ids, "values": {"repair.rumble.on": True, "clarity.eq.on": True, "clarity.eqPreset": "Balanced Voice"}},
        })
    if ambience_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": ambience_ids, "type": "ambience"}})
    if sfx_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": sfx_ids, "type": "sfx"}})
    if music_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": music_ids, "type": "music"}})
        commands.append({
            "id": "essentialSound.set",
            "params": {"clips": music_ids, "values": {"ducking.enabled": True, "ducking.reduceDb": -11.5, "ducking.fadeS": 0.35, "ducking.sensitivity": 6.0}},
        })
        if dialogue_ids:
            commands.append({"id": "essentialSound.generateDucking", "params": {"clips": music_ids}})

    if not commands:
        return

    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    jsonl_payload = "\n".join(json.dumps(c) for c in commands) + "\n"
    subprocess.run(
        [cli_bin, "--project", str(fcproj_path), "--save", "run", "-"],
        input=jsonl_payload,
        capture_output=True,
        text=True,
        check=False,
        cwd=str(cache_dir),
    )


def polish_and_render_project(
    fcproj_path: Path,
    output_mp4: Path | None = None,
    burn_captions: bool = False,
    allow_used_music: bool = False,
    run_essential_sound: bool = True,
) -> Path:
    """Apply Studio v3 quality standards (4K UHD, zero-gap V1, Ken Burns, Dip-to-Black, disabled burn captions)."""
    cli_bin = find_binary("filmcraft-cli")
    if run_essential_sound or output_mp4:
        env_status = verify_filmcraft_environment(auto_sync_cli=True, check_remote=False)
        cli_bin = env_status.get("cli_binary") or cli_bin or "filmcraft-cli"

    data = json.loads(fcproj_path.read_text(encoding="utf-8"))
    proj = data["project"]
    items = proj["items"]
    seq_id = str(data["view"].get("active_sequence") or "")
    if seq_id not in items or "Sequence" not in items[seq_id].get("kind", {}):
        for k, v in items.items():
            if "Sequence" in v.get("kind", {}):
                seq_id = k
                break
    seq = items[seq_id]["kind"]["Sequence"]
    next_id = int(proj.get("next_id", data.get("next_id", 300)))

    if len(seq.get("video_tracks", [])) > 1:
        v1_names = {it.get("name") for it in seq["video_tracks"][0].get("items", [])}
        v2_items = seq["video_tracks"][1].get("items", [])
        if any(it.get("name") in v1_names for it in v2_items):
            seq["video_tracks"][1]["items"] = []
            seq["video_tracks"][1]["transitions"] = []

    verify_zero_project_scripts(fcproj_path)
    verify_music_non_reuse(fcproj_path, seq, items, strict=not allow_used_music)

    video_tracks = seq.get("video_tracks", [])
    if video_tracks and video_tracks[0].get("items"):
        v1 = video_tracks[0]
        verify_and_repair_v1_continuity(seq)
        all_v1_items = v1.get("items", [])
        max_src_w = max(
            (items.get(str(it.get("item", it.get("media_id"))), {}).get("kind", {}).get("Media", {}).get("info", {}).get("video") or {}).get("width", 1920)
            for it in all_v1_items
        )
        seq_w, seq_h = (3840, 2160) if max_src_w > 1920 else (1920, 1080)
        seq.setdefault("settings", {})["width"] = seq_w
        seq.setdefault("settings", {})["height"] = seq_h
        seq.setdefault("settings", {})["preset"] = f"{seq_w}x{seq_h} 30"

        still_zoom_toggle = True
        for it in all_v1_items:
            name = it.get("name", "")
            dur_s = it.get("duration", 0) / TICKS_PER_SEC
            media_id = str(it.get("item", it.get("media_id")))
            vinfo = items.get(media_id, {}).get("kind", {}).get("Media", {}).get("info", {}).get("video") or {}
            src_w = vinfo.get("width", 1920)
            src_h = vinfo.get("height", 1080)
            is_static_graphic = "-4k." in name.lower() or "graphic" in name.lower() or "card" in name.lower() or (src_w == seq_w and src_h == seq_h and "strava" in name.lower())
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")) and not is_static_graphic:
                it["scale_to_frame"] = False
                effects = it.get("effects", [])
                has_custom_kb = any(e.get("effect") == "motion" and "keyframes" in e.get("params", {}).get("scale", {}) for e in effects)
                if not has_custom_kb:
                    effects = [e for e in effects if e.get("effect") != "motion"]
                    effects.insert(0, make_motion_ken_burns(dur_s, src_w, src_h, seq_w, seq_h, zoom_in=still_zoom_toggle))
                    still_zoom_toggle = not still_zoom_toggle
                    it["effects"] = effects
            elif is_static_graphic:
                it["scale_to_frame"] = True
                effects = [e for e in it.get("effects", []) if e.get("effect") != "motion"]
                effects.insert(0, make_static_motion(src_w, src_h, seq_w, seq_h))
                it["effects"] = effects
            else:
                it["scale_to_frame"] = True
                for eff in it.get("effects", []):
                    if eff.get("effect") == "motion":
                        eff["params"]["position"] = {"value": {"Vec2": {"x": seq_w / 2.0, "y": seq_h / 2.0}}}
                        eff["params"]["anchor"] = {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}}
                        eff["params"]["scale"] = {"value": {"Float": 100.0}}

        last_clip = all_v1_items[-1]
        last_end_ticks = last_clip["start"] + last_clip["duration"]
        fade_ticks = int(1.5 * TICKS_PER_SEC)
        v1["transitions"] = [{
            "id": next_id,
            "effect": {"effect": "dip_to_black", "enabled": True, "params": {}},
            "start": max(last_clip["start"], last_end_ticks - fade_ticks),
            "duration": fade_ticks,
            "from": last_clip["id"],
            "to": None,
            "align": "EndAtCut",
            "reverse": False,
        }]
        next_id += 1

        audio_tracks = seq.get("audio_tracks", [])
        if len(audio_tracks) > 1 and audio_tracks[1].get("items"):
            a2 = audio_tracks[1]
            last_music_clip = a2["items"][-1]
            music_end_ticks = last_music_clip["start"] + last_music_clip["duration"]
            audio_fade_ticks = int(2.2 * TICKS_PER_SEC)
            a2["transitions"] = [{
                "id": next_id,
                "effect": {"effect": "constant_power", "enabled": True, "params": {}},
                "start": max(last_music_clip["start"], music_end_ticks - audio_fade_ticks),
                "duration": audio_fade_ticks,
                "from": last_music_clip["id"],
                "to": None,
                "align": "EndAtCut",
                "reverse": False,
            }]
            next_id += 1

    if seq.get("caption_tracks"):
        for ct in seq["caption_tracks"]:
            ct["enabled"] = False
            for cap in ct.get("captions", []):
                cap["text"] = sanitize_caption_text(cap.get("text", ""))
                cap.setdefault("speaker", None)
                cap.setdefault("cue_id", None)
                cap.setdefault("settings", "")

    proj["next_id"] = next_id
    fcproj_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    if run_essential_sound and cli_bin:
        apply_v017_essential_sound_via_cli(cli_bin, fcproj_path, seq)

    if output_mp4 and cli_bin:
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        cache_dir = get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        burn_json = "true" if burn_captions else "false"
        subprocess.run(
            [
                cli_bin,
                "--project", str(fcproj_path),
                "export", str(output_mp4),
                "--preset", PRESET_4K_MATCH_SOURCE,
                "--settings", f'{{"burnCaptions": {burn_json}}}',
            ],
            capture_output=True,
            text=True,
            check=True,
            cwd=str(cache_dir),
        )
    return fcproj_path


# ---------------------------------------------------------------------------
# Mandatory Refinement #2: 4K Edition Export Plan (Zero `-f concat` Splicing)
# ---------------------------------------------------------------------------
_AUDIO_LANG_META: dict[str, tuple[str, str, str]] = {
    "en": ("eng", "English", ""),
    "ua": ("ukr", "Українська", "_UA"),
    "ru": ("rus", "Русский", "_RU"),
}


def build_edition_export_plan(
    proj_dir: Path,
    exports_dir: Path,
    edition_visual_mode: str = "universal_4k_remux",
    available_audio_langs: tuple[str, ...] = ("en", "ua", "ru"),
) -> dict[str, Any]:
    """
    Build a deterministic 4K UHD export & remux plan with ZERO mid-stream `-f concat` splicing:
    - `universal_4k_remux` (default): Renders Master 4K (`3840x2160`) once via `filmcraft-cli`,
      then losslessly remuxes `en` (`<proj>.mp4`), `ua` (`<proj>_UA.mp4`), and `ru` (`<proj>_RU.mp4`)
      via `ffmpeg -map 0:v:0 -map 1:a:0 -c:v copy -c:a copy` in 0.2s.
    - `localized_4k_render` (opt-in): Renders both Master (`en`) and Russian (`ru`) `.fcproj` timelines
      at full 4K UHD (`3840x2160`, never `1080p`), then losslessly remuxes audio + soft subtitles.
    """
    mode = (edition_visual_mode or "universal_4k_remux").strip().lower()
    if mode not in ("universal_4k_remux", "localized_4k_render"):
        raise ValueError(f"Unsupported edition_visual_mode: {edition_visual_mode!r}")

    ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
    proj_name = proj_dir.name
    master_mp4 = exports_dir / f"{proj_name}.mp4"
    ru_render_mp4 = exports_dir / f"{proj_name}_RU.mp4"

    filmcraft_renders: list[dict[str, Any]] = [
        {"edition": "en", "resolution": (3840, 2160), "preset": PRESET_4K_MATCH_SOURCE}
    ]
    if mode == "localized_4k_render":
        filmcraft_renders.append(
            {"edition": "ru", "resolution": (3840, 2160), "preset": PRESET_4K_MATCH_SOURCE}
        )

    srt_en = proj_dir / "captions.en.srt"
    srt_ua = proj_dir / "captions.ua.srt"
    srt_ru = proj_dir / "captions.ru.srt"
    has_srts = srt_en.exists() and srt_ua.exists() and srt_ru.exists()

    ffmpeg_remuxes: list[dict[str, Any]] = []
    for lang in available_audio_langs:
        lang_clean = lang.lower()
        iso3, title, suffix = _AUDIO_LANG_META.get(lang_clean, ("eng", lang_clean.upper(), f"_{lang_clean.upper()}"))
        video_src = ru_render_mp4 if (mode == "localized_4k_render" and lang_clean == "ru") else master_mp4
        final_out = exports_dir / f"{proj_name}{suffix}.mp4"
        temp_out = final_out.with_suffix(f".tmp_{lang_clean}.mp4") if final_out == video_src else final_out
        audio_in = proj_dir / f"full_audio_{lang_clean}.m4a"

        cmd = [ffmpeg_bin, "-y", "-i", str(video_src), "-i", str(audio_in)]
        if has_srts:
            cmd.extend([
                "-i", str(srt_en), "-i", str(srt_ua), "-i", str(srt_ru),
                "-map", "0:v:0", "-map", "1:a:0", "-map", "2:s:0", "-map", "3:s:0", "-map", "4:s:0",
                "-c:v", "copy", "-c:a", "copy", "-c:s", "mov_text",
                "-metadata:s:a:0", f"language={iso3}", "-metadata:s:a:0", f"title={title}",
                "-metadata:s:s:0", "language=eng", "-metadata:s:s:0", "title=English",
                "-metadata:s:s:1", "language=ukr", "-metadata:s:s:1", "title=Українська",
                "-metadata:s:s:2", "language=rus", "-metadata:s:s:2", "title=Русский",
                str(temp_out),
            ])
        else:
            cmd.extend([
                "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "copy",
                "-metadata:s:a:0", f"language={iso3}", "-metadata:s:a:0", f"title={title}",
                str(temp_out),
            ])

        ffmpeg_remuxes.append({
            "edition": lang_clean,
            "video_source": video_src,
            "audio_source": audio_in,
            "temp_output": temp_out,
            "final_output": final_out,
            "cmd": cmd,
        })

    return {
        "mode": mode,
        "filmcraft_renders": filmcraft_renders,
        "ffmpeg_remuxes": ffmpeg_remuxes,
    }


def execute_edition_exports(
    proj_dir: Path,
    exports_dir: Path,
    edition_visual_mode: str = "universal_4k_remux",
    mux_audio_only: bool = False,
    render_en_only: bool = False,
    render_ru_only: bool = False,
) -> list[Path]:
    """Execute FilmCraft 4K renders (with cwd=get_cache_dir()) and lossless 0.2s FFmpeg edition remuxes."""
    avail_langs = tuple(
        lang for lang in ("en", "ua", "ru") if (proj_dir / f"full_audio_{lang}.m4a").exists()
    ) or ("en",)
    plan = build_edition_export_plan(
        proj_dir=proj_dir,
        exports_dir=exports_dir,
        edition_visual_mode=edition_visual_mode,
        available_audio_langs=avail_langs,
    )
    exports_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)

    if not mux_audio_only:
        env_status = verify_filmcraft_environment(auto_sync_cli=True, check_remote=False)
        cli_bin = env_status.get("cli_binary") or find_binary("filmcraft-cli") or "filmcraft-cli"
        for render_step in plan["filmcraft_renders"]:
            ed = render_step["edition"]
            if render_en_only and ed != "en":
                continue
            if render_ru_only and ed != "ru":
                continue
            fcproj = proj_dir / (f"{proj_dir.name}_RU.fcproj" if ed == "ru" else f"{proj_dir.name}.fcproj")
            out_mp4 = exports_dir / (f"{proj_dir.name}_RU.mp4" if ed == "ru" else f"{proj_dir.name}.mp4")
            subprocess.run(
                [
                    cli_bin,
                    "--project", str(fcproj),
                    "export", str(out_mp4),
                    "--preset", render_step["preset"],
                    "--settings", '{"burnCaptions": false}',
                ],
                check=True,
                cwd=str(cache_dir),
            )

    produced: list[Path] = []
    for remux in plan["ffmpeg_remuxes"]:
        if render_en_only and remux["edition"] != "en":
            continue
        if render_ru_only and remux["edition"] != "ru":
            continue
        if not remux["video_source"].exists() or not remux["audio_source"].exists():
            continue
        subprocess.run(remux["cmd"], check=True, capture_output=True)
        if remux["temp_output"] != remux["final_output"]:
            remux["temp_output"].replace(remux["final_output"])
        produced.append(remux["final_output"])
    return produced


def build_project_timeline(
    proj_dir: Path,
    render_export: bool = False,
    render_ru_only: bool = False,
    render_en_only: bool = False,
    mux_audio_only: bool = False,
    allow_used_music: bool = False,
    open_gui: bool = True,
) -> dict[str, Any]:
    """Full declarative pipeline entrypoint for building `.fcproj` and exporting 4K editions."""
    proj_dir = Path(proj_dir).expanduser().resolve()
    spec_path = proj_dir / "timeline_spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"Missing declarative timeline_spec.json in {proj_dir}")

    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    year_str = proj_dir.parent.name
    raw_dir = get_hot_media_dir() / year_str / proj_dir.name
    overlays_dir = proj_dir / "overlays"
    exports_dir = get_exports_dir() / year_str
    fcproj_path = proj_dir / f"{proj_dir.name}.fcproj"
    fcproj_ru_path = proj_dir / f"{proj_dir.name}_RU.fcproj"

    verify_zero_project_scripts(proj_dir)
    bgm_rel = spec["bgm_track"]
    check_bgm_non_reuse_preflight(proj_dir, bgm_rel, allow_used=allow_used_music)
    bgm_track = get_studio_root() / bgm_rel

    bookends_cfg = spec.get("bookends", {})
    if not mux_audio_only and bookends_cfg.get("enabled", False):
        overlays_dir.mkdir(parents=True, exist_ok=True)
        bookends_hash = hashlib.sha256(json.dumps(bookends_cfg, sort_keys=True).encode("utf-8")).hexdigest()[:16]
        bookends_hash_file = overlays_dir / ".bookends_hash"
        prev_hash = bookends_hash_file.read_text(encoding="utf-8").strip() if bookends_hash_file.exists() else ""
        intro_mp4 = overlays_dir / "bookend_intro_4K.mp4"
        outro_mp4 = overlays_dir / "bookend_outro_4K.mp4"
        intro_ru_mp4 = overlays_dir / "bookend_intro_4K_RU.mp4"
        outro_ru_mp4 = overlays_dir / "bookend_outro_4K_RU.mp4"
        all_valid = (
            prev_hash == bookends_hash
            and intro_mp4.exists() and outro_mp4.exists()
            and intro_ru_mp4.exists() and outro_ru_mp4.exists()
            and intro_mp4.stat().st_size > 100_000 and outro_mp4.stat().st_size > 100_000
        )
        if not all_valid:
            first_c = raw_dir / bookends_cfg["first_clip"] if bookends_cfg.get("first_clip") else None
            last_c = raw_dir / bookends_cfg["last_clip"] if bookends_cfg.get("last_clip") else None
            generate_project_bookends(proj_dir, overlays_dir, first_clip=first_c, last_clip=last_c)
            bookends_hash_file.write_text(bookends_hash, encoding="utf-8")

    cuts_spec = attach_bookend_cuts_if_needed(spec["cuts"], bookends_cfg, overlays_dir=overlays_dir, raw_dir=raw_dir)
    overlays_spec = spec.get("overlays", [])
    check_landmark_synchronization_preflight(proj_dir, cuts_spec, overlays_spec)

    total_dur = round(sum(float(c["dur"]) for c in cuts_spec), 2)
    boosted_dialogs = spec.get("boosted_dialogs", [])
    sfx_cues = spec.get("sfx_cues", [])
    vo_cues = spec.get("vo_cues", [])
    live_subtitles = spec.get("live_subtitles", [])

    expanded_overlays_map = render_declarative_overlays(
        overlays_spec,
        overlays_dir,
        raw_dir=raw_dir,
        skip_render=mux_audio_only,
        cuts_spec=cuts_spec,
        hud_mode=spec.get("hud_mode", "auto"),
    )
    expanded_overlays_en = expanded_overlays_map["en"]
    expanded_overlays_ru = expanded_overlays_map["ru"]

    prepare_paced_voiceovers(proj_dir, vo_cues)
    generate_srt_subtitles(proj_dir, vo_cues, live_subtitles)
    prepare_boosted_dialog_stems(proj_dir, raw_dir, boosted_dialogs)
    riding_gain_db = build_broadcast_audio_mixes(
        proj_dir,
        raw_dir,
        overlays_dir,
        bgm_track,
        total_dur,
        cuts_spec,
        boosted_dialogs,
        sfx_cues,
        vo_cues,
        bgm_tracks_spec=spec.get("bgm_tracks"),
    )

    build_fcproj_from_spec(
        proj_dir, raw_dir, overlays_dir, fcproj_path, bgm_track, total_dur,
        cuts_spec, expanded_overlays_en, boosted_dialogs, sfx_cues, vo_cues,
        riding_gain_db=riding_gain_db, edition="en",
    )
    build_fcproj_from_spec(
        proj_dir, raw_dir, overlays_dir, fcproj_ru_path, bgm_track, total_dur,
        cuts_spec, expanded_overlays_ru, boosted_dialogs, sfx_cues, vo_cues,
        riding_gain_db=riding_gain_db, edition="ru",
    )
    polish_and_render_project(fcproj_path, allow_used_music=allow_used_music)
    polish_and_render_project(fcproj_ru_path, allow_used_music=allow_used_music)

    if open_gui:
        cache_dir = get_cache_dir()
        cache_dir.mkdir(parents=True, exist_ok=True)
        subprocess.run(["open", "-a", "FilmCraft", "--args", "--control", "9876", str(fcproj_path)], cwd=str(cache_dir), check=False)

    edition_visual_mode = spec.get("edition_visual_mode", "universal_4k_remux")
    if render_ru_only and edition_visual_mode == "universal_4k_remux":
        edition_visual_mode = "localized_4k_render"

    exported: list[Path] = []
    if mux_audio_only or render_export or render_en_only or render_ru_only:
        exported = execute_edition_exports(
            proj_dir=proj_dir,
            exports_dir=exports_dir,
            edition_visual_mode=edition_visual_mode,
            mux_audio_only=mux_audio_only,
            render_en_only=render_en_only,
            render_ru_only=render_ru_only,
        )

    return {
        "fcproj_en": fcproj_path,
        "fcproj_ru": fcproj_ru_path,
        "exported_mp4s": exported,
        "edition_visual_mode": edition_visual_mode,
        "total_dur_s": total_dur,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Universal Declarative 4K Timeline Builder (AGVS v3)")
    p.add_argument("--project-dir", required=True, help="Path to project directory in 04_Project_Catalog/YEAR/<project>")
    p.add_argument("--render-export", action="store_true", help="Render 4K MP4 via filmcraft-cli and remux editions")
    p.add_argument("--render-ru-only", action="store_true", help="Render 4K Russian Edition (_RU.mp4) via filmcraft-cli")
    p.add_argument("--render-en-only", action="store_true", help="Render 4K Master EN Video via filmcraft-cli")
    p.add_argument("--mux-audio-only", action="store_true", help="Losslessly remux updated audio/subtitles into existing 4K MP4")
    p.add_argument("--allow-used-music", action="store_true", help="Override Music Non-Reuse Law check")
    p.add_argument("--no-open-gui", action="store_true", help="Skip launching FilmCraft.app GUI")
    args = p.parse_args(argv)

    build_project_timeline(
        proj_dir=Path(args.project_dir),
        render_export=args.render_export,
        render_ru_only=args.render_ru_only,
        render_en_only=args.render_en_only,
        mux_audio_only=args.mux_audio_only,
        allow_used_music=args.allow_used_music,
        open_gui=not args.no_open_gui,
    )
    return 0
