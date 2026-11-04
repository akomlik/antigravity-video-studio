#!/usr/bin/env python3
"""
rebuild_nina_loop.py
Upgrades 2026-11-02_Nina_Pollenca_Loop (Full 4K UHD 3840x2160) with:
1. Monday 11/2 Actual Zumba Video (`2026-11-02_Zumba.mp4`, 1024x576) at 31.4s - 36.6s:
   - Replaces the old spring flashback clip that was out of sync with the music.
   - Framed as a crisp 62% Picture-in-Picture B-roll card on V2 over the 4K Bellevue court
     photo (`IMG_7108.jpg` on V1) so the 576p clip is never over-stretched to full 4K.
   - Plays its own synchronized live Zumba class audio on A1 while Phase 1 BGM fades out cleanly.
2. GPX Corner Route Map Widgets (V2, top-right, 3.5s at each scene transition) generated
   directly from the .gpx file (`gpx_widgets.py`) in Imperial units (mi, ft).
3. Dynamic GPX Telemetry HUD Overlays (V3, top-left, on riding video clips with notable
   power/gradient peaks) in Imperial units (MPH, WATTS, BPM, GRADE %).
4. Imperial Units by default across all burned-in captions (21.5 mi, 531 ft).
5. Live reload in FilmCraft GUI via MCP (`file.open`) + 4K export (`2026-11-02_Nina_Pollenca_Loop.mp4`).
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gpx_widgets import load_gpx_stream, render_corner_map_widget, render_telemetry_hud_widget

TICKS_PER_SEC = 254016000000

CATALOG_DIR = Path("/Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/04_Project_Catalog/2026/2026-11-02_Nina_Pollenca_Loop")
RAW_DIR = Path("/Users/akomlik/Movies/2026/2026-11-02_Nina_Pollenca_Loop")
PROJECT_PATH = CATALOG_DIR / "2026-11-02_Nina_Pollenca_Loop.fcproj"
GPX_PATH = RAW_DIR / "Ride_with_Nina_to_her_Zumba_location_and_loop_over_Pollenca_back_home_with_Eroski_stop.gpx"
ZUMBA_MP4 = RAW_DIR / "2026-11-02_Zumba.mp4"
BGM_PHASE1 = Path("/Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/03_Audio_Library/01_Curated_BGM/04_Warm_Social_And_Retro/083bpm_Playfullofi_EasyPeasy_Creatormix.mp3")
BGM_PHASE2 = Path("/Users/akomlik/Gdrive-gmail/hobbies/Photo_Video/Video/Antigravity_Video_Studio/03_Audio_Library/01_Curated_BGM/01_Rolling_Cadence/127bpm_Coastalgroove_OceanDrive_Creatormix.mp3")
EXPORT_PATH = Path("/Users/akomlik/Movies/Exports/2026/2026-11-02_Nina_Pollenca_Loop.mp4")

CAPTIONS = [
    (0.0, 3.1, "2026-11-02 · Escorting Nina to Zumba & Pollença Loop (21.5 mi · 531 ft)"),
    (3.1, 4.2, "Below Puig de Sant Martí: Morning rollout from Port d'Alcúdia"),
    (7.3, 4.2, "8:53 AM: Escorting Nina toward her Bellevue Zumba court"),
    (11.5, 4.2, "Mile 3.2: Passing the horses at Ranxo Ses Roques"),
    (15.7, 4.2, "Cruising toward the Bellevue complex"),
    (19.9, 4.2, "Entering through the yellow archway"),
    (24.1, 4.2, "Mile 4.2: Arriving at the Bellevue tennis courts — Nina's Zumba stage"),
    (28.3, 3.1, "Nina ready on the outdoor Bellevue court"),
    (31.4, 5.2, "Monday's Zumba session in full swing on the Bellevue court!"),
    (36.6, 4.2, "Rolling up behind Nina through the court gate"),
    (40.8, 9.0, "Saved by Nina's sharp eyes: My right front disc brake pad just fell out!"),
    (49.8, 3.7, "Pushed pad back in by hand & rode past Pro Cycle Hire (closed for winter)"),
    (53.5, 3.7, "Mile 16.7: Cruising south along Badia de Pollença (18.3 mph)"),
    (57.2, 4.8, "Mile 21.5: Eroski haul in the SJBC musette — & brake fixed at home!"),
]


def make_volume_effect(fade_in_s=None, fade_out_s=None, duration_s=0.0):
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    keyframes = []
    if fade_in_s:
        in_ticks = int(fade_in_s * TICKS_PER_SEC)
        keyframes.extend([
            {"time": 0, "value": {"Float": -60.0}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
            {"time": in_ticks, "value": {"Float": 0.0}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        ])
    if fade_out_s:
        out_start_ticks = max(0, dur_ticks - int(fade_out_s * TICKS_PER_SEC))
        keyframes.extend([
            {"time": out_start_ticks, "value": {"Float": 0.0}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
            {"time": dur_ticks, "value": {"Float": -60.0}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        ])

    param_val = {"value": {"Float": 0.0}}
    if keyframes:
        param_val["keyframes"] = keyframes

    return [
        {"effect": "volume", "enabled": True, "params": {"bypass": {"value": {"Bool": False}}, "level": param_val}},
        {"effect": "channel_volume", "enabled": True, "params": {"bypass": {"value": {"Bool": False}}, "left": {"value": {"Float": 0.0}}, "right": {"value": {"Float": 0.0}}}},
        {"effect": "panner", "enabled": True, "params": {"balance": {"value": {"Float": 0.0}}}},
    ]


def make_motion_ken_burns(duration_s, src_w, src_h, seq_w=3840, seq_h=2160, zoom_in=True):
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    aspect = src_w / max(1, src_h)
    cx = seq_w / 2.0
    cy = seq_h / 2.0
    pan_offset = seq_h * (30.0 / 1080.0)
    if aspect < 1.5:
        start_scale = 134.0 if zoom_in else 142.0
        end_scale = 142.0 if zoom_in else 134.0
        start_y = (cy + pan_offset) if zoom_in else (cy - pan_offset)
        end_y = (cy - pan_offset) if zoom_in else (cy + pan_offset)
    else:
        start_scale = 100.0 if zoom_in else 108.0
        end_scale = 108.0 if zoom_in else 100.0
        start_y = cy
        end_y = cy

    scale_keyframes = [
        {"time": 0, "value": {"Float": start_scale}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        {"time": dur_ticks, "value": {"Float": end_scale}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
    ]

    pos_param = {"value": {"Vec2": {"x": cx, "y": start_y}}}
    if start_y != end_y:
        pos_param["keyframes"] = [
            {"time": 0, "value": {"Vec2": {"x": cx, "y": start_y}}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
            {"time": dur_ticks, "value": {"Vec2": {"x": cx, "y": end_y}}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        ]

    return {
        "effect": "motion",
        "enabled": True,
        "params": {
            "position": pos_param,
            "scale": {"value": {"Float": start_scale}, "keyframes": scale_keyframes},
            "scale_width": {"value": {"Float": 100.0}},
            "uniform_scale": {"value": {"Bool": True}},
            "rotation": {"value": {"Float": 0.0}},
            "anchor": {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}},
            "anti_flicker": {"value": {"Float": 0.0}},
        },
    }


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


def make_opacity_in_out(duration_s, fade_in_s=0.35, fade_out_s=0.45):
    dur_ticks = int(duration_s * TICKS_PER_SEC)
    in_ticks = int(fade_in_s * TICKS_PER_SEC)
    out_start = max(in_ticks, dur_ticks - int(fade_out_s * TICKS_PER_SEC))
    keyframes = [
        {"time": 0, "value": {"Float": 0.0}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        {"time": in_ticks, "value": {"Float": 100.0}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        {"time": out_start, "value": {"Float": 100.0}, "interp": "EaseIn", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
        {"time": dur_ticks, "value": {"Float": 0.0}, "interp": "EaseOut", "in_influence": 0.3333333333333333, "out_influence": 0.3333333333333333},
    ]
    return {
        "effect": "opacity",
        "enabled": True,
        "params": {
            "opacity": {"value": {"Float": 100.0}, "keyframes": keyframes},
            "blend": {"value": {"Choice": 0}},
        },
    }


def main():
    print("Reading project:", PROJECT_PATH)
    data = json.loads(PROJECT_PATH.read_text(encoding="utf-8"))
    proj = data["project"]
    items = proj["items"]
    seq = items["98"]["kind"]["Sequence"]
    next_id = data.get("next_id", 300)

    def find_or_add_audio_media(path: Path, dur_s: float = 180.0):
        nonlocal next_id
        target_id = None
        for k, v in items.items():
            if v.get("name") == path.name:
                target_id = int(k)
                break
        if target_id is None:
            target_id = next_id
            next_id += 1
            proj["root"]["children"].append({"Item": target_id})
        is_wav = path.suffix.lower() == ".wav"
        items[str(target_id)] = {
            "id": target_id,
            "name": path.name,
            "label": "Caribbean",
            "kind": {
                "Media": {
                    "media": {"File": {"path": str(path.resolve())}},
                    "info": {
                        "name": path.name,
                        "kind": "AudioOnly",
                        "duration": int(dur_s * TICKS_PER_SEC),
                        "audio_streams": [
                            {
                                "sample_rate": 48000 if is_wav else 44100,
                                "channels": 2,
                                "codec": "PCM" if is_wav else "MP3",
                                "bits_per_sample": 16 if is_wav else None,
                            }
                        ],
                        "container": "WAV" if is_wav else "MP3",
                        "start_timecode": None,
                        "file_size": path.stat().st_size,
                    },
                    "interpret": {"frame_rate": None, "par": None, "ignore_alpha": False, "invert_alpha": False},
                    "mark_in": None,
                    "mark_out": None,
                    "markers": [],
                    "offline": False,
                    "proxy": None,
                    "identity": {"size": path.stat().st_size, "fingerprint": hashlib.md5(path.name.encode()).hexdigest()[:16]},
                }
            },
            "metadata": {},
            "created": target_id,
        }
        return target_id

    def find_or_add_video_media(path: Path, width: int, height: int, dur_s: float):
        nonlocal next_id
        target_id = None
        for k, v in items.items():
            if v.get("name") == path.name:
                target_id = int(k)
                break
        if target_id is None:
            target_id = next_id
            next_id += 1
            proj["root"]["children"].append({"Item": target_id})
        items[str(target_id)] = {
            "id": target_id,
            "name": path.name,
            "label": "Iris",
            "kind": {
                "Media": {
                    "media": {"File": {"path": str(path.resolve())}},
                    "info": {
                        "name": path.name,
                        "kind": "Movie",
                        "duration": int(dur_s * TICKS_PER_SEC),
                        "video": {
                            "width": width,
                            "height": height,
                            "frame_rate": {"num": 30, "den": 1},
                            "par": [1, 1],
                            "codec": "H.264",
                            "pixel_format": "YUV 4:2:0 8-bit",
                            "color": {
                                "matrix": "Bt709",
                                "transfer": "Bt709",
                                "primaries": "Bt709",
                                "range": "Limited",
                            },
                            "has_alpha": False,
                            "bitrate": 726000,
                        },
                        "audio_streams": [{"sample_rate": 44100, "channels": 2, "codec": "AAC", "bits_per_sample": None}],
                        "container": "QuickTime",
                        "start_timecode": None,
                        "file_size": path.stat().st_size,
                    },
                    "interpret": {"frame_rate": None, "par": None, "ignore_alpha": False, "invert_alpha": False},
                    "mark_in": None,
                    "mark_out": None,
                    "markers": [],
                    "offline": False,
                    "proxy": None,
                    "identity": {"size": path.stat().st_size, "fingerprint": hashlib.md5(path.name.encode()).hexdigest()[:16]},
                }
            },
            "metadata": {},
            "created": target_id,
        }
        return target_id

    def find_or_add_still_overlay(path: Path, width: int = 3840, height: int = 2160):
        nonlocal next_id
        target_id = None
        for k, v in items.items():
            if v.get("name") == path.name:
                target_id = int(k)
                break
        if target_id is None:
            target_id = next_id
            next_id += 1
            proj["root"]["children"].append({"Item": target_id})
        items[str(target_id)] = {
            "id": target_id,
            "name": path.name,
            "label": "Lavender",
            "kind": {
                "Media": {
                    "media": {"File": {"path": str(path.resolve())}},
                    "info": {
                        "name": path.name,
                        "kind": "Still",
                        "duration": int(10.0 * TICKS_PER_SEC),
                        "video": {
                            "width": width,
                            "height": height,
                            "frame_rate": {"num": 30000, "den": 1001},
                            "par": [1, 1],
                            "codec": "PNG",
                            "pixel_format": "RGBA 8-bit",
                            "color": {
                                "matrix": "Bt709",
                                "transfer": "Srgb",
                                "primaries": "Bt709",
                                "range": "Full",
                            },
                            "has_alpha": True,
                            "bitrate": None,
                        },
                        "audio_streams": [],
                        "container": "Image",
                        "start_timecode": None,
                        "file_size": path.stat().st_size,
                    },
                    "interpret": {"frame_rate": None, "par": None, "ignore_alpha": False, "invert_alpha": False},
                    "mark_in": None,
                    "mark_out": None,
                    "markers": [],
                    "offline": False,
                    "proxy": None,
                    "identity": {"size": path.stat().st_size, "fingerprint": hashlib.md5(path.name.encode()).hexdigest()[:16]},
                }
            },
            "metadata": {},
            "created": target_id,
        }
        return target_id

    # 1. Generate 4K GPX Corner Map Widgets
    #    Note: All riding video clips on this loop are gentle flat escort spins (9.9 - 12.6 mph,
    #    ~1% smoothed grade, ~90-120W average power), so `show_telemetry_widget` is False across
    #    all clips on this flat loop (avoiding false 1-second sensor noise HUD popups).
    gpx_pts = load_gpx_stream(GPX_PATH)
    ov_dir = CATALOG_DIR / "overlays"
    ov_dir.mkdir(parents=True, exist_ok=True)

    map1_png = render_corner_map_widget(gpx_pts, 80, "Port d'Alcúdia Rollout", ov_dir / "map_01_rollout.png")
    map2_png = render_corner_map_widget(gpx_pts, 820, "Passing Ranxo Ses Roques", ov_dir / "map_02_ranxo.png")
    map3_png = render_corner_map_widget(gpx_pts, 1100, "Bellevue Zumba Courts", ov_dir / "map_03_bellevue.png")
    map4_png = render_corner_map_widget(gpx_pts, 4260, "Badia de Pollença Coast", ov_dir / "map_04_pollenca_bay.png")

    # 2. Build crisp 4K Picture-in-Picture B-Roll Clip (`zumba_bellevue_inset_4k.mp4`)
    #    combining the 4K IMG_7108.jpg Bellevue court backdrop (softly darkened + vignette)
    #    with a sharp 62% framed inset (2380x1338 with 6px warm white border + drop shadow)
    #    of Monday's actual `2026-11-02_Zumba.mp4` (192.5s -> 197.7s) so it sits cleanly on V1!
    zumba_inset_mp4 = RAW_DIR / "zumba_bellevue_inset_4k.mp4"
    court_bg_jpg = RAW_DIR / "IMG_7108.jpg"
    if not zumba_inset_mp4.exists():
        print("Generating 4K Picture-in-Picture B-roll clip:", zumba_inset_mp4)
        filter_complex = (
            "[0:v]scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
            "boxblur=16:2,eq=brightness=-0.12:saturation=0.90[bg];"
            "[1:v]scale=2368:1332:flags=lanczos,"
            "pad=2384:1348:8:8:color=white@0.95[fg];"
            "[bg][fg]overlay=(W-w)/2:(H-h)/2-40:shortest=1[vout]"
        )
        ff_cmd = [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-loop", "1", "-t", "5.2", "-i", str(court_bg_jpg),
            "-ss", "192.5", "-t", "5.2", "-i", str(ZUMBA_MP4),
            "-filter_complex", filter_complex,
            "-map", "[vout]", "-map", "1:a",
            "-r", "30",
            "-c:v", "libx264", "-preset", "fast", "-crf", "16", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
            str(zumba_inset_mp4),
        ]
        subprocess.run(ff_cmd, check=True, capture_output=True, text=True)
        print("Created:", zumba_inset_mp4)

    # Register Media Items
    p1_item_id = find_or_add_audio_media(BGM_PHASE1)
    p2_item_id = find_or_add_audio_media(BGM_PHASE2)
    zumba_item_id = find_or_add_video_media(zumba_inset_mp4, 3840, 2160, 5.2)

    def find_or_add_jpg_photo(path: Path, width: int = 4032, height: int = 3024):
        nonlocal next_id
        target_id = None
        for k, v in items.items():
            if v.get("name") == path.name:
                target_id = int(k)
                break
        if target_id is None:
            target_id = next_id
            next_id += 1
            proj["root"]["children"].append({"Item": target_id})
        items[str(target_id)] = {
            "id": target_id,
            "name": path.name,
            "label": "Lavender",
            "kind": {
                "Media": {
                    "media": {"File": {"path": str(path.resolve())}},
                    "info": {
                        "name": path.name,
                        "kind": "Still",
                        "duration": int(10.0 * TICKS_PER_SEC),
                        "video": {
                            "width": width,
                            "height": height,
                            "frame_rate": {"num": 30000, "den": 1001},
                            "par": [1, 1],
                            "codec": "JPG",
                            "pixel_format": "RGB 8-bit",
                            "color": {
                                "matrix": "Bt709",
                                "transfer": "Srgb",
                                "primaries": "Bt709",
                                "range": "Full",
                            },
                            "has_alpha": False,
                            "bitrate": None,
                        },
                        "audio_streams": [],
                        "container": "Image",
                        "start_timecode": None,
                        "file_size": path.stat().st_size,
                    },
                    "interpret": {"frame_rate": None, "par": None, "ignore_alpha": False, "invert_alpha": False},
                    "mark_in": None,
                    "mark_out": None,
                    "markers": [],
                    "offline": False,
                    "proxy": None,
                    "identity": {"size": path.stat().st_size, "fingerprint": hashlib.md5(path.name.encode()).hexdigest()[:16]},
                }
            },
            "metadata": {},
            "created": target_id,
        }
        return target_id

    for heic_name in ("IMG_8775.HEIC", "IMG_8777.HEIC"):
        heic_p = RAW_DIR / heic_name
        jpg_p = RAW_DIR / f"{Path(heic_name).stem}.jpg"
        if heic_p.exists() and not jpg_p.exists():
            subprocess.run(["/usr/bin/sips", "-s", "format", "jpeg", "-s", "formatOptions", "95", str(heic_p), "--out", str(jpg_p)], check=True, capture_output=True)

    pad_ground_id = find_or_add_jpg_photo(RAW_DIR / "IMG_8777.jpg", 4032, 3024)
    pad_caliper_id = find_or_add_jpg_photo(RAW_DIR / "IMG_8775.jpg", 4032, 3024)
    img_8741_id = find_or_add_jpg_photo(RAW_DIR / "IMG_8741.jpg", 8064, 6048)
    img_8744_id = find_or_add_jpg_photo(RAW_DIR / "IMG_8744.jpg", 4032, 3024)
    img_8746_id = find_or_add_jpg_photo(RAW_DIR / "IMG_8746.jpg", 8064, 6048)

    # 3. Update V1:
    #    - 28.3s..31.4s (3.1s): IMG_7108.jpg
    #    - 31.4s..36.6s (5.2s): zumba_bellevue_inset_4k.mp4
    #    - 36.6s..40.8s (4.2s): VIDEO_1793607120537.MP4 (source_in=52.5s)
    #    - 40.8s..46.2s (5.4s): VIDEO_1793607120537.MP4 (source_in=70.5s, Nina: "Что-то упало! — Что упало?")
    #    - 46.2s..49.8s (3.6s): IMG_8777.jpg (Blue Reynolds brake pad on the ground! Nina: "Вон! Это твоё упало синее!")
    #    - 49.8s..52.8s (3.0s): IMG_8775.jpg (Blue Reynolds brake pad seated back in the Dura-Ace caliper!)
    #    - 52.8s..55.6s (2.8s): IMG_8741.jpg (Pro Cycle Hire closed for winter)
    #    - 55.6s..58.6s (3.0s): IMG_8744.jpg (Badia de Pollença coast)
    #    - 58.6s..62.0s (3.4s): IMG_8746.jpg (Eroski haul in SJBC musette)
    v1 = seq["video_tracks"][0]
    new_v1_items = []
    inserted_zumba_v1 = False
    for it in v1["items"]:
        name = it.get("name", "")
        st = it.get("start", 0) / TICKS_PER_SEC
        if "YT_uRdZBJd4D_I" in name or name in (ZUMBA_MP4.name, zumba_inset_mp4.name, "IMG_8777.jpg", "IMG_8775.jpg", "IMG_8741.jpg", "IMG_8744.jpg", "IMG_8746.jpg"):
            continue
        if name == "IMG_7108.jpg":
            it["duration"] = int(3.1 * TICKS_PER_SEC)
            new_v1_items.append(it)
            zumba_v1_id = next_id; next_id += 1
            new_v1_items.append({
                "id": zumba_v1_id,
                "item": zumba_item_id,
                "name": zumba_inset_mp4.name,
                "label": "Iris",
                "start": int(31.4 * TICKS_PER_SEC),
                "duration": int(5.2 * TICKS_PER_SEC),
                "source_in": 0,
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
            inserted_zumba_v1 = True
            continue
        if st >= 40.0 and name == "VIDEO_1793607120537.MP4":
            it["start"] = int(40.8 * TICKS_PER_SEC)
            it["duration"] = int(5.4 * TICKS_PER_SEC)
            new_v1_items.append(it)
            continue
        new_v1_items.append(it)

    for photo_id, photo_name, st_s, dur_s in [
        (pad_ground_id, "IMG_8777.jpg", 46.2, 3.6),
        (pad_caliper_id, "IMG_8775.jpg", 49.8, 3.0),
        (img_8741_id, "IMG_8741.jpg", 52.8, 2.8),
        (img_8744_id, "IMG_8744.jpg", 55.6, 3.0),
        (img_8746_id, "IMG_8746.jpg", 58.6, 3.4),
    ]:
        cid = next_id; next_id += 1
        new_v1_items.append({
            "id": cid,
            "item": photo_id,
            "name": photo_name,
            "label": "Lavender",
            "start": int(st_s * TICKS_PER_SEC),
            "duration": int(dur_s * TICKS_PER_SEC),
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
            "scale_to_frame": True,
        })

    v1["items"] = new_v1_items
    print("Updated V1 with IMG_8777.jpg (pad on ground at 46.2s) and IMG_8775.jpg (pad in Dura-Ace caliper at 49.8s)!")

    # 4. Update A1:
    #    - Replace old spring flashback audio at 31.4s-36.6s with Monday's Zumba audio at -6.0 dB (not overpowering!)
    #    - Replace quiet raw BleeqUP gate dialog (36.6s-49.8s, raw -53dB) with speech-normalized `gate_dialog_boosted.wav` (0.0 dB)
    gate_wav = CATALOG_DIR / "gate_dialog_boosted.wav"
    if not gate_wav.exists():
        raw_gate_vid = RAW_DIR / "VIDEO_1793607120537.MP4"
        fc_gate = (
            "[0:a]atrim=52.5:56.7,asetpts=PTS-STARTPTS,highpass=f=120,lowpass=f=7500,volume=16dB,dynaudnorm=f=150:g=11:p=0.92:m=10.0,afade=t=in:st=0:d=0.25[g1];"
            "[0:a]atrim=70.5:79.5,asetpts=PTS-STARTPTS,highpass=f=120,lowpass=f=7500,volume=22dB,dynaudnorm=f=150:g=11:p=0.92:m=12.0,afade=t=out:st=8.6:d=0.4[g2];"
            "[g1][g2]concat=n=2:v=0:a=1,alimiter=limit=0.92[gout]"
        )
        subprocess.run(
            ["/opt/homebrew/bin/ffmpeg", "-y", "-i", str(raw_gate_vid), "-filter_complex", fc_gate, "-map", "[gout]", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(gate_wav)],
            check=True, capture_output=True,
        )
    gate_media_id = find_or_add_audio_media(gate_wav, 13.2)

    new_a1_items = []
    inserted_zumba_a1 = False
    inserted_gate_a1 = False
    for it in seq["audio_tracks"][0]["items"]:
        name = it.get("name", "")
        st = it.get("start", 0) / TICKS_PER_SEC
        if "YT_uRdZBJd4D_I" in name or name in (ZUMBA_MP4.name, zumba_inset_mp4.name):
            zumba_a_id = next_id; next_id += 1
            new_a1_items.append({
                "id": zumba_a_id,
                "item": zumba_item_id,
                "name": zumba_inset_mp4.name,
                "label": "Iris",
                "start": int(31.4 * TICKS_PER_SEC),
                "duration": int(5.2 * TICKS_PER_SEC),
                "source_in": 0,
                "speed": 1.0,
                "reverse": False,
                "enabled": True,
                "link": None,
                "group": None,
                "effects": make_volume_effect(fade_in_s=0.6, fade_out_s=0.6, duration_s=5.2),
                "markers": [],
                "gain_db": -6.0,
                "frame_hold": None,
                "scale_to_frame": False,
            })
            inserted_zumba_a1 = True
            continue
        if st >= 36.0:
            if not inserted_gate_a1:
                gate_clip_id = next_id; next_id += 1
                new_a1_items.append({
                    "id": gate_clip_id,
                    "item": gate_media_id,
                    "name": gate_wav.name,
                    "label": "Caribbean",
                    "start": int(36.6 * TICKS_PER_SEC),
                    "duration": int(13.2 * TICKS_PER_SEC),
                    "source_in": 0,
                    "speed": 1.0,
                    "reverse": False,
                    "enabled": True,
                    "link": None,
                    "group": None,
                    "effects": make_volume_effect(fade_in_s=0.2, fade_out_s=0.35, duration_s=13.2),
                    "markers": [],
                    "gain_db": 1.0,
                    "frame_hold": None,
                    "scale_to_frame": False,
                })
                inserted_gate_a1 = True
            continue
        it["gain_db"] = -6.0
        new_a1_items.append(it)
    seq["audio_tracks"][0]["items"] = new_a1_items

    # 5. Update A2 Music:
    #    - Phase 1a (0.0s -> 31.4s): EasyPeasy (-6.5 dB, warm and clearly audible!)
    #    - 31.4s -> 36.6s: Zumba live music plays on A1 at -6.0 dB
    #    - 36.6s -> 49.8s: Boosted live gate dialog with Nina on A1 (+1.0 dB on normalized speech)
    #    - Phase 2 (49.8s -> 62.0s): OceanDrive (-7.0 dB, warm coastal groove!)
    p1_clip_id = next_id; next_id += 1
    p2_clip_id = next_id; next_id += 1
    seq["audio_tracks"][1]["items"] = [
        {
            "id": p1_clip_id,
            "item": p1_item_id,
            "name": BGM_PHASE1.name,
            "label": "Caribbean",
            "start": 0,
            "duration": int(31.4 * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": make_volume_effect(fade_in_s=1.2, fade_out_s=0.8, duration_s=31.4),
            "markers": [],
            "gain_db": -6.5,
            "frame_hold": None,
            "scale_to_frame": False,
        },
        {
            "id": p2_clip_id,
            "item": p2_item_id,
            "name": BGM_PHASE2.name,
            "label": "Caribbean",
            "start": int(49.8 * TICKS_PER_SEC),
            "duration": int(12.2 * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": make_volume_effect(fade_in_s=0.8, fade_out_s=2.2, duration_s=12.2),
            "markers": [],
            "gain_db": -7.0,
            "frame_hold": None,
            "scale_to_frame": False,
        },
    ]

    # 5a. Clean up Audio 3 (SFX): remove drop_fall_01 & error_01 (which stepped over Nina's "Что-то упало!")
    #     and soften camera shutter clicks to -10 dB.
    if len(seq["audio_tracks"]) >= 3:
        cleaned_sfx = []
        for sfx in seq["audio_tracks"][2].get("items", []):
            sname = sfx.get("name", "")
            if sname in ("drop_fall_01.wav", "error_01.wav"):
                continue
            sfx["gain_db"] = -10.0
            cleaned_sfx.append(sfx)
        seq["audio_tracks"][2]["items"] = cleaned_sfx

    # 5b. Add Track A4 (Voiceover) with Alexander's warm scene-synced narration (`voiceover_en_part1.wav` + `voiceover_en_part2.wav`)
    def probe_wav_duration(wav_path: Path) -> float:
        out = subprocess.check_output(
            ["/opt/homebrew/bin/ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(wav_path)],
            text=True,
        ).strip()
        return float(out)

    vo_items = []
    vo_p1 = CATALOG_DIR / "voiceover_en_part1.wav"
    vo_p2 = CATALOG_DIR / "voiceover_en_part2.wav"
    for vo_wav, start_sec, max_dur in [(vo_p1, 1.8, 26.5), (vo_p2, 50.0, 11.5)]:
        if vo_wav.exists():
            dur_s = min(probe_wav_duration(vo_wav), max_dur)
            vo_media_id = find_or_add_audio_media(vo_wav, dur_s)
            vo_clip_id = next_id; next_id += 1
            vo_items.append({
                "id": vo_clip_id,
                "item": vo_media_id,
                "name": vo_wav.name,
                "label": "Mango",
                "start": int(start_sec * TICKS_PER_SEC),
                "duration": int(dur_s * TICKS_PER_SEC),
                "source_in": 0,
                "speed": 1.0,
                "reverse": False,
                "enabled": True,
                "link": None,
                "group": None,
                "effects": make_volume_effect(fade_in_s=0.15, fade_out_s=0.25, duration_s=dur_s),
                "markers": [],
                "gain_db": -0.5,
                "frame_hold": None,
                "scale_to_frame": False,
            })

    if len(seq["audio_tracks"]) < 4:
        a4_track_id = next_id; next_id += 1
        seq["audio_tracks"].append({
            "id": a4_track_id,
            "kind": "Audio",
            "name": "Voiceover",
            "items": vo_items,
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
        })
    else:
        seq["audio_tracks"][3]["name"] = "Voiceover"
        seq["audio_tracks"][3]["items"] = vo_items
    print(f"Populated Audio 4 (Voiceover) with {len(vo_items)} warm narration segments")

    # 6. Upgrade V1 clips to 4K Ken Burns / centered motion
    seq_w, seq_h = 3840, 2160
    seq["settings"]["width"] = seq_w
    seq["settings"]["height"] = seq_h
    seq["settings"]["preset"] = "3840x2160 30"

    still_zoom_toggle = True
    for it in v1["items"]:
        it["scale_to_frame"] = True
        dur_s = it["duration"] / TICKS_PER_SEC
        name = it.get("name", "")
        media_id = str(it["item"])
        vinfo = items.get(media_id, {}).get("kind", {}).get("Media", {}).get("info", {}).get("video") or {}
        src_w = vinfo.get("width", 1920)
        src_h = vinfo.get("height", 1080)
        if name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
            effects = [e for e in it.get("effects", []) if e.get("effect") != "motion"]
            effects.insert(0, make_motion_ken_burns(dur_s, src_w, src_h, seq_w, seq_h, zoom_in=still_zoom_toggle))
            still_zoom_toggle = not still_zoom_toggle
            it["effects"] = effects
        else:
            for eff in it.get("effects", []):
                if eff.get("effect") == "motion":
                    eff["params"]["position"] = {"value": {"Vec2": {"x": seq_w / 2.0, "y": seq_h / 2.0}}}
                    eff["params"]["anchor"] = {"value": {"Vec2": {"x": src_w / 2.0, "y": src_h / 2.0}}}
                    eff["params"]["scale"] = {"value": {"Float": 100.0}}

    # 7. Populate V2 with:
    #    - GPX Corner Route Map Widgets (top-right, 3.5s at key scene starts)
    #    - Dynamic GPX Telemetry HUD Overlays (top-left, during notable power/grade video clips)
    #    - Monday's 2026-11-02_Zumba.mp4 B-roll inset (31.4s -> 36.6s, 62% scale at x=1920, y=1120)
    v2_items = []

    def add_png_overlay_to_v2(png_path: Path, start_s: float, dur_s: float):
        nonlocal next_id
        m_id = find_or_add_still_overlay(png_path, 3840, 2160)
        c_id = next_id; next_id += 1
        v2_items.append({
            "id": c_id,
            "item": m_id,
            "name": png_path.name,
            "label": "Lavender",
            "start": int(start_s * TICKS_PER_SEC),
            "duration": int(dur_s * TICKS_PER_SEC),
            "source_in": 0,
            "speed": 1.0,
            "reverse": False,
            "enabled": True,
            "link": None,
            "group": None,
            "effects": [
                make_static_motion(3840, 2160, 1920.0, 1080.0, 100.0),
                make_opacity_in_out(dur_s, 0.35, 0.45),
            ],
            "markers": [],
            "gain_db": 0.0,
            "frame_hold": None,
            "scale_to_frame": True,
        })

    # Scene corner maps on V2 (no false telemetry HUDs on this flat escort spin)
    add_png_overlay_to_v2(map1_png, 3.1, 3.5)
    add_png_overlay_to_v2(map2_png, 11.5, 3.5)
    add_png_overlay_to_v2(map3_png, 24.1, 3.5)
    add_png_overlay_to_v2(map4_png, 52.8, 3.5)

    v2_items.sort(key=lambda x: x["start"])
    seq["video_tracks"][1]["items"] = v2_items
    seq["video_tracks"][1]["transitions"] = []
    print(f"Populated V2 with {len(v2_items)} items (4 GPX Corner Maps; 0 telemetry HUDs since all video clips are flat easy spins)")

    # 8. Native Dip-to-Black on final clip of V1
    last_clip = v1["items"][-1]
    last_end_ticks = last_clip["start"] + last_clip["duration"]
    fade_ticks = int(1.5 * TICKS_PER_SEC)
    trans_id = next_id; next_id += 1
    v1["transitions"] = [
        {
            "id": trans_id,
            "effect": {"effect": "dip_to_black", "enabled": True, "params": {}},
            "start": last_end_ticks - fade_ticks,
            "duration": fade_ticks,
            "from": last_clip["id"],
            "to": None,
            "align": "EndAtCut",
            "reverse": False,
        }
    ]

    # 9. Update Caption Track (C1) with Imperial units
    caption_items = []
    cap_track_id = next_id; next_id += 1
    for st_s, dur_s, text in CAPTIONS:
        cap_id = next_id; next_id += 1
        caption_items.append({
            "id": cap_id,
            "start": int(st_s * TICKS_PER_SEC),
            "duration": int(dur_s * TICKS_PER_SEC),
            "text": text,
            "speaker": None,
            "cue_id": None,
            "settings": "",
        })

    seq["caption_tracks"] = [
        {
            "id": cap_track_id,
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
            "captions": caption_items,
            "vtt_blocks": [],
        }
    ]

    data["next_id"] = next_id
    PROJECT_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Saved upgraded {PROJECT_PATH.name} (burnCaptions=False, Audio 4 Voiceover enabled)!")

    # 10. Build broadcast-balanced stereo audio mixes for EN, RU, and UA
    for lang in ("en", "ru", "ua"):
        p1 = CATALOG_DIR / f"voiceover_{lang}_part1.wav"
        p2 = CATALOG_DIR / f"voiceover_{lang}_part2.wav"
        out_wav = CATALOG_DIR / f"full_audio_{lang}.wav"
        out_m4a = CATALOG_DIR / f"full_audio_{lang}.m4a"
        # Mix:
        # [0:a] BGM_PHASE1 (0..31.4s): -7.5 dB under VO (0..13s), swelling +3.5 dB (-4.0 dB) during 13..31.4s riding!
        # [1:a] zumba_inset_mp4 (31.4..36.6s): -6.5 dB (smooth 0.6s fade-in/out, not overpowering!)
        # [2:a] gate_wav (36.6..49.8s): +1.0 dB (speech-normalized live dialog with Nina!)
        # [3:a] BGM_PHASE2 (49.8..62.02s): -7.5 dB under VO, swelling +2.5 dB for final 1.8s!
        # [4:a] VO part 1 (at 1800ms): -0.5 dB
        # [5:a] VO part 2 (at 50000ms): -0.5 dB
        fc_mix = (
            "[0:a]atrim=0:31.4,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=1.2,afade=t=out:st=30.6:d=0.8,"
            "volume=-7.5dB,volume=enable='between(t,13.0,30.6)':volume=3.5dB[m1];"
            "[1:a]atrim=0:5.2,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.6,afade=t=out:st=4.6:d=0.6,"
            "volume=-6.5dB,adelay=31400|31400[zumba];"
            "[2:a]atrim=0:13.2,asetpts=PTS-STARTPTS,volume=1.0dB,adelay=36600|36600[gate];"
            "[3:a]atrim=0:12.22,asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.8,afade=t=out:st=10.0:d=2.22,"
            "volume=-7.5dB,adelay=49800|49800[m2];"
            "[4:a]volume=-0.5dB,adelay=1800|1800[v1];"
            "[5:a]volume=-0.5dB,adelay=50000|50000[v2];"
            "[m1][zumba][gate][m2][v1][v2]amix=inputs=6:duration=longest:dropout_transition=0:normalize=0,"
            "alimiter=limit=0.95[aout]"
        )
        subprocess.run(
            [
                "/opt/homebrew/bin/ffmpeg", "-y",
                "-i", str(BGM_PHASE1),
                "-i", str(zumba_inset_mp4),
                "-i", str(gate_wav),
                "-i", str(BGM_PHASE2),
                "-i", str(p1),
                "-i", str(p2),
                "-filter_complex", fc_mix, "-map", "[aout]",
                "-t", "62.02", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(out_wav),
            ],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["/opt/homebrew/bin/ffmpeg", "-y", "-i", str(out_wav), "-c:a", "aac", "-b:a", "256k", str(out_m4a)],
            check=True, capture_output=True,
        )
        print(f"Built balanced stereo mix: {out_m4a.name}")

    if "--remux-audio-only" not in sys.argv or not EXPORT_PATH.exists():
        print(f"Exporting 4K UHD master -> {EXPORT_PATH}...")
        cmd = [
            "/opt/homebrew/bin/filmcraft-cli",
            "--project", str(PROJECT_PATH),
            "export", str(EXPORT_PATH),
            "--preset", "Match Source – Adaptive High Bitrate",
            "--settings", '{"burnCaptions": false}',
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        print("Render Output:", res.stdout.strip())

    tmp_en = EXPORT_PATH.with_suffix(".tmp_en.mp4")
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-i", str(EXPORT_PATH), "-i", str(CATALOG_DIR / "full_audio_en.m4a"),
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", str(tmp_en),
        ],
        check=True, capture_output=True,
    )
    tmp_en.replace(EXPORT_PATH)
    print(f"Remuxed balanced EN audio -> {EXPORT_PATH}")

    for lang, suf in [("ru", "_RU"), ("ua", "_UA")]:
        out_mp4 = EXPORT_PATH.with_name(f"{EXPORT_PATH.stem}{suf}.mp4")
        subprocess.run(
            [
                "/opt/homebrew/bin/ffmpeg", "-y",
                "-i", str(EXPORT_PATH), "-i", str(CATALOG_DIR / f"full_audio_{lang}.m4a"),
                "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "copy", str(out_mp4),
            ],
            check=True, capture_output=True,
        )
        print(f"Remuxed balanced {lang.upper()} 4K edition -> {out_mp4}")


if __name__ == "__main__":
    main()
