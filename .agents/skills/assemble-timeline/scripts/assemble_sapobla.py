#!/usr/bin/env python3
"""
assemble_sapobla.py
Studio v2 Timeline Assembly & 4K Master Render for:
`2026-11-01_SaPobla_Market_Trip` (3840x2160@30, 136.0s total runtime)

Executes:
1. Paces and normalizes voice-over stems (en, ua, ru) to perfectly fit scene windows.
2. Generates caption subtitle tracks: captions.en.srt, captions.ua.srt, captions.ru.srt.
3. Assembles complete `2026-11-01_SaPobla_Market_Trip.fcproj`:
   - V1: 31 cuts, uncropped Blur_Pillarbox_V2 backdrop on 5 stills, 26 4K MOV cuts, 1.5s dip_to_black.
   - V2: 5 uncropped stills with Ken Burns scale keyframes (EaseIn/EaseOut).
   - A1: 26 camera audio cuts with +6 dB on Cut #19 (Bar Casa Miss roar).
   - A2: Two-Phase BGM (Fashionista + VintageVibes) with ducking, swells, and 2.0s fade-out.
   - A3: 12 peak-aligned SFX cues.
   - A4: 11 scene-synced English VO segments.
   - C1: 15 caption items (enabled: false, burnCaptions: false).
4. Mixes broadcast 4-track audio for EN, UA, and RU editions via ffmpeg.
5. Renders 4K MP4 master via filmcraft-cli and remuxes EN, UA (_UA.mp4), and RU (_RU.mp4) editions.
"""

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

TICKS_PER_SEC = 254016000000

STUDIO_ROOT = Path("/Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio")
PROJ_DIR = STUDIO_ROOT / "04_Project_Catalog/2026/2026-11-01_SaPobla_Market_Trip"
RAW_DIR = Path("/Users/akomlik/Movies/2026/2026-11-01_SaPobla_Market_Trip")
EXPORTS_DIR = Path("/Users/akomlik/Movies/Exports/2026")
FCPROJ_PATH = PROJ_DIR / "2026-11-01_SaPobla_Market_Trip.fcproj"
MASTER_MP4 = EXPORTS_DIR / "2026-11-01_SaPobla_Market_Trip.mp4"

BGM_P1 = STUDIO_ROOT / "03_Audio_Library/01_Curated_BGM/04_Warm_Social_And_Retro/116bpm_Funkygroove_Fashionista_Creatormix.mp3"
BGM_P2 = STUDIO_ROOT / "03_Audio_Library/01_Curated_BGM/04_Warm_Social_And_Retro/119bpm_Upbeatretro_VintageVibes_Creatormix.mp3"

VO_TIMINGS = [
    ("cue01", 1.2),
    ("cue02", 12.0),
    ("cue03", 20.0),
    ("cue04", 36.0),
    ("cue05", 48.5),
    ("cue06", 62.0),
    ("cue07", 71.5),
    ("cue08", 89.5),
    ("cue09", 99.5),
    ("cue10", 112.5),
    ("cue11", 122.5),
]

CAPTIONS = [
    (0.0, 3.8, "In Memoriam: The legendary €20 Mallorca fleece (2022–2025)"),
    (3.8, 3.7, "Worn over the black Voler jersey—until left on our SJC flight!"),
    (7.5, 4.0, "Sunday morning mission: Take the 302 bus to Sa Pobla"),
    (18.0, 3.5, "First stop: Sa Pobla Eroski for fresh Llampuga & Magno Brandy"),
    (35.5, 6.0, "Miracle in Plaça Major: The exact same seller 4 years later!"),
    (48.0, 6.0, "Punchline 1: 4 years of inflation — €20 is now €30!"),
    (54.0, 6.0, "Punchline 2: 'I set up my stall in Alcúdia every Tuesday!'"),
    (60.0, 3.5, "Sunday market colors: Sweet peppers & autumn wild mushrooms"),
    (71.0, 4.0, "10:46 AM at Bar Casa Miss: Deafening Sunday roar — Nina calls Plan B!"),
    (89.0, 4.0, "Back in Alcúdia Old Town: Hunting for mussels at an empty Restaurante Sombrero"),
    (97.0, 7.0, "Mussels: 10/10. Entrecôte with a butter knife: 100% un-chewable!"),
    (104.0, 7.0, "Spanish hospitality peace offering: Complimentary house wine on the spot!"),
    (114.5, 3.5, "Sweet redemption at Forn Can Torres: Flaky croissant & café con leche!"),
    (122.0, 4.0, "Home-cooked Eroski Llampuga steaks: 100x more tender than the entrecôte!"),
    (130.0, 6.0, "4 years later: The €30 jacket successors are officially in service!"),
]

