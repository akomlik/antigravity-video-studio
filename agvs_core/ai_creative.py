"""
agvs_core/ai_creative.py
Native Gemini AI Creative Artifact Engine (paint_morph, fpv_drone, living_memory)
and Long-Clip Contact-Strip Semantic Subclip & Landmark Analyzer.
Zero third-party BleeqUP app dependency and zero plugin sys.path hacks.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from PIL import Image

from agvs_core.config import find_binary, get_studio_root

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None  # type: ignore[assignment]
    types = None  # type: ignore[assignment]

VIDEO_MODEL = "gemini-omni-1.2-flash"
IMAGE_MODEL = "gemini-3-pro-image"
VISION_MODEL = "gemini-4-carbon"
FALLBACK_VISION_MODEL = "gemini-3.8-flash"

STYLE_PROMPTS: dict[str, str] = {
    "impasto_oil": (
        "Transform this exact photograph into a museum-grade Mediterranean palette-knife impasto oil painting "
        "on canvas. Preserve the exact road geometry, horizon line, sky features, and subject placement so it "
        "can seamlessly morph back into the original photograph, with thick expressive textured brushstrokes "
        "and vibrant warm Mediterranean colors."
    ),
    "watercolor": (
        "Transform this exact photograph into a luminous architectural Mediterranean watercolor and ink wash "
        "illustration on textured cold-press paper. Preserve the exact composition, road geometry, and horizon "
        "line so it aligns frame-accurately with the original image."
    ),
    "anime": (
        "Transform this exact photograph into a Makoto Shinkai / Studio Ghibli style hand-painted coastal anime "
        "background illustration with luminous clouds, shimmering Mediterranean light, and crisp road details, "
        "preserving the exact perspective and subject placement."
    ),
}


def _generate_vision_content(client: Any, contents: list[Any], json_mode: bool = False) -> Any:
    """Calls Gemini 4 Carbon Vision first, falling back cleanly to Gemini 3.8 Flash if needed."""
    cfg = types.GenerateContentConfig(response_mime_type="application/json") if (json_mode and types) else None
    for model_id in (VISION_MODEL, FALLBACK_VISION_MODEL):
        try:
            return client.models.generate_content(model=model_id, contents=contents, config=cfg)
        except Exception as exc:
            if model_id == FALLBACK_VISION_MODEL:
                raise exc
    raise RuntimeError("Vision generation failed across configured models.")


def resolve_or_upload_asset(client: Any, asset_ref: str, default_mime: str = "image/jpeg") -> tuple[str, str]:
    """Uploads a local file via Gemini File API (polling until ACTIVE) or passes through an existing URI."""
    if asset_ref.startswith(("https://", "http://", "gs://", "files/")):
        return asset_ref, default_mime
    path = Path(asset_ref).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Asset file not found: {path}")
    guessed_mime, _ = mimetypes.guess_type(str(path))
    mime_type = guessed_mime or default_mime
    uploaded = client.files.upload(file=str(path))
    for _ in range(45):
        state = getattr(uploaded, "state", None)
        state_name = getattr(state, "name", str(state or "")).upper()
        if not state_name or "ACTIVE" in state_name:
            break
        if "FAILED" in state_name:
            raise RuntimeError(f"Gemini File API processing failed for {path.name}: {state_name}")
        time.sleep(2.0)
        uploaded = client.files.get(name=uploaded.name)
    uri = getattr(uploaded, "uri", None) or getattr(uploaded, "name", "")
    return str(uri), str(getattr(uploaded, "mime_type", None) or mime_type)


def extract_16x9_frame(source_path: Path, out_jpg: Path, timestamp_sec: float = 1.0) -> Path:
    """Extracts or center-crops a clean 1920x1080 (16:9) JPEG frame from a video or image."""
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = find_binary("ffmpeg")
    ext = source_path.suffix.lower()
    if ext in {".mp4", ".mov", ".m4v"}:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss",
            f"{timestamp_sec:.2f}",
            "-i",
            str(source_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-update",
            "1",
            "-q:v",
            "2",
            str(out_jpg),
        ]
    else:
        cmd = [
            ffmpeg_bin,
            "-y",
            "-i",
            str(source_path),
            "-vf",
            "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-update",
            "1",
            "-q:v",
            "2",
            str(out_jpg),
        ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_jpg


def describe_ride_kit_and_bike(client: Any, ref_images: list[Path], cache_file: Path) -> str:
    """Dynamically inspects that day's rider+bike reference photo(s) so nothing is ever hardcoded."""
    if cache_file.exists():
        return cache_file.read_text(encoding="utf-8").strip()
    imgs = [Image.open(p) for p in ref_images if p.exists()]
    if not imgs:
        return "the exact cyclist and road bicycle shown in the reference photo"
    prompt = (
        "Describe this cyclist and their bicycle in one concise, highly specific visual sentence for an image/video "
        "generator prompt. Include only positive visible attributes: helmet color/style (and cap underneath if visible), "
        "sunglasses color, jersey color/text/pattern, bib shorts color/trim, socks and cycling shoe color/brand, "
        "and the exact bicycle frame color, top-tube/fork accent colors, brand logo, wheel color, and any under-saddle "
        "rear mudguard/fender. Return ONLY the descriptive noun phrase starting with 'a fit male road cyclist wearing...'."
    )
    resp = _generate_vision_content(client, [*imgs, prompt], json_mode=False)
    spec = (resp.text or "").strip()
    if spec:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(spec, encoding="utf-8")
        print(f"Auto-detected ride kit & bike spec from reference photo: {spec}")
        return spec
    return "the exact cyclist and road bicycle shown in the reference photo"


