#!/usr/bin/env python3
"""
assemble_engine.py
Universal Timeline Assembly & Polishing Engine for Google Antigravity & FilmCraft (v0.17.0+).

Guarantees Studio v2 broadcast quality standards automatically on EVERY movie:
1. Enforces FilmCraft >= v0.17.0 version gate & auto-syncs `filmcraft-cli` with `FilmCraft.app`.
2. Auto-detects 4K UHD (3840x2160) when sources exceed 1080p, applying smooth Ken Burns scale/pan
   keyframing (`EaseIn`/`EaseOut`) on all still photos and `scale_to_frame=True` on video clips.
3. Configures native FilmCraft v0.17.0+ `Essential Sound` metadata & processing (`essentialSound.*`):
   - Tags `A1` speech & `A4` voiceover clips as `Dialogue` (with rumble/noise repair & `Balanced Voice` clarity).
   - Tags `A1` riding clips as `Ambience`, `A2` tracks as `Music`, and `A3` clips as `SFX`.
   - Executes `essentialSound.generateDucking` via `filmcraft-cli` so music (`A2`) automatically ducks `-3.5 dB`
     under dialogue/voiceover (`A1`/`A4`) and swells back up during pure riding segments!
4. Applies a smooth native 1.5s `dip_to_black` transition on the closing clip.
5. Defaults to clean 4K frames (`--burn-captions false` by default; captions served via `.srt` + voiceover).
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_filmcraft_env import verify_filmcraft_environment

TICKS_PER_SEC = 254016000000

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
EXPORTS_ROOT = Path(os.environ.get("EXPORTS_ROOT", "~/Movies/Exports")).expanduser()


def sanitize_caption_text(text: str) -> str:
    """Strips emoji glyphs that fail to render in Inter font, preserving standard punctuation and accents."""
    cleaned = re.sub(r"[\U00010000-\U0010ffff]", "", text)
    cleaned = re.sub(r"[\u2600-\u27bf]", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def verify_and_repair_v1_continuity(seq: dict) -> int:
    """
    Ensures V1 timeline items are strictly contiguous with zero accidental black gaps or overlaps.
    If a gap > 0 ticks is detected between clip i and clip i+1, snaps subsequent clips to close
    the black void.
    Returns the count of repaired gaps.
    """
    video_tracks = seq.get("video_tracks", [])
    if not video_tracks or not video_tracks[0].get("items"):
        return 0
    v1_items = video_tracks[0]["items"]
    v1_items.sort(key=lambda x: x.get("start", 0))

    current_ticks = 0
    repaired_gaps = 0
    for idx, item in enumerate(v1_items):
        start = item.get("start", 0)
        dur = item.get("duration", 0)
        gap = start - current_ticks
        if abs(gap) > 0:
            gap_s = gap / TICKS_PER_SEC
            if gap > 0:
                print(f"[Continuity Check] Repaired black gap of {gap_s:.3f}s before clip '{item.get('name')}' (snapped from {start/TICKS_PER_SEC:.2f}s to {current_ticks/TICKS_PER_SEC:.2f}s)")
            else:
                print(f"[Continuity Check] Repaired overlap of {-gap_s:.3f}s before clip '{item.get('name')}' (snapped from {start/TICKS_PER_SEC:.2f}s to {current_ticks/TICKS_PER_SEC:.2f}s)")
            item["start"] = current_ticks
            repaired_gaps += 1
        current_ticks += dur

    if repaired_gaps:
        print(f"V1 Visual Continuity: Repaired {repaired_gaps} gap(s)/overlap(s). Total V1 duration: {current_ticks / TICKS_PER_SEC:.2f}s")
    else:
        print(f"V1 Visual Continuity: Passed (100% contiguous, {len(v1_items)} clips, total duration: {current_ticks / TICKS_PER_SEC:.2f}s)")
    return repaired_gaps


def make_volume_effect(fade_in_s=None, fade_out_s=None, duration_s=0.0):
    """Creates a volume effect dictionary with keyframed fades if requested."""
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    keyframes = []
    if fade_in_s:
        in_ticks = int(fade_in_s * TICKS_PER_SEC)
        keyframes.append({
            "time": 0,
            "value": {"Float": -60.0},
            "interp": "EaseIn",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        })
        keyframes.append({
            "time": in_ticks,
            "value": {"Float": 0.0},
            "interp": "EaseOut",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        })
    if fade_out_s:
        out_start_ticks = max(0, dur_ticks - int(fade_out_s * TICKS_PER_SEC))
        keyframes.append({
            "time": out_start_ticks,
            "value": {"Float": 0.0},
            "interp": "EaseIn",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        })
        keyframes.append({
            "time": dur_ticks,
            "value": {"Float": -60.0},
            "interp": "EaseOut",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        })

    param_val = {"value": {"Float": 0.0}}
    if keyframes:
        param_val["keyframes"] = keyframes

    return [
        {"effect": "volume", "enabled": True, "params": {"bypass": {"value": {"Bool": False}}, "level": param_val}},
        {"effect": "channel_volume", "enabled": True, "params": {"bypass": {"value": {"Bool": False}}, "left": {"value": {"Float": 0.0}}, "right": {"value": {"Float": 0.0}}}},
        {"effect": "panner", "enabled": True, "params": {"balance": {"value": {"Float": 0.0}}}},
    ]


def make_static_motion(src_w, src_h, seq_w=3840, seq_h=2160):
    return {
        "effect": "motion",
        "enabled": True,
        "params": {
            "position": {"value": {"Vec2": {"x": seq_w / 2.0, "y": seq_h / 2.0}}},
            "scale": {"value": {"Float": 100.0}},
            "scale_width": {"value": {"Float": 100.0}},
            "uniform_scale": {"value": {"Bool": True}},
            "rotation": {"value": {"Float": 0.0}},
            "anchor": {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}},
            "anti_flicker": {"value": {"Float": 0.0}},
        },
    }

def make_motion_ken_burns(duration_s, src_w, src_h, seq_w=3840, seq_h=2160, zoom_in=True, start_pos=None, end_pos=None, start_scale=None, end_scale=None):
    """Creates a full-bleed 2-axis motion effect with true-center anchor and Ken Burns scale + pan keyframing."""
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    cx = seq_w / 2.0
    cy = seq_h / 2.0

    # Minimum scale (%) required to cover the entire sequence frame with zero black bars (when scale_to_frame=False)
    min_cover_scale = max(seq_w / max(1, src_w), seq_h / max(1, src_h)) * 100.0

    if start_scale is None or end_scale is None:
        base_s = max(108.0, round(min_cover_scale + 4.0, 1))
        zoom_s = round(base_s + 12.0, 1)
        start_scale = base_s if zoom_in else zoom_s
        end_scale = zoom_s if zoom_in else base_s

    if start_pos is None or end_pos is None:
        if src_h > src_w:
            # Portrait photo: bring faces into view with generous headroom
            start_pos = (cx, cy + seq_h * 0.52)
            end_pos = (cx, cy + seq_h * 0.46)
        else:
            # Landscape photo: gentle diagonal pan + zoom across the frame
            pan_x = seq_w * 0.025
            pan_y = seq_h * 0.03
            start_pos = (cx + (pan_x if zoom_in else -pan_x), cy + (pan_y if zoom_in else -pan_y))
            end_pos = (cx + (-pan_x if zoom_in else pan_x), cy + (-pan_y if zoom_in else pan_y))

    pos_keyframes = [
        {
            "time": 0,
            "value": {"Vec2": {"x": float(start_pos[0]), "y": float(start_pos[1])}},
            "interp": "EaseOut",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        },
        {
            "time": dur_ticks,
            "value": {"Vec2": {"x": float(end_pos[0]), "y": float(end_pos[1])}},
            "interp": "EaseIn",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        },
    ]

    scale_keyframes = [
        {
            "time": 0,
            "value": {"Float": float(start_scale)},
            "interp": "EaseOut",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        },
        {
            "time": dur_ticks,
            "value": {"Float": float(end_scale)},
            "interp": "EaseIn",
            "in_influence": 0.3333333333333333,
            "out_influence": 0.3333333333333333,
        },
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


def master_outro_fade_filter(total_dur_s: float, fade_dur_s: float = 2.2) -> str:
    """Returns the mandatory Synchronized Outro Audio Fade ffmpeg filter string (Half-Sine S-curve to -inf dB)."""
    st = max(0.0, total_dur_s - fade_dur_s)
    return f"afade=t=out:st={st:.2f}:d={fade_dur_s:.2f}:curve=hsin"


def measure_mean_volume_db(audio_path: Path) -> float:
    """
    Measures midrange-weighted RMS mean_volume in dB via ffmpeg behind a 180 Hz high-pass filter
    (`-af "highpass=f=180,volumedetect"`), ignoring sub-bass (60-120 Hz) inflation so chillhop/ambient
    tracks are calibrated to human perceptual loudness rather than sub-bass energy.
    """
    ffmpeg_bin = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
    out = subprocess.check_output(
        [ffmpeg_bin, "-i", str(audio_path), "-af", "highpass=f=180,volumedetect", "-f", "null", "-"],
        stderr=subprocess.STDOUT,
    ).decode("utf-8", errors="replace")
    for line in out.splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except ValueError:
                pass
    return -16.0


def is_mellow_bgm_track(bgm_path: Path) -> bool:
    """
    Detects if a BGM track is mellow/chillhop/ambient based on keywords in filename/path
    ('chillhop', 'chill', 'ambient', 'warm', 'scenic', 'lofi') or BPM < 95.
    """
    s = str(bgm_path).lower()
    keywords = ["chillhop", "chill", "ambient", "warm", "scenic", "lofi"]
    if any(kw in s for kw in keywords):
        return True
    m = re.search(r"(\d{2,3})\s*bpm", s)
    if m:
        try:
            bpm = int(m.group(1))
            if bpm < 95:
                return True
        except ValueError:
            pass
    return False


def calculate_bgm_gains(
    bgm_path: Path,
    target_riding_db: float = -15.5,
    target_ducked_db: float = -21.5,
) -> dict:
    """
    Calculates midrange-weighted BGM gains and presence EQ filter.
    Baseline targets:
      - Riding / Open Visual Swells (`target_riding_db`): -15.5 dB (midrange-weighted RMS)
      - Ducked Under VO / Live Speech (`target_ducked_db`): -21.5 dB (smooth 6.0 dB duck)
    Mellow / Chillhop Boost:
      - If filename/path contains mellow keywords or BPM < 95:
        - Additional +1.5 dB offset applied to both riding_gain and ducked_gain.
        - Gentle presence EQ filter: equalizer=f=1800:t=q:w=1.0:g=2.0
    """
    raw_mean_db = measure_mean_volume_db(bgm_path)
    is_mellow = is_mellow_bgm_track(bgm_path)
    mellow_boost_db = 1.5 if is_mellow else 0.0

    effective_target_riding_db = target_riding_db + mellow_boost_db
    effective_target_ducked_db = target_ducked_db + mellow_boost_db

    ducked_gain_db = round(effective_target_ducked_db - raw_mean_db, 1)
    riding_gain_db = round(effective_target_riding_db - raw_mean_db, 1)
    swell_boost_db = round(effective_target_riding_db - effective_target_ducked_db, 1)

    eq_filter = "equalizer=f=1800:t=q:w=1.0:g=2.0" if is_mellow else ""

    return {
        "raw_mean_db": raw_mean_db,
        "is_mellow": is_mellow,
        "mellow_boost_db": mellow_boost_db,
        "target_riding_db": effective_target_riding_db,
        "target_ducked_db": effective_target_ducked_db,
        "base_target_riding_db": target_riding_db,
        "base_target_ducked_db": target_ducked_db,
        "riding_gain_db": riding_gain_db,
        "ducked_gain_db": ducked_gain_db,
        "swell_boost_db": swell_boost_db,
        "eq_filter": eq_filter,
    }


def compute_bgm_ducked_gain_db(bgm_path: Path, target_ducked_mean_db: float = -21.5) -> float:
    """
    Computes the exact ducked fader gain (dB) required for a music track under VO/speech.
    Defaults to -21.5 dB (with automatic +1.5 dB boost if mellow).
    """
    res = calculate_bgm_gains(bgm_path, target_ducked_db=target_ducked_mean_db)
    return res["ducked_gain_db"]


def filter_vo_cues_for_same_language_dialog(vo_cues: list, dialog_windows_by_lang: dict, lang: str) -> list:
    """
    Same-Language Live Dialogue Honor Law:
    Removes any voice-over cue in `lang` that overlaps a live on-camera dialogue window in the SAME language (`lang`),
    so synthetic narration never covers live speech in the same language (e.g., EN VO honors live EN speech;
    RU VO honors live RU speech).
    """
    same_lang_windows = dialog_windows_by_lang.get(lang, [])
    if not same_lang_windows:
        return vo_cues
    filtered = []
    for cue in vo_cues:
        cue_key, st, ed = cue[0], cue[1], cue[2]
        overlaps = any(max(st, d_st) < min(ed, d_ed) - 0.15 for d_st, d_ed in same_lang_windows)
        if not overlaps:
            filtered.append(cue)
    return filtered


def apply_v017_essential_sound_via_cli(cli_bin: str, fcproj_path: Path, seq: dict):
    """
    Uses FilmCraft v0.17.0+ native `essentialSound.*` commands via `filmcraft-cli run` to:
    - Tag Dialogue (`A4` voiceover + `A1` dialog clips), Music (`A2`), SFX (`A3`), and Ambience (`A1` riding clips)
    - Enable auto-ducking on `A2` Music (`reduceDb: -3.5`, `fadeS: 0.45`) and generate ducking keyframes against Dialogue.
    """
    dialogue_ids, ambience_ids, music_ids, sfx_ids = [], [], [], []
    audio_tracks = seq.get("audio_tracks", [])

    for idx, track in enumerate(audio_tracks):
        tname = (track.get("name") or "").lower()
        for it in track.get("items", []):
            cid = it.get("id")
            cname = (it.get("name") or "").lower()
            if idx == 3 or "voiceover" in tname or "dialog" in cname or "voiceover" in cname:
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
            "params": {
                "clips": dialogue_ids,
                "values": {"repair.rumble.on": True, "clarity.eq.on": True, "clarity.eqPreset": "Balanced Voice"},
            },
        })
    if ambience_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": ambience_ids, "type": "ambience"}})
    if sfx_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": sfx_ids, "type": "sfx"}})
    if music_ids:
        commands.append({"id": "essentialSound.setType", "params": {"clips": music_ids, "type": "music"}})
        commands.append({
            "id": "essentialSound.set",
            "params": {
                "clips": music_ids,
                "values": {
                    "ducking.enabled": True,
                    "ducking.reduceDb": -6.0,
                    "ducking.fadeS": 0.45,
                    "ducking.sensitivity": 6.0,
                },
            },
        })
        if dialogue_ids:
            commands.append({"id": "essentialSound.generateDucking", "params": {"clips": music_ids}})

    if not commands:
        return

    jsonl_payload = "\n".join(json.dumps(c) for c in commands) + "\n"
    res = subprocess.run(
        [cli_bin, "--project", str(fcproj_path), "--save", "run", "-"],
        input=jsonl_payload,
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0:
        print(
            f"Applied FilmCraft v0.17.0+ Essential Sound tags & auto-ducking "
            f"(Dialogue={len(dialogue_ids)}, Music={len(music_ids)}, Ambience={len(ambience_ids)}, SFX={len(sfx_ids)})"
        )
    else:
        print(f"Note: Essential Sound batch returned non-zero ({res.stderr.strip()[:200]})")


def verify_music_non_reuse(fcproj_path: Path, seq: dict, items: dict, strict: bool = True):
    """
    Article I Anti-Monotony & Mandatory Music Non-Reuse Law:
    Never reuse the same background music track across video projects.
    Scans all other projects in 04_Project_Catalog/ and halts if an A2 track is reused.
    """
    bgm_names = set()
    audio_tracks = seq.get("audio_tracks", [])
    for idx, track in enumerate(audio_tracks):
        tname = (track.get("name") or "").lower()
        if idx == 1 or "music" in tname or "bgm" in tname:
            for it in track.get("items", []):
                name = it.get("name")
                if name and name.endswith(".mp3"):
                    bgm_names.add(name)
                mid = str(it.get("item", it.get("media_id")))
                media = items.get(mid, {})
                file_p = media.get("kind", {}).get("Media", {}).get("media", {}).get("File", {}).get("path")
                if file_p and file_p.endswith(".mp3"):
                    bgm_names.add(Path(file_p).name)

    if not bgm_names:
        return

    studio_root = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
    catalog_dir = studio_root / "04_Project_Catalog"
    current_proj_dir = fcproj_path.parent.resolve()

    conflicts = []
    for other_proj in catalog_dir.glob("*/*"):
        if not other_proj.is_dir() or other_proj.resolve() == current_proj_dir:
            continue
        for bgm in bgm_names:
            for ext in ("*.fcproj", "Storyboard.md"):
                for f in other_proj.glob(ext):
                    text = f.read_text(errors="ignore")
                    if bgm in text:
                        conflicts.append((bgm, other_proj.name, f.name))

    if conflicts:
        lines = [f"  - '{c[0]}' already used in {c[1]} ({c[2]})" for c in conflicts]
        msg = (
            f"\n🚨 FATAL ERROR: Article I Music Non-Reuse Law Violation!\n"
            f"The following track(s) in {fcproj_path.parent.name} were already used in past projects:\n"
            + "\n".join(lines)
            + "\n\nEvery ride, hike, party, and event MUST have its own unique musical identity.\n"
            "Please select a fresh track from 03_Audio_Library/01_Curated_BGM/ or run `fetch_creatormix_catalog.py`.\n"
        )
        if strict:
            raise ValueError(msg)
        else:
            print(f"WARNING: {msg}")
    else:
        for bgm in bgm_names:
            print(f"✅ Music Non-Reuse Check Passed: Track '{bgm}' is unique to {fcproj_path.parent.name}.")


def verify_zero_project_scripts(fcproj_path: Path):
    """Enforces the Zero-Script Project Law: no per-project assemble_*.py or build_*_overlays.py scripts allowed."""
    proj_dir = fcproj_path.parent
    rogue = list(proj_dir.glob("assemble_*.py")) + list(proj_dir.glob("build_*_overlays.py"))
    if rogue:
        names = ", ".join(p.name for p in rogue)
        raise RuntimeError(
            f"\n🚨 FATAL ERROR: Zero-Script Project Law Violation in {proj_dir.name}!\n"
            f"Found banned per-project script(s): {names}\n"
            f"Projects must be 100% declarative (`timeline_spec.json` + `Storyboard.md`) and built via `build_timeline.py`."
        )


def polish_and_render_project(fcproj_path: Path, output_mp4: Path = None, burn_captions: bool = False, allow_used_music: bool = False):
    """Applies Studio v2 quality standards (4K UHD, Ken Burns, Essential Sound auto-ducking, Dip to Black) and exports master MP4."""
    env_status = verify_filmcraft_environment(auto_sync_cli=True, check_remote=True)
    cli_bin = env_status.get("cli_binary") or "/opt/homebrew/bin/filmcraft-cli"

    print(f"Loading project for polishing: {fcproj_path}")
    data = json.loads(fcproj_path.read_text(encoding="utf-8"))
    proj = data["project"]
    items = proj["items"]
    seq_id = str(data["view"].get("active_sequence") or 98)
    if seq_id not in items or "Sequence" not in items[seq_id].get("kind", {}):
        for k, v in items.items():
            if "Sequence" in v.get("kind", {}):
                seq_id = k
                break
    seq = items[seq_id]["kind"]["Sequence"]
    next_id = data.get("next_id", 300)

    # 1. Clear accidental duplicate items from V2
    if len(seq.get("video_tracks", [])) > 1:
        v1_names = {it.get("name") for it in seq["video_tracks"][0].get("items", [])}
        v2_items = seq["video_tracks"][1].get("items", [])
        if any(it.get("name") in v1_names for it in v2_items):
            print("Clearing duplicate occluding items from V2 track.")
            seq["video_tracks"][1]["items"] = []
            seq["video_tracks"][1]["transitions"] = []

    # 1b. Enforce Zero-Script Project Law & Article I Music Non-Reuse Law
    verify_zero_project_scripts(fcproj_path)
    verify_music_non_reuse(fcproj_path, seq, items, strict=not allow_used_music)

    # 2. Auto-detect 4K UHD (3840x2160) when sources exceed 1080p, enforce V1 visual continuity, apply scale_to_frame=True, Ken Burns & Dip-to-Black
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
            # Still images: apply Ken Burns unless the still is a pre-composed full-frame 16:9 graphic (e.g. Strava comparison card, infographic, or 4K/HUD canvas)
            is_static_graphic = "-4k." in name.lower() or "graphic" in name.lower() or "card" in name.lower() or (src_w == seq_w and src_h == seq_h and "strava" in name.lower())
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")) and not is_static_graphic:
                it["scale_to_frame"] = False
                effects = it.get("effects", [])
                effects = [e for e in effects if e.get("effect") != "motion"]
                effects.insert(0, make_motion_ken_burns(dur_s, src_w, src_h, seq_w, seq_h, zoom_in=still_zoom_toggle))
                still_zoom_toggle = not still_zoom_toggle
                it["effects"] = effects
                print(f"Applied full-bleed 2-axis Ken Burns motion to {name} ({src_w}x{src_h} -> {seq_w}x{seq_h}, {dur_s:.1f}s)")
            elif is_static_graphic:
                it["scale_to_frame"] = True
                effects = it.get("effects", [])
                effects = [e for e in effects if e.get("effect") != "motion"]
                effects.insert(0, make_static_motion(src_w, src_h, seq_w, seq_h))
                it["effects"] = effects
                print(f"Preserved static full-frame graphic framing for {name} ({src_w}x{src_h})")
            else:
                it["scale_to_frame"] = True
                for eff in it.get("effects", []):
                    if eff.get("effect") == "motion":
                        eff["params"]["position"] = {"value": {"Vec2": {"x": seq_w / 2.0, "y": seq_h / 2.0}}}
                        eff["params"]["anchor"] = {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}}
                        eff["params"]["scale"] = {"value": {"Float": 100.0}}

        # Native Dip-to-Black transition on closing clip
        last_clip = all_v1_items[-1]
        last_clip_id = last_clip["id"]
        last_end_ticks = last_clip["start"] + last_clip["duration"]
        fade_ticks = int(1.5 * TICKS_PER_SEC)
        v1["transitions"] = [
            {
                "id": next_id,
                "effect": {
                    "effect": "dip_to_black",
                    "enabled": True,
                    "params": {},
                },
                "start": last_end_ticks - fade_ticks,
                "duration": fade_ticks,
                "from": last_clip_id,
                "to": None,
                "align": "EndAtCut",
                "reverse": False,
            }
        ]
        next_id += 1
        print(f"Applied native Dip-to-Black (1.5s) transition to closing clip {last_clip.get('name')}")

        # Synchronized 2.2s Audio Outro Fade on A2 (Music)
        audio_tracks = seq.get("audio_tracks", [])
        if len(audio_tracks) > 1 and audio_tracks[1].get("items"):
            a2 = audio_tracks[1]
            last_music_clip = a2["items"][-1]
            music_end_ticks = last_music_clip["start"] + last_music_clip["duration"]
            audio_fade_ticks = int(2.2 * TICKS_PER_SEC)
            a2["transitions"] = [
                {
                    "id": next_id,
                    "effect": {
                        "effect": "constant_power",
                        "enabled": True,
                        "params": {},
                    },
                    "start": max(last_music_clip["start"], music_end_ticks - audio_fade_ticks),
                    "duration": audio_fade_ticks,
                    "from": last_music_clip["id"],
                    "to": None,
                    "align": "EndAtCut",
                    "reverse": False,
                }
            ]
            next_id += 1
            print(f"Applied synchronized 2.2s Audio Outro Fade to closing music clip {last_music_clip.get('name')}")

    # 3. Sanitize Subtitles in Caption Tracks & Preserve Visibility in Timeline UI
    # Always keep caption tracks enabled=True in .fcproj so all 3 language subtitle tracks
    # (English, Українська, Русский) remain visible on the FilmCraft timeline UI!
    # Clean MP4 export (without burnt-in captions) is controlled separately via --settings '{"burnCaptions": false}'.
    if seq.get("caption_tracks"):
        for ct in seq["caption_tracks"]:
            ct["enabled"] = True
            for cap in ct.get("captions", []):
                orig_text = cap.get("text", "")
                cap["text"] = sanitize_caption_text(orig_text)
                cap.setdefault("speaker", None)
                cap.setdefault("cue_id", None)
                cap.setdefault("settings", "")
        print(f"Sanitized caption glyphs in {len(seq['caption_tracks'])} track(s) (caption tracks enabled=True in timeline)")

    data["next_id"] = next_id
    fcproj_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Updated {fcproj_path.name} with polishing parameters.")

    # 4. Apply FilmCraft v0.17.0+ Essential Sound tags & auto-ducking keyframes
    apply_v017_essential_sound_via_cli(cli_bin, fcproj_path, seq)

    # 5. Render MP4 (burnCaptions=false by default in Studio v2)
    if output_mp4:
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        burn_json = "true" if burn_captions else "false"
        print(f"Rendering polished master MP4 -> {output_mp4} with burnCaptions={burn_json}...")
        cmd = [
            cli_bin,
            "--project", str(fcproj_path),
            "export", str(output_mp4),
            "--preset", "Match Source – Adaptive High Bitrate",
            "--settings", f'{{"burnCaptions": {burn_json}}}',
        ]
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"Export successful -> {output_mp4} ({round(output_mp4.stat().st_size / 1024 / 1024, 1)} MB)")


def main():
    p = argparse.ArgumentParser(description="Universal Timeline Assembly & Polishing Engine (FilmCraft v0.17.0+)")
    p.add_argument("--project", required=True, help="Path to .fcproj project file")
    p.add_argument("--export-mp4", help="Optional path to output master MP4")
    p.add_argument("--burn-captions", action="store_true", help="Burn captions into video (default: False in Studio v2)")
    p.add_argument("--allow-used-music", action="store_true", help="Allow tracks already used in past projects (default: False)")
    args = p.parse_args()

    fcproj = Path(args.project).expanduser().resolve()
    mp4 = Path(args.export_mp4).expanduser().resolve() if args.export_mp4 else None
    polish_and_render_project(fcproj, mp4, burn_captions=args.burn_captions, allow_used_music=args.allow_used_music)


if __name__ == "__main__":
    main()
