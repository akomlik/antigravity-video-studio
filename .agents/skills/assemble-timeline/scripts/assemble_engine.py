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
            # Portrait photo: smooth vertical sweep from upper face/subject down over torso/details
            pan_y = seq_h * 0.20
            start_pos = (cx, cy + pan_y)
            end_pos = (cx, cy - pan_y)
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
    """Measures RMS mean_volume in dB via ffmpeg volumedetect so hot-mastered music never overpowers narration."""
    out = subprocess.check_output(
        ["/opt/homebrew/bin/ffmpeg", "-i", str(audio_path), "-af", "volumedetect", "-f", "null", "-"],
        stderr=subprocess.STDOUT,
    ).decode("utf-8", errors="replace")
    for line in out.splitlines():
        if "mean_volume:" in line:
            try:
                return float(line.split("mean_volume:")[1].split("dB")[0].strip())
            except ValueError:
                pass
    return -16.0


def compute_bgm_ducked_gain_db(bgm_path: Path, target_ducked_mean_db: float = -28.5) -> float:
    """
    Computes the exact fader gain (dB) required so a music track sits at `target_ducked_mean_db` (-28.5 dB mean)
    underneath Voice-Over / Live Dialogue (-16.0 dB mean), guaranteeing >= 12.5 dB of speech-to-music headroom
    even on loud upbeat tracks (-10 dB to -12 dB raw RMS).
    """
    raw_mean = measure_mean_volume_db(bgm_path)
    return round(target_ducked_mean_db - raw_mean, 1)


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


def polish_and_render_project(fcproj_path: Path, output_mp4: Path = None, burn_captions: bool = False):
    """Applies Studio v2 quality standards (4K UHD, Ken Burns, Essential Sound auto-ducking, Dip to Black) and exports master MP4."""
    env_status = verify_filmcraft_environment(auto_sync_cli=True, check_remote=True)
    cli_bin = env_status.get("cli_binary") or "/opt/homebrew/bin/filmcraft-cli"

    print(f"Loading project for polishing: {fcproj_path}")
    data = json.loads(fcproj_path.read_text(encoding="utf-8"))
    proj = data["project"]
    items = proj["items"]
    seq_id = str(data["view"].get("active_sequence") or 98)
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

    # 2. Auto-detect 4K UHD (3840x2160) when sources exceed 1080p, apply scale_to_frame=True, Ken Burns & Dip-to-Black
    video_tracks = seq.get("video_tracks", [])
    if video_tracks and video_tracks[0].get("items"):
        v1 = video_tracks[0]
        all_v1_items = v1.get("items", [])
        max_src_w = max(
            (items.get(str(it["item"]), {}).get("kind", {}).get("Media", {}).get("info", {}).get("video") or {}).get("width", 1920)
            for it in all_v1_items
        )
        seq_w, seq_h = (3840, 2160) if max_src_w > 1920 else (1920, 1080)
        seq["settings"]["width"] = seq_w
        seq["settings"]["height"] = seq_h
        seq["settings"]["preset"] = f"{seq_w}x{seq_h} 30"

        still_zoom_toggle = True
        for it in all_v1_items:
            name = it.get("name", "")
            dur_s = it.get("duration", 0) / TICKS_PER_SEC
            media_id = str(it["item"])
            vinfo = items.get(media_id, {}).get("kind", {}).get("Media", {}).get("info", {}).get("video") or {}
            src_w = vinfo.get("width", 1920)
            src_h = vinfo.get("height", 1080)
            if name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
                it["scale_to_frame"] = False
                effects = it.get("effects", [])
                effects = [e for e in effects if e.get("effect") != "motion"]
                effects.insert(0, make_motion_ken_burns(dur_s, src_w, src_h, seq_w, seq_h, zoom_in=still_zoom_toggle))
                still_zoom_toggle = not still_zoom_toggle
                it["effects"] = effects
                print(f"Applied full-bleed 2-axis Ken Burns motion to {name} ({src_w}x{src_h} -> {seq_w}x{seq_h}, {dur_s:.1f}s)")
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

    # 3. Sanitize Subtitles in Caption Tracks & Set Burn-In Visibility
    if seq.get("caption_tracks"):
        for ct in seq["caption_tracks"]:
            ct["enabled"] = bool(burn_captions)
            for cap in ct.get("captions", []):
                orig_text = cap.get("text", "")
                cap["text"] = sanitize_caption_text(orig_text)
        print(f"Sanitized caption glyphs in {len(seq['caption_tracks'])} track(s) (burn_captions={burn_captions})")

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
    args = p.parse_args()

    fcproj = Path(args.project).expanduser().resolve()
    mp4 = Path(args.export_mp4).expanduser().resolve() if args.export_mp4 else None
    polish_and_render_project(fcproj, mp4, burn_captions=args.burn_captions)


if __name__ == "__main__":
    main()