def generate_stylized_frame(
    client: Any,
    real_frame_jpg: Path,
    out_stylized_jpg: Path,
    style: str,
    custom_prompt: Optional[str] = None,
) -> Path:
    """Uses Gemini 3 Pro Image to synthesize a 16:9 artistic twin."""
    prompt = custom_prompt or STYLE_PROMPTS.get(style, STYLE_PROMPTS["impasto_oil"])
    img = Image.open(real_frame_jpg)
    print(f"Synthesizing native '{style}' keyframe via {IMAGE_MODEL}...")
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=[img, prompt],
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
        ),
    )
    for part in response.parts:
        if part.inline_data:
            gen_img = part.as_image()
            out_stylized_jpg.parent.mkdir(parents=True, exist_ok=True)
            gen_img.save(str(out_stylized_jpg))
            extract_16x9_frame(out_stylized_jpg, out_stylized_jpg)
            print(f"Saved synthesized keyframe: {out_stylized_jpg}")
            return out_stylized_jpg
    raise RuntimeError(f"No image returned by {IMAGE_MODEL}")


def synthesize_viewpoint_keyframe(
    client: Any,
    road_frame_jpg: Path,
    ref_images: list[Path],
    rider_bike_spec: str,
    viewpoint_instruction: str,
    out_jpg: Path,
) -> Path:
    """Uses Gemini 3 Pro Image with road frame + ride-specific reference photo(s) to create an exact 16:9 keyframe."""
    contents: list[Any] = [Image.open(road_frame_jpg)]
    for ref_p in ref_images:
        if ref_p and ref_p.exists():
            contents.append(Image.open(ref_p))
    full_prompt = (
        f"Image 1 is the exact road, camera heading, and environment. The remaining image(s) are exact visual "
        f"references from today's ride showing {rider_bike_spec}. "
        f"{viewpoint_instruction} "
        f"CRITICAL DIRECTION OF TRAVEL RULE: The cyclist MUST ride in the exact same geographic travel direction "
        f"as the forward camera heading and any other cyclists in Image 1 (heading toward the landmarks/mountains "
        f"in the distance of Image 1, NEVER turned 180 degrees riding the wrong way against the flow of Image 1!). "
        f"CRITICAL VISUAL LOCK: Preserve the exact bicycle frame color, brand decals, accessories, and the rider's "
        f"exact helmet, glasses, jersey, shorts, and shoes from the reference photo(s)."
    )
    contents.append(full_prompt)
    print(f"Synthesizing viewpoint keyframe ({out_jpg.name}) via {IMAGE_MODEL}...")
    response = client.models.generate_content(
        model=IMAGE_MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="16:9", image_size="2K"),
        ),
    )
    for part in response.parts:
        if part.inline_data:
            gen_img = part.as_image()
            out_jpg.parent.mkdir(parents=True, exist_ok=True)
            gen_img.save(str(out_jpg))
            extract_16x9_frame(out_jpg, out_jpg)
            print(f"Saved viewpoint keyframe: {out_jpg}")
            return out_jpg
    raise RuntimeError(f"No keyframe returned by {IMAGE_MODEL}")