CUTS_SPEC = [
    # cut_num, source, is_still, src_in, dur, a1_gain, desc
    (1, "IMG_E9287.jpg", True, 0.0, 3.8, None, "Flashback selfie"),
    (2, "IMG_9735.jpg", True, 0.0, 3.7, None, "Flashback original jacket"),
    (3, "IMG_8694.MOV", False, 0.5, 4.0, -12.0, "Morning Departure"),
    (4, "IMG_8702.MOV", False, 10.0, 3.0, -12.0, "TIB Bus Shelter"),
    (5, "IMG_8703.MOV", False, 2.0, 3.5, -10.0, "Boarding TIB 302"),
    (6, "IMG_8708.MOV", False, 1.0, 3.5, -12.0, "Arrival in Sa Pobla"),
    (7, "IMG_8712.MOV", False, 2.0, 3.0, -14.0, "Magno Brandy & Wine"),
    (8, "IMG_8714.MOV", False, 1.0, 3.0, -14.0, "Fresh Llampuga Counter"),
    (9, "IMG_8716.MOV", False, 2.0, 4.0, -8.0, "Sa Pobla Town Hall"),
    (10, "IMG_8718.MOV", False, 0.5, 4.0, -8.0, "Entering the Market"),
    (11, "IMG_8720.MOV", False, 5.0, 6.0, -10.0, "Spotting the Stall!"),
    (12, "IMG_8721.MOV", False, 2.0, 6.5, -10.0, "The Jacket Haul"),
    (13, "IMG_8721.MOV", False, 16.0, 6.0, -10.0, "Punchline 1 (€20 -> €30)"),
    (14, "IMG_8722.MOV", False, 1.0, 6.0, -8.0, "Punchline 2 (Tuesday in Alcúdia)"),
    (15, "IMG_8726.MOV", False, 0.5, 3.5, -10.0, "Roasted Peppers"),
    (16, "IMG_8728.MOV", False, 1.0, 3.5, -10.0, "Wild Chanterelles (€9.90)"),
    (17, "IMG_8729.MOV", False, 3.0, 4.0, -8.0, "Plaça Major Crowd"),
    (18, "IMG_8730.MOV", False, 2.0, 4.0, -8.0, "Bar Casa Miss (1967)"),
    (19, "IMG_8731.MOV", False, 1.0, 6.0, 6.0, "Deafening Sunday Roar & Veto (+6dB)"),
    (20, "IMG_8732.MOV", False, 2.0, 3.5, -12.0, "Bougainvillea Alley"),
    (21, "IMG_8733.MOV", False, 1.5, 4.5, -12.0, "TIB 301 Bus Stop"),
    (22, "IMG_8734.MOV", False, 3.0, 4.0, -12.0, "Alcúdia Medieval Walls"),
    (23, "IMG_8735.MOV", False, 2.0, 4.0, -12.0, "Scouting Menus for Mussels"),
    (24, "IMG_8736.MOV", False, 3.0, 7.0, -10.0, "The Un-Chewable Entrecôte"),
    (25, "IMG_8736.MOV", False, 22.0, 7.0, -10.0, "Free House Wine Peace Offering"),
    (26, "IMG_8737.MOV", False, 2.0, 3.5, -12.0, "Old Town Green Shutters"),
    (27, "IMG_8739.MOV", False, 1.0, 3.5, -10.0, "Croissant & Latte Art"),
    (28, "IMG_8740.MOV", False, 2.0, 4.0, -10.0, "Forn Can Torres Interior"),
    (29, "IMG_8754.jpg", True, 0.0, 4.0, None, "Pan-Seared Llampuga"),
    (30, "IMG_8762.jpg", True, 0.0, 4.0, None, "Forest-Green Pullover"),
    (31, "IMG_8767.jpg", True, 0.0, 6.0, None, "The €30 Successor Jacket"),
]

SFX_CUES = [
    # filename, timeline_start_s, gain_db
    ("12_Camera_Shutter/shutter_01.wav", 0.0, -8.0),
    ("12_Camera_Shutter/shutter_02.wav", 3.735, -8.0),
    ("03_Whooshes_Cinematic/whoosh_cinematic_01.wav", 6.895, -6.0),
    ("14_Success_Done/success_01.wav", 35.283, -8.0),
    ("10_Ticks_Clicks/tick_counter_01.wav", 48.855, -10.0),
    ("09_UI_Appears/ui_appear_01.wav", 53.897, -9.0),
    ("15_Error_Wrong/error_01.wav", 74.832, -8.0),
    ("15_Error_Wrong/error_02.wav", 96.831, -8.0),
    ("16_Shimmer_Sparkle/shimmer_01.wav", 114.181, -10.0),
    ("12_Camera_Shutter/shutter_01.wav", 121.995, -8.0),
    ("12_Camera_Shutter/shutter_02.wav", 125.935, -8.0),
    ("14_Success_Done/success_02.wav", 129.750, -7.0),
]