def run_omni_video(
    client: Any,
    prompt: str,
    output_mp4: Path,
    first_frame: Optional[Path] = None,
    last_frame: Optional[Path] = None,
    ref_images: Optional[list[Path]] = None,
    duration: int = 5,
    resolution: str = "1080p",
) -> Path:
    """Runs Gemini Omni 1.2 Flash background video synthesis via native File API anchoring."""
    input_parts: list[dict[str, Any]] = []
    img_idx = 1
    sources_decl: list[str] = []
    refs_decl: list[str] = []

    if first_frame:
        f1_uri, f1_mime = resolve_or_upload_asset(client, str(first_frame), "image/jpeg")
        input_parts.append({"type": "image", "uri": f1_uri, "mime_type": f1_mime})
        sources_decl.append(f"<FIRST_FRAME>@Image{img_idx}")
        img_idx += 1

    if last_frame:
        f2_uri, f2_mime = resolve_or_upload_asset(client, str(last_frame), "image/jpeg")
        input_parts.append({"type": "image", "uri": f2_uri, "mime_type": f2_mime})
        sources_decl.append(f"<LAST_FRAME>@Image{img_idx}")
        img_idx += 1

    valid_refs = [r for r in (ref_images or []) if r and r.exists()]
    for r_i, ref_p in enumerate(valid_refs):
        r_uri, r_mime = resolve_or_upload_asset(client, str(ref_p), "image/jpeg")
        input_parts.append({"type": "image", "uri": r_uri, "mime_type": r_mime})
        refs_decl.append(f"<IMAGE_REF_{r_i}>@Image{img_idx}")
        img_idx += 1

    prefix_blocks: list[str] = []
    if sources_decl:
        prefix_blocks.append(f"[# Sources {' '.join(sources_decl)}]")
    if refs_decl:
        prefix_blocks.append(f"[# References {' '.join(refs_decl)}]")

    prompt_text = f"{' '.join(prefix_blocks)} {prompt}".strip()
    input_parts.append({"type": "text", "text": prompt_text})

    video_config = {
        "type": "video",
        "delivery": "uri",
        "aspect_ratio": "16:9",
        "duration": f"{duration}s",
        "resolution": resolution,
    }

    print(f"Launching {VIDEO_MODEL} ({resolution}, {duration}s) -> {output_mp4.name} ...")
    interaction = client.interactions.create(
        model=VIDEO_MODEL,
        input=input_parts,
        response_format=video_config,
        background=True,
    )
    while True:
        interaction = client.interactions.get(interaction.id)
        if interaction.status == "completed":
            break
        if interaction.status in ("failed", "cancelled"):
            raise RuntimeError(f"Video generation {interaction.status}: {getattr(interaction, 'error', '')}")
        time.sleep(8)

    output_video = getattr(interaction, "output_video", None)
    if output_video:
        if getattr(output_video, "data", None):
            raw = output_video.data
            video_bytes = base64.b64decode(raw) if isinstance(raw, str) else raw
            output_mp4.parent.mkdir(parents=True, exist_ok=True)
            output_mp4.write_bytes(video_bytes)
            return output_mp4
        if getattr(output_video, "uri", None):
            video_bytes = client.files.download(file=output_video.uri)
            output_mp4.parent.mkdir(parents=True, exist_ok=True)
            output_mp4.write_bytes(video_bytes)
            return output_mp4
    raise RuntimeError("No video output returned.")


# --- Contact-Strip Long-Clip Subclip & Landmark Analyzer ---

def analyze_clip_strip(strip_path: Path, duration_s: float, client: Any) -> dict[str, Any]:
    """Extracts structured sub-events and landmarks from a 6-frame contact strip."""
    cache_path = strip_path.parent / f"{strip_path.stem.replace('_strip', '')}_subclips.json"
    if cache_path.exists():
        try:
            cached = json.loads(cache_path.read_text(encoding="utf-8"))
            if "sub_events" in cached:
                return cached
        except Exception:
            pass

    if client is None or not strip_path.exists():
        return {}

    img = Image.open(strip_path)
    prompt = f"""
This is a 3x2 contact sheet showing 6 evenly spaced frames across a {duration_s:.1f}-second cycling video clip:
- Frame 1 (top-left): ~{duration_s * 0.05:.1f}s
- Frame 2 (top-center): ~{duration_s * 0.23:.1f}s
- Frame 3 (top-right): ~{duration_s * 0.42:.1f}s
- Frame 4 (bottom-left): ~{duration_s * 0.60:.1f}s
- Frame 5 (bottom-center): ~{duration_s * 0.78:.1f}s
- Frame 6 (bottom-right): ~{duration_s * 0.95:.1f}s

Analyze these 6 frames carefully and return ONLY valid JSON matching this schema:
{{
  "sub_events": [
    {{"segment": [start_s, end_s], "description": "concise description of action/setting"}}
  ],
  "landmarks": [
    {{"name": "Landmark Name", "type": "hotel|restaurant|sign|ruin|vista", "timestamp_range": [start_s, end_s], "details": "visible features"}}
  ]
}}
"""
    for attempt in range(1, 4):
        try:
            resp = _generate_vision_content(client, [img, prompt], json_mode=True)
            data = json.loads((resp.text or "{}").strip())
            cache_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
            return data
        except Exception as exc:
            if attempt < 3:
                time.sleep(3.0 * attempt)
            else:
                print(f"Warning: Failed to analyze strip {strip_path.name}: {exc}", file=sys.stderr)
    return {}


def update_storyboard_media_log(project_dir: Path, media_items: list[dict[str, Any]], studio_root: Optional[Path] = None) -> None:
    """Enriches Section 3 of Storyboard.md with canonical `subclips` and `landmarks`."""
    storyboard_path = project_dir / "Storyboard.md"
    if not storyboard_path.exists():
        return

    text = storyboard_path.read_text(encoding="utf-8")
    m = re.search(r"(## 3\.\s*Chronological Media & GPS Log[^\n]*\n)", text)
    if not m:
        return

    log_lines: list[str] = []
    for item in media_items:
        fname = item.get("filename", "")
        dur = item.get("duration_s", 0.0)
        gps_str = f" (GPS: {item.get('qt_lat')}, {item.get('qt_lon')})" if item.get("qt_lat") else ""
        dur_str = f" [{dur}s]" if item.get("media_type") == "video" else " [Still]"
        log_lines.append(f"- `{fname}` — `{item.get('creation_time_utc', '')}`{dur_str}{gps_str}")

        for lm in item.get("landmarks", []):
            t_rng = lm.get("timestamp_range", [])
            rng_str = f"{t_rng[0]:.1f}s - {t_rng[1]:.1f}s" if len(t_rng) == 2 else ""
            log_lines.append(f"  * **[KEY LANDMARK]** `{lm.get('name')}` ({lm.get('type')}) at `{rng_str}`: {lm.get('details', '')}")

        for sc in item.get("subclips") or item.get("sub_clips") or []:
            seg = sc.get("segment", [])
            seg_str = f"{seg[0]:.1f}s - {seg[1]:.1f}s" if len(seg) == 2 else ""
            log_lines.append(f"  * `{seg_str}`: {sc.get('description')}")

    sec4_match = re.search(r"(\n## 4\.\s*Multi-Language Voice-Over)", text)
    if sec4_match:
        new_text = text[: m.end()] + "\n" + "\n".join(log_lines) + "\n" + text[sec4_match.start() :]
    else:
        new_text = text[: m.end()] + "\n" + "\n".join(log_lines) + "\n"

    storyboard_path.write_text(new_text, encoding="utf-8")
    root = studio_root or get_studio_root()
    for p in (root / "04_Project_Catalog").glob(f"*/{project_dir.name}/Storyboard.md"):
        p.write_text(new_text, encoding="utf-8")