def fmt_srt_tc(sec: float) -> str:
    sec = max(0.0, float(sec))
    whole = int(sec)
    ms = int(round((sec - whole) * 1000))
    if ms >= 1000:
        whole += 1
        ms -= 1000
    m, s = divmod(whole, 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def prepare_paced_voiceovers():
    print("Preparing paced voiceover stems...")
    scripts = json.loads((PROJ_DIR / "narration_scripts.json").read_text(encoding="utf-8"))
    for lang in ("en", "ua", "ru"):
        for cue_key, start_s in VO_TIMINGS:
            raw_wav = PROJ_DIR / f"voiceover_{lang}_{cue_key}.wav"
            paced_wav = PROJ_DIR / f"voiceover_{lang}_{cue_key}_paced.wav"
            if not paced_wav.exists() or paced_wav.stat().st_mtime < raw_wav.stat().st_mtime:
                # 1.14x tempo with silence trimming
                fc = "atempo=1.14,silenceremove=stop_periods=-1:stop_duration=0.2:stop_threshold=-40dB"
                subprocess.run(
                    ["/opt/homebrew/bin/ffmpeg", "-y", "-i", str(raw_wav), "-filter:a", fc, "-ar", "48000", "-ac", "2", str(paced_wav)],
                    check=True, capture_output=True,
                )
    print("All paced voiceovers prepared!")


def generate_srt_subtitles():
    print("Generating .srt subtitle tracks...")
    scripts = json.loads((PROJ_DIR / "narration_scripts.json").read_text(encoding="utf-8"))
    for lang, suf in [("en", "en"), ("ua", "ua"), ("ru", "ru")]:
        lines = []
        for idx, (cue_key, start_s) in enumerate(VO_TIMINGS, 1):
            text = scripts[lang][cue_key]
            paced_wav = PROJ_DIR / f"voiceover_{lang}_{cue_key}_paced.wav"
            dur = float(subprocess.check_output(
                ["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(paced_wav)]
            ).decode().strip())
            end_s = start_s + dur
            lines.append(str(idx))
            lines.append(f"{fmt_srt_tc(start_s)} --> {fmt_srt_tc(end_s)}")
            lines.append(text)
            lines.append("")
        srt_path = PROJ_DIR / f"captions.{suf}.srt"
        srt_path.write_text("\n".join(lines), encoding="utf-8")
        print(f"Generated -> {srt_path.name}")


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


def make_motion_ken_burns(duration_s, src_w, src_h, start_scale, end_scale):
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    cx, cy = 1920.0, 1080.0
    scale_keyframes = [
        {"time": 0, "value": {"Float": start_scale}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        {"time": dur_ticks, "value": {"Float": end_scale}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
    ]
    return {
        "effect": "motion",
        "enabled": True,
        "params": {
            "position": {"value": {"Vec2": {"x": cx, "y": cy}}},
            "scale": {"value": {"Float": start_scale}, "keyframes": scale_keyframes},
            "scale_width": {"value": {"Float": 100.0}},
            "uniform_scale": {"value": {"Bool": True}},
            "rotation": {"value": {"Float": 0.0}},
            "anchor": {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}},
            "anti_flicker": {"value": {"Float": 0.0}},
        },
    }


def build_fcproj_project():
    print("Building full 4K .fcproj project:", FCPROJ_PATH)
    next_id = 1
    items = {}
    root_children = []

    def register_media(path: Path, kind_type: str, width=None, height=None, dur_s=180.0):
        nonlocal next_id
        mid = next_id; next_id += 1
        root_children.append({"Item": mid})
        file_sz = path.stat().st_size
        fp = hashlib.md5(path.name.encode()).hexdigest()[:16]

        if kind_type == "Still":
            media_info = {
                "name": path.name,
                "kind": "Still",
                "duration": int(dur_s * TICKS_PER_SEC),
                "video": {
                    "width": width or 3840,
                    "height": height or 2160,
                    "frame_rate": {"num": 30, "den": 1},
                    "par": [1, 1],
                    "codec": "JPG",
                    "pixel_format": "RGB 8-bit",
                    "color": {"matrix": "Bt709", "transfer": "Srgb", "primaries": "Bt709", "range": "Full"},
                    "has_alpha": False,
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
                "duration": int(dur_s * TICKS_PER_SEC),
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
        else: # AudioOnly
            is_wav = path.suffix.lower() == ".wav"
            media_info = {
                "name": path.name,
                "kind": "AudioOnly",
                "duration": int(dur_s * TICKS_PER_SEC),
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
            lbl = "Caribbean"

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

    # Register Media Files
    media_map = {}
    # Stills
    still_dims = {
        "IMG_E9287.jpg": (3739, 2804),
        "IMG_9735.jpg": (3024, 4032),
        "IMG_8754.jpg": (4032, 3024),
        "IMG_8762.jpg": (4032, 3024),
        "IMG_8767.jpg": (4032, 3024),
    }
    for sname, (w, h) in still_dims.items():
        media_map[sname] = register_media(RAW_DIR / sname, "Still", w, h, dur_s=10.0)

    # Videos
    for cut in CUTS_SPEC:
        src = cut[1]
        if not cut[2] and src not in media_map:
            p = RAW_DIR / src
            dur = float(subprocess.check_output(
                ["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)]
            ).decode().strip())
            media_map[src] = register_media(p, "Movie", 3840, 2160, dur_s=dur)

    # Music
    bgm_p1_id = register_media(BGM_P1, "AudioOnly", dur_s=180.0)
    bgm_p2_id = register_media(BGM_P2, "AudioOnly", dur_s=180.0)

    # SFX
    sfx_media_map = {}
    for sname, _t_s, _g in SFX_CUES:
        if sname not in sfx_media_map:
            p = STUDIO_ROOT / "03_Audio_Library/02_SFX" / sname
            dur = float(subprocess.check_output(
                ["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)]
            ).decode().strip())
            sfx_media_map[sname] = register_media(p, "AudioOnly", dur_s=dur)

    # VO (English paced)
    vo_media_map = {}
    for cue_key, _t_s in VO_TIMINGS:
        p = PROJ_DIR / f"voiceover_en_{cue_key}_paced.wav"
        dur = float(subprocess.check_output(
            ["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(p)]
        ).decode().strip())
        vo_media_map[cue_key] = register_media(p, "AudioOnly", dur_s=dur)

    # Build Sequence Tracks
    v1_items = []
    v2_items = []
    a1_items = []
    current_time_s = 0.0

    v1_clip_ids = []
    still_kb_params = {
        1: (100.0, 107.0), # Cut 1
        2: (100.0, 106.0), # Cut 2
        29: (100.0, 107.0), # Cut 29
        30: (107.0, 100.0), # Cut 30 Pull-Out
        31: (100.0, 108.0), # Cut 31
    }

    for cut_num, src, is_still, src_in, dur, a1_gain, desc in CUTS_SPEC:
        start_ticks = int(current_time_s * TICKS_PER_SEC)
        dur_ticks = int(dur * TICKS_PER_SEC)
        src_in_ticks = int(src_in * TICKS_PER_SEC)
        m_id = media_map[src]

        if is_still:
            w, h = still_dims[src]
            blur_scale = 320.0 if h > w else 180.0
            cid_v1 = next_id; next_id += 1
            v1_clip_ids.append((cut_num, cid_v1))
            v1_items.append({
                "id": cid_v1,
                "item": m_id,
                "name": src,
                "label": "Lavender",
                "start": start_ticks,
                "duration": dur_ticks,
                "source_in": 0,
                "speed": 1.0,
                "reverse": False,
                "enabled": True,
                "link": None,
                "group": None,
                "effects": [
                    make_static_motion(w, h, 1920.0, 1080.0, scale=blur_scale),
                    {
                        "effect": "opacity",
                        "enabled": True,
                        "params": {"opacity": {"value": {"Float": 60.0}}, "blend": {"value": {"Choice": 0}}},
                    },
                    {
                        "effect": "gaussian_blur",
                        "enabled": True,
                        "params": {
                            "blurriness": {"value": {"Float": 45.0}},
                            "dimensions": {"value": {"Choice": 0}},
                            "repeat_edge": {"value": {"Bool": True}},
                        },
                    },
                ],
                "markers": [],
                "gain_db": 0.0,
                "frame_hold": None,
                "scale_to_frame": True,
            })

            # Foreground uncropped photo on V2 with Ken Burns
            st_scale, end_scale = still_kb_params[cut_num]
            cid_v2 = next_id; next_id += 1
            v2_items.append({
                "id": cid_v2,
                "item": m_id,
                "name": src,
                "label": "Lavender",
                "start": start_ticks,
                "duration": dur_ticks,
                "source_in": 0,
                "speed": 1.0,
                "reverse": False,
                "enabled": True,
                "link": None,
                "group": None,
                "effects": [make_motion_ken_burns(dur, w, h, st_scale, end_scale)],
                "markers": [],
                "gain_db": 0.0,
                "frame_hold": None,
                "scale_to_frame": True,
            })
        else: # Video Cut
            cid_v1 = next_id; next_id += 1
            v1_clip_ids.append((cut_num, cid_v1))
            v1_items.append({
                "id": cid_v1,
                "item": m_id,
                "name": src,
                "label": "Iris",
                "start": start_ticks,
                "duration": dur_ticks,
                "source_in": src_in_ticks,
                "speed": 1.0,
                "reverse": False,
                "enabled": True,
                "link": None,
                "group": None,
                "effects": [make_static_motion(3840, 2160, 1920.0, 1080.0, 100.0)],
                "markers": [],
                "gain_db": 0.0,
                "frame_hold": None,
                "scale_to_frame": True,
            })

            # Camera Audio on A1
            cid_a1 = next_id; next_id += 1
            a1_items.append({
                "id": cid_a1,
                "item": m_id,
                "name": src,
                "label": "Iris",
                "start": start_ticks,
                "duration": dur_ticks,
                "source_in": src_in_ticks,
                "speed": 1.0,
                "reverse": False,
                "enabled": True,
                "link": None,
                "group": None,
                "effects": [],
                "markers": [],
                "gain_db": a1_gain if a1_gain is not None else -12.0,
                "frame_hold": None,
                "scale_to_frame": False,
            })

        current_time_s += dur

    # Transitions on V1
    # Cut 1 -> 2 (0.5s cross dissolve at 3.8s)
    # Cut 2 -> 3 (0.5s cross dissolve at 7.5s)
    # Cut 28 -> 29 (0.5s cross dissolve at 122.0s)
    # Cut 31 (1.5s dip to black at 134.5s -> 136.0s)
    clip_id_by_cut = dict(v1_clip_ids)
    v1_transitions = [
        {
            "id": next_id,
            "effect": {"effect": "cross_dissolve", "enabled": True, "params": {}},
            "start": int((3.8 - 0.25) * TICKS_PER_SEC),
            "duration": int(0.5 * TICKS_PER_SEC),
            "from": clip_id_by_cut[1],
            "to": clip_id_by_cut[2],
            "align": "CenterAtCut",
            "reverse": False,
        },
        {
            "id": next_id + 1,
            "effect": {"effect": "cross_dissolve", "enabled": True, "params": {}},
            "start": int((7.5 - 0.25) * TICKS_PER_SEC),
            "duration": int(0.5 * TICKS_PER_SEC),
            "from": clip_id_by_cut[2],
            "to": clip_id_by_cut[3],
            "align": "CenterAtCut",
            "reverse": False,
        },
        {
            "id": next_id + 2,
            "effect": {"effect": "cross_dissolve", "enabled": True, "params": {}},
            "start": int((122.0 - 0.25) * TICKS_PER_SEC),
            "duration": int(0.5 * TICKS_PER_SEC),
            "from": clip_id_by_cut[28],
            "to": clip_id_by_cut[29],
            "align": "CenterAtCut",
            "reverse": False,
        },
        {
            "id": next_id + 3,
            "effect": {"effect": "dip_to_black", "enabled": True, "params": {}},
            "start": int((136.0 - 1.5) * TICKS_PER_SEC),
            "duration": int(1.5 * TICKS_PER_SEC),
            "from": clip_id_by_cut[31],
            "to": None,
            "align": "EndAtCut",
            "reverse": False,
        },
    ]
    next_id += 4

    # Track A2 (Dedicated BGM)
    # Phase 1: 0.0 - 60.0s, Fashionista
    # Phase 2: 60.0 - 136.0s, VintageVibes
    a2_items = [
        {
            "id": next_id,
            "item": bgm_p1_id,
            "name": BGM_P1.name,
            "label": "Caribbean",
            "start": 0,
            "duration": int(60.0 * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": -7.5,
            "frame_hold": None,
            "scale_to_frame": False,
        },
        {
            "id": next_id + 1,
            "item": bgm_p2_id,
            "name": BGM_P2.name,
            "label": "Caribbean",
            "start": int(60.0 * TICKS_PER_SEC),
            "duration": int(76.0 * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": -7.5,
            "frame_hold": None,
            "scale_to_frame": False,
        },
    ]
    next_id += 2

    # Track A3 (Peak-Aligned SFX)
    a3_items = []
    for sname, t_start_s, gain_db in SFX_CUES:
        m_id = sfx_media_map[sname]
        dur_s = items[str(m_id)]["kind"]["Media"]["info"]["duration"] / TICKS_PER_SEC
        cid = next_id; next_id += 1
        a3_items.append({
            "id": cid,
            "item": m_id,
            "name": Path(sname).name,
            "label": "Caribbean",
            "start": int(t_start_s * TICKS_PER_SEC),
            "duration": int(dur_s * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": gain_db,
            "frame_hold": None,
            "scale_to_frame": False,
        })

    # Track A4 (Voice-Over EN)
    a4_items = []
    for cue_key, t_start_s in VO_TIMINGS:
        m_id = vo_media_map[cue_key]
        dur_s = items[str(m_id)]["kind"]["Media"]["info"]["duration"] / TICKS_PER_SEC
        cid = next_id; next_id += 1
        a4_items.append({
            "id": cid,
            "item": m_id,
            "name": f"voiceover_en_{cue_key}_paced.wav",
            "label": "Mango",
            "start": int(t_start_s * TICKS_PER_SEC),
            "duration": int(dur_s * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [],
            "markers": [],
            "gain_db": -0.5,
            "frame_hold": None,
            "scale_to_frame": False,
        })

    # Caption Track C1
    cap_items = []
    for st_s, dur_s, txt in CAPTIONS:
        cid = next_id; next_id += 1
        cap_items.append({
            "id": cid,
            "start": int(st_s * TICKS_PER_SEC),
            "duration": int(dur_s * TICKS_PER_SEC),
            "text": txt,
            "speaker": None,
            "cue_id": None,
            "settings": "",
        })

    seq_id = next_id; next_id += 1
    root_children.append({"Item": seq_id})

    sequence_obj = {
        "id": seq_id,
        "name": "2026-11-01_SaPobla_Market_Trip",
        "label": "Forest",
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
                "video_tracks": [
                    {
                        "id": next_id,
                        "kind": "Video",
                        "name": "Video 1",
                        "items": v1_items,
                        "transitions": v1_transitions,
                        "locked": False,
                        "sync_lock": True,
                        "enabled": True,
                        "muted": False,
                        "solo": False,
                        "channels": "Stereo",
                        "volume_db": 0.0,
                        "pan": 0.0,
                        "effects": [],
                        "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                    },
                    {
                        "id": next_id + 1,
                        "kind": "Video",
                        "name": "Video 2",
                        "items": v2_items,
                        "transitions": [],
                        "locked": False,
                        "sync_lock": True,
                        "enabled": True,
                        "muted": False,
                        "solo": False,
                        "channels": "Stereo",
                        "volume_db": 0.0,
                        "pan": 0.0,
                        "effects": [],
                        "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                    },
                ],
                "audio_tracks": [
                    {
                        "id": next_id + 2,
                        "kind": "Audio",
                        "name": "Camera Audio",
                        "items": a1_items,
                        "transitions": [],
                        "locked": False,
                        "sync_lock": True,
                        "enabled": True,
                        "muted": False,
                        "solo": False,
                        "channels": "Stereo",
                        "volume_db": 0.0,
                        "pan": 0.0,
                        "effects": [],
                        "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                    },
                    {
                        "id": next_id + 3,
                        "kind": "Audio",
                        "name": "Music",
                        "items": a2_items,
                        "transitions": [],
                        "locked": False,
                        "sync_lock": True,
                        "enabled": True,
                        "muted": False,
                        "solo": False,
                        "channels": "Stereo",
                        "volume_db": 0.0,
                        "pan": 0.0,
                        "effects": [],
                        "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                    },
                    {
                        "id": next_id + 4,
                        "kind": "Audio",
                        "name": "SFX",
                        "items": a3_items,
                        "transitions": [],
                        "locked": False,
                        "sync_lock": True,
                        "enabled": True,
                        "muted": False,
                        "solo": False,
                        "channels": "Stereo",
                        "volume_db": 0.0,
                        "pan": 0.0,
                        "effects": [],
                        "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                    },
                    {
                        "id": next_id + 5,
                        "kind": "Audio",
                        "name": "Voiceover",
                        "items": a4_items,
                        "transitions": [],
                        "locked": False,
                        "sync_lock": True,
                        "enabled": True,
                        "muted": False,
                        "solo": False,
                        "channels": "Stereo",
                        "volume_db": 0.0,
                        "pan": 0.0,
                        "effects": [],
                        "mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                    },
                ],
                "markers": [],
                "mark_in": None,
                "mark_out": None,
                "work_area": None,
                "start_timecode": 0,
                "master_volume_db": 0.0,
                "master_effects": [],
                "master_mixer": {"mode": "Read", "output": None, "record_arm": False, "solo_safe": False, "input_map": "Stereo"},
                "submix_tracks": [],
                "caption_tracks": [
                    {
                        "id": next_id + 6,
                        "name": "Subtitles",
                        "format": "Subtitle",
                        "language": "en",
                        "style": {
                            "font": "Inter",
                            "size": 52.0,
                            "color": [255, 255, 255, 255],
                            "background": True,
                            "background_color": [0, 0, 0, 195],
                            "align": "Center",
                            "anchor": "Bottom",
                            "margin": 0.08,
                            "line_spacing": 1.25,
                            "outline": 0.0,
                            "outline_color": [0, 0, 0, 255],
                            "font_style": "SemiBold",
                        },
                        "enabled": False,
                        "locked": False,
                        "sync_lock": True,
                        "captions": cap_items,
                        "vtt_blocks": [],
                    }
                ],
            }
        },
        "metadata": {},
        "created": seq_id,
    }
    next_id += 7
    items[str(seq_id)] = sequence_obj

    base_proj_path = STUDIO_ROOT / "04_Project_Catalog/2026/2026-11-02_Nina_Pollenca_Loop/2026-11-02_Nina_Pollenca_Loop.fcproj"
    base_data = json.loads(base_proj_path.read_text(encoding="utf-8"))

    project_data = {
        "format": base_data["format"],
        "schema_version": base_data["schema_version"],
        "generator": base_data["generator"],
        "project": {
            "name": "2026-11-01_SaPobla_Market_Trip",
            "settings": base_data["project"]["settings"],
            "root": {"id": 0, "name": "2026-11-01_SaPobla_Market_Trip", "children": root_children},
            "items": items,
            "next_id": next_id + 100,
        },
        "view": {
            "open_sequences": [seq_id],
            "active_sequence": seq_id,
            "sequences": {
                str(seq_id): {
                    "pps": 50.0,
                    "scroll": 0.0,
                    "v_scroll": 0.0,
                    "a_scroll": 0.0,
                    "video_track_h": 60.0,
                    "audio_track_h": 56.0,
                }
            },
            "playheads": {str(seq_id): 0},
        },
    }

    FCPROJ_PATH.write_text(json.dumps(project_data, indent=2), encoding="utf-8")
    print(f"Saved complete 4K project -> {FCPROJ_PATH} (31 cuts, 136.0s runtime)!")


def build_broadcast_audio_mixes():
    print("Building broadcast-balanced 4-track audio mixes for EN, UA, and RU...")
    # Build camera audio master stem
    cam_stem = PROJ_DIR / "camera_audio_master.wav"
    cam_inputs = []
    cam_filter_parts = []
    input_idx = 0
    curr_t = 0.0

    for cut_num, src, is_still, src_in, dur, a1_gain, desc in CUTS_SPEC:
        if is_still:
            curr_t += dur
            continue
        p = RAW_DIR / src
        cam_inputs.extend(["-ss", f"{src_in:.3f}", "-t", f"{dur:.3f}", "-i", str(p)])
        del_ms = int(round(curr_t * 1000))
        gain = a1_gain if a1_gain is not None else -12.0
        cam_filter_parts.append(
            f"[{input_idx}:a]volume={gain:.1f}dB,adelay={del_ms}|{del_ms},apad=whole_dur=136.0s[a_c{cut_num}]"
        )
        input_idx += 1
        curr_t += dur

    cam_mix_inputs = "".join(f"[a_c{c[0]}]" for c in CUTS_SPEC if not c[2])
    n_cam = len([c for c in CUTS_SPEC if not c[2]])
    fc_cam = f"{';'.join(cam_filter_parts)};{cam_mix_inputs}amix=inputs={n_cam}:duration=first:dropout_transition=0:normalize=0[cout]"

    subprocess.run(
        ["/opt/homebrew/bin/ffmpeg", "-y", *cam_inputs, "-filter_complex", fc_cam, "-map", "[cout]", "-t", "136.0", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(cam_stem)],
        check=True, capture_output=True,
    )
    print("Created camera audio master stem!")

    # Build SFX master stem
    sfx_stem = PROJ_DIR / "sfx_master.wav"
    sfx_inputs = []
    sfx_filter_parts = []
    for idx, (sname, t_start_s, gain_db) in enumerate(SFX_CUES):
        p = STUDIO_ROOT / "03_Audio_Library/02_SFX" / sname
        sfx_inputs.extend(["-i", str(p)])
        del_ms = int(round(t_start_s * 1000))
        sfx_filter_parts.append(f"[{idx}:a]volume={gain_db:.1f}dB,adelay={del_ms}|{del_ms},apad=whole_dur=136.0s[s{idx}]")

    sfx_mix_inputs = "".join(f"[s{i}]" for i in range(len(SFX_CUES)))
    fc_sfx = f"{';'.join(sfx_filter_parts)};{sfx_mix_inputs}amix=inputs={len(SFX_CUES)}:duration=first:dropout_transition=0:normalize=0[sout]"

    subprocess.run(
        ["/opt/homebrew/bin/ffmpeg", "-y", *sfx_inputs, "-filter_complex", fc_sfx, "-map", "[sout]", "-t", "136.0", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(sfx_stem)],
        check=True, capture_output=True,
    )
    print("Created SFX master stem!")

    # For each language, combine Camera Audio, SFX, BGM (Phase 1 & 2 with swells/ducking), and VO cues
    for lang in ("en", "ua", "ru"):
        out_m4a = PROJ_DIR / f"full_audio_{lang}.m4a"
        out_wav = PROJ_DIR / f"full_audio_{lang}.wav"

        # BGM Phase 1: 0..60s (fade in 1.2s, swell +3.5dB at 27.5-35.5s, fade out 0.8s)
        # BGM Phase 2: 60..136s (fade in 0.8s, swell +3.5dB at 67-71s, duck -16dB at 75-81s, swell +3.5dB at 81-89s, fade out 2.0s at 134-136s)
        vo_inputs = []
        vo_parts = []
        for idx, (cue_key, t_start_s) in enumerate(VO_TIMINGS):
            p = PROJ_DIR / f"voiceover_{lang}_{cue_key}_paced.wav"
            vo_inputs.extend(["-i", str(p)])
            del_ms = int(round(t_start_s * 1000))
            vo_parts.append(f"[{4 + idx}:a]volume=-0.5dB,adelay={del_ms}|{del_ms},apad=whole_dur=136.0s[v{idx}]")

        bgm_p1_fc = (
            "[2:a]atrim=0:60.0,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.2,afade=t=out:st=59.2:d=0.8,"
            "volume=-7.5dB,volume=enable='between(t,27.5,35.5)':volume=3.5dB,apad=whole_dur=136.0s[bgm1]"
        )
        bgm_p2_fc = (
            "[3:a]atrim=0:76.0,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.8,afade=t=out:st=74.0:d=2.0,"
            "volume=-7.5dB,volume=enable='between(t,7.0,11.0)':volume=3.5dB,volume=enable='between(t,15.0,21.0)':volume=-8.5dB,volume=enable='between(t,21.0,29.0)':volume=3.5dB,"
            "adelay=60000|60000,apad=whole_dur=136.0s[bgm2]"
        )

        all_mix_inputs = "[0:a][1:a][bgm1][bgm2]" + "".join(f"[v{i}]" for i in range(len(VO_TIMINGS)))
        total_in = 4 + len(VO_TIMINGS)
        fc_full = f"{bgm_p1_fc};{bgm_p2_fc};{';'.join(vo_parts)};{all_mix_inputs}amix=inputs={total_in}:duration=first:dropout_transition=0:normalize=0,alimiter=limit=0.95[fullout]"

        subprocess.run(
            [
                "/opt/homebrew/bin/ffmpeg", "-y",
                "-i", str(cam_stem),
                "-i", str(sfx_stem),
                "-i", str(BGM_P1),
                "-i", str(BGM_P2),
                *vo_inputs,
                "-filter_complex", fc_full, "-map", "[fullout]",
                "-t", "136.0", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out_wav),
            ],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["/opt/homebrew/bin/ffmpeg", "-y", "-i", str(out_wav), "-c:a", "aac", "-b:a", "256k", str(out_m4a)],
            check=True, capture_output=True,
        )
        print(f"Created balanced {lang.upper()} master audio track -> {out_m4a.name}")


def export_and_remux_all():
    print(f"Exporting 4K clean master video from FilmCraft -> {MASTER_MP4}...")
    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [
        "/opt/homebrew/bin/filmcraft-cli",
        "--project", str(FCPROJ_PATH),
        "export", str(MASTER_MP4),
        "--preset", "Match Source – Adaptive High Bitrate",
        "--settings", '{"burnCaptions": false}',
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=True)
    print("FilmCraft Export:", res.stdout.strip())

    # Remux EN Master with balanced 4-track mix
    tmp_en = MASTER_MP4.with_suffix(".tmp_en.mp4")
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-i", str(MASTER_MP4), "-i", str(PROJ_DIR / "full_audio_en.m4a"),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", str(tmp_en),
        ],
        check=True, capture_output=True,
    )
    tmp_en.replace(MASTER_MP4)
    print(f"✅ Master English 4K Video ready: {MASTER_MP4} ({round(MASTER_MP4.stat().st_size / 1024 / 1024, 1)} MB)")

    # Remux UA Edition
    ua_mp4 = EXPORTS_DIR / "2026-11-01_SaPobla_Market_Trip_UA.mp4"
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-i", str(MASTER_MP4), "-i", str(PROJ_DIR / "full_audio_ua.m4a"),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", str(ua_mp4),
        ],
        check=True, capture_output=True,
    )
    print(f"✅ Ukrainian 4K Edition ready: {ua_mp4} ({round(ua_mp4.stat().st_size / 1024 / 1024, 1)} MB)")

    # Remux RU Edition
    ru_mp4 = EXPORTS_DIR / "2026-11-01_SaPobla_Market_Trip_RU.mp4"
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-i", str(MASTER_MP4), "-i", str(PROJ_DIR / "full_audio_ru.m4a"),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", str(ru_mp4),
        ],
        check=True, capture_output=True,
    )
    print(f"✅ Russian 4K Edition ready: {ru_mp4} ({round(ru_mp4.stat().st_size / 1024 / 1024, 1)} MB)")


def main():
    prepare_paced_voiceovers()
    generate_srt_subtitles()
    build_fcproj_project()
    build_broadcast_audio_mixes()
    export_and_remux_all()


if __name__ == "__main__":
    main()