def process_project_subclips(project_dir: Path, force: bool = False, studio_root: Optional[Path] = None) -> bool:
    """Processes all video contact strips >= 12.0s in project_dir and updates canonical `subclips` in manifest."""
    root = studio_root or get_studio_root()
    manifest_path = project_dir / "project_manifest.json"
    proxy_dir = project_dir / ".proxies"
    if not manifest_path.exists() or not proxy_dir.exists():
        return False

    if not genai or not os.environ.get("GEMINI_API_KEY"):
        print("Note: GEMINI_API_KEY not set or google-genai not installed. Skipping vision subclip analysis.", file=sys.stderr)
        return False

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    client = genai.Client()
    media_items = manifest.get("media_inventory") or manifest.get("media_items", [])
    updated = False

    for item in media_items:
        if item.get("media_type") != "video" or float(item.get("duration_s") or 0.0) < 12.0:
            continue
        dur = float(item["duration_s"])
        stem = Path(str(item.get("filename", ""))).stem
        strip_path = proxy_dir / f"{stem}_strip.jpg"
        if not strip_path.exists():
            continue
        cache_path = proxy_dir / f"{stem}_subclips.json"
        if not force and cache_path.exists() and (item.get("subclips") or item.get("sub_clips")):
            if "sub_clips" in item and "subclips" not in item:
                item["subclips"] = item.pop("sub_clips")
                updated = True
            continue

        res = analyze_clip_strip(strip_path, dur, client)
        if res:
            item.pop("sub_clips", None)
            item["subclips"] = res.get("sub_events", [])
            item["landmarks"] = res.get("landmarks", [])
            updated = True

    if updated:
        serialized = json.dumps(manifest, indent=2, ensure_ascii=False)
        manifest_path.write_text(serialized, encoding="utf-8")
        for p in (root / "04_Project_Catalog").glob(f"*/{project_dir.name}/project_manifest.json"):
            if p.resolve() != manifest_path.resolve():
                p.write_text(serialized, encoding="utf-8")
        update_storyboard_media_log(project_dir, media_items, studio_root=root)
    return updated


def ai_creative_cli_main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Native Studio AI Creative Artifact Generator (Zero BleeqUP Dependency)")
    parser.add_argument("--mode", required=True, choices=["paint_morph", "fpv_drone", "living_memory"])
    parser.add_argument("--source", required=True, help="Source photo or video clip path")
    parser.add_argument("--timestamp", type=float, default=1.0, help="Timestamp in seconds if source is video")
    parser.add_argument("--style", default="impasto_oil", choices=["impasto_oil", "watercolor", "anime"])
    parser.add_argument("--reverse-morph", action="store_true", help="Morph Reality -> Painting (for film outro)")
    parser.add_argument(
        "--viewpoint",
        default="crane_above_to_behind",
        choices=["crane_above_to_behind", "side_tracking", "low_rear_chase", "front_lead", "custom"],
    )
    parser.add_argument("--rider-ref", nargs="+", help="Ride-specific photo(s) or video clip of the rider with bike")
    parser.add_argument("--rider-ref-timestamp", type=float, default=11.2)
    parser.add_argument("--prompt", help="Optional custom motion/viewpoint prompt")
    parser.add_argument("--force-keyframes", action="store_true")
    parser.add_argument("--keyframes-only", action="store_true")
    parser.add_argument("--duration", type=int, default=5)
    parser.add_argument("--output", required=True, help="Output MP4 file path")
    args = parser.parse_args(argv)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key or not genai:
        sys.exit("Error: GEMINI_API_KEY and google-genai are required.")

    client = genai.Client(api_key=api_key)
    source_path = Path(args.source).expanduser().resolve()
    output_mp4 = Path(args.output).expanduser().resolve()
    work_dir = output_mp4.parent / ".ai_assets"
    work_dir.mkdir(parents=True, exist_ok=True)

    stem = output_mp4.stem
    real_16x9 = work_dir / f"{stem}_real_16x9.jpg"
    extract_16x9_frame(source_path, real_16x9, args.timestamp)

    if args.mode == "paint_morph":
        styled_16x9 = work_dir / f"{stem}_{args.style}_16x9.jpg"
        if args.force_keyframes or not styled_16x9.exists():
            generate_stylized_frame(client, real_16x9, styled_16x9, args.style)
        if args.keyframes_only:
            return
        if args.reverse_morph:
            first_f, last_f = real_16x9, styled_16x9
            default_prompt = (
                "In a single unbroken shot, start from the photorealistic scene in Image1 and smoothly transform "
                "into the textured palette-knife oil painting in Image2."
            )
        else:
            first_f, last_f = styled_16x9, real_16x9
            default_prompt = (
                "In a single unbroken shot, the vibrant painting in Image1 comes alive with gentle natural motion "
                "in the water and sky, then smoothly melts and transforms into the crisp photorealistic morning road in Image2."
            )
        run_omni_video(client, args.prompt or default_prompt, output_mp4, first_frame=first_f, last_frame=last_f, duration=args.duration)

    elif args.mode == "fpv_drone":
        if not args.rider_ref:
            sys.exit("Error: --rider-ref <photo_with_bike.jpg> is required for --mode fpv_drone.")
        refs: list[Path] = []
        for idx, ref_str in enumerate(args.rider_ref):
            ref_p = Path(ref_str).expanduser().resolve()
            if ref_p.suffix.lower() in {".mp4", ".mov", ".m4v"}:
                extracted = work_dir / f"ride_ref_{ref_p.stem}_{idx}.jpg"
                extract_16x9_frame(ref_p, extracted, args.rider_ref_timestamp)
                refs.append(extracted)
            else:
                refs.append(ref_p)

        spec_cache = work_dir / f"rider_bike_spec_{'_'.join(p.stem for p in refs)}.txt"
        rider_bike_spec = describe_ride_kit_and_bike(client, refs, spec_cache)
        vp = args.viewpoint
        start_kf = work_dir / f"{stem}_{vp}_start_16x9.jpg"
        end_kf = work_dir / f"{stem}_{vp}_end_16x9.jpg"

        if vp == "crane_above_to_behind":
            if args.force_keyframes or not start_kf.exists():
                synthesize_viewpoint_keyframe(
                    client,
                    real_16x9,
                    refs,
                    rider_bike_spec,
                    "Generate a photorealistic 16:9 high-angle FPV drone view from 7 meters up looking down at an angle "
                    "toward the road where this exact cyclist on this exact road bike is pedaling forward along this exact road.",
                    start_kf,
                )
            if args.force_keyframes or not end_kf.exists():
                synthesize_viewpoint_keyframe(
                    client,
                    real_16x9,
                    refs,
                    rider_bike_spec,
                    "Generate a photorealistic 16:9 low rear-three-quarter chase camera view just 2.5 meters behind and "
                    "slightly to the left of this exact cyclist on this exact road bike pedaling forward along this exact road.",
                    end_kf,
                )
            if args.keyframes_only:
                return
            default_prompt = (
                f"In a single continuous unbroken FPV drone shot, start high above the road in Image1 and "
                f"smoothly crane down and swoop forward behind the cyclist <IMAGE_REF_0> ({rider_bike_spec}) "
                f"to reach the close low rear-three-quarter tracking view in Image2. No dialogue."
            )
            run_omni_video(client, args.prompt or default_prompt, output_mp4, first_frame=start_kf, last_frame=end_kf, ref_images=refs[:1], duration=args.duration)
        else:
            vp_desc = {
                "side_tracking": (
                    "Generate a photorealistic 16:9 low-angle pro-peloton motorcycle side-profile tracking shot showing "
                    "this exact cyclist pedaling forward in the exact same geographic travel direction as Image 1."
                ),
                "low_rear_chase": (
                    "Generate a photorealistic 16:9 low-angle rear-three-quarter pro-peloton follow shot 2 meters behind "
                    "this exact cyclist on this exact road bike riding forward on this exact road."
                ),
                "front_lead": (
                    "Generate a photorealistic 16:9 low front-three-quarter lead camera view looking back at this exact "
                    "cyclist on this exact road bike riding forward along this exact road."
                ),
                "custom": args.prompt or "Generate a photorealistic 16:9 dynamic tracking view of this exact cyclist on this road.",
            }[vp]
            if args.force_keyframes or not start_kf.exists():
                synthesize_viewpoint_keyframe(client, real_16x9, refs, rider_bike_spec, vp_desc, start_kf)
            if args.keyframes_only:
                return
            default_prompt = (
                f"In a single continuous unbroken camera tracking shot starting from Image1, follow the cyclist "
                f"<IMAGE_REF_0> ({rider_bike_spec}) riding smoothly along the road. {args.prompt or ''} No dialogue."
            )
            run_omni_video(client, default_prompt, output_mp4, first_frame=start_kf, ref_images=refs[:1], duration=args.duration)

    elif args.mode == "living_memory":
        default_prompt = (
            "In a single unbroken shot starting from Image1, the people in the photograph come gently to life "
            "with warm natural smiles, subtle head movement, and gentle ambient motion in the background, "
            "preserving their exact faces and clothing."
        )
        run_omni_video(client, args.prompt or default_prompt, output_mp4, first_frame=real_16x9, duration=args.duration)


def subclips_cli_main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Analyze video contact strips to index sub-events and landmarks.")
    parser.add_argument("--project-dir", required=True, type=Path, help="Path to project folder")
    parser.add_argument("--force", action="store_true", help="Force re-analysis even if cached")
    args = parser.parse_args(argv)
    process_project_subclips(args.project_dir.expanduser().resolve(), force=args.force)
