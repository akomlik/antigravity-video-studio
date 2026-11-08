#!/usr/bin/env python3
"""
Antigravity Video Studio — Native AI Creative Artifact Engine (Zero BleeqUP Dependency)
========================================================================================
Generates watermark-free 1080p (16:9) AI creative transitions, multi-viewpoint 3rd-person
FPV drone / moto tracking shots, and living archival memories directly from raw camera clips
and ride photos using:
  1. `gemini-3-pro-image-preview` (Native 2K 16:9 Multi-Viewpoint Keyframe & Stylization Synthesis)
  2. `gemini-omni-1.1-flash` (First-to-Last-Frame + Multi-Reference `<IMAGE_REF_0>` Video Generation)

How `fpv_drone` mode works (mirroring & surpassing the BleeqUP workflow with zero hardcoding):
  1. Choose a source video clip from the ride (`--source <clip.MOV> --timestamp <sec>`).
  2. Provide that day's photo(s) of the rider with their bike (`--rider-ref <photo_with_bike.jpg>`),
     since kit and bike change from ride to ride. The script dynamically extracts the visual spec
     of that day's exact bike + kit from the reference photo and passes the photo as `<IMAGE_REF_0>`.
  3. Select one of the 4 POV Templates (`crane_above_to_behind`, `side_tracking`, `low_rear_chase`,
     `front_lead`) or `custom` with `--prompt "..."`.
"""

import argparse
import base64
import os
import subprocess
import sys
import time
from pathlib import Path
from PIL import Image
from google import genai
from google.genai import types

VIDEO_MODEL = "gemini-omni-flash-preview"
IMAGE_MODEL = "gemini-3-pro-image"
VISION_MODEL = "gemini-3.8-flash"

STYLE_PROMPTS = {
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


def extract_16x9_frame(source_path: Path, out_jpg: Path, timestamp_sec: float = 1.0) -> Path:
    """Extracts or center-crops a clean 1920x1080 (16:9) JPEG frame from a video or image."""
    out_jpg.parent.mkdir(parents=True, exist_ok=True)
    ext = source_path.suffix.lower()
    if ext in {".mp4", ".mov", ".m4v"}:
        cmd = [
            "ffmpeg", "-y", "-ss", f"{timestamp_sec:.2f}", "-i", str(source_path),
            "-frames:v", "1", "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-update", "1", "-q:v", "2", str(out_jpg)
        ]
    else:
        cmd = [
            "ffmpeg", "-y", "-i", str(source_path),
            "-vf", "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080",
            "-update", "1", "-q:v", "2", str(out_jpg)
        ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out_jpg


def describe_ride_kit_and_bike(client: genai.Client, ref_images: list[Path], cache_file: Path) -> str:
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
    resp = client.models.generate_content(
        model=VISION_MODEL,
        contents=[*imgs, prompt],
    )
    spec = (resp.text or "").strip()
    if spec:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(spec, encoding="utf-8")
        print(f"🔍 Auto-detected ride kit & bike spec from reference photo: {spec}")
        return spec
    return "the exact cyclist and road bicycle shown in the reference photo"


def generate_stylized_frame(client: genai.Client, real_frame_jpg: Path, out_stylized_jpg: Path, style: str, custom_prompt: str = None) -> Path:
    """Uses gemini-3-pro-image-preview to synthesize a 16:9 artistic twin."""
    prompt = custom_prompt or STYLE_PROMPTS.get(style, STYLE_PROMPTS["impasto_oil"])
    img = Image.open(real_frame_jpg)
    print(f"🎨 Synthesizing native '{style}' keyframe via {IMAGE_MODEL}...")
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
            print(f"✅ Saved synthesized keyframe: {out_stylized_jpg}")
            return out_stylized_jpg
    raise RuntimeError(f"No image returned by {IMAGE_MODEL}")


def synthesize_viewpoint_keyframe(
    client: genai.Client,
    road_frame_jpg: Path,
    ref_images: list[Path],
    rider_bike_spec: str,
    viewpoint_instruction: str,
    out_jpg: Path,
) -> Path:
    """Uses gemini-3-pro-image-preview with road frame + ride-specific reference photo(s) to create an exact 16:9 keyframe."""
    contents = [Image.open(road_frame_jpg)]
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
        f"Do not blindly copy the left-or-right facing direction of the reference photo if the road in Image 1 "
        f"flows in the opposite direction. "
        f"CRITICAL VISUAL LOCK: Preserve the exact bicycle frame color, brand decals, accessories, and the rider's "
        f"exact helmet, glasses, jersey, shorts, and shoes from the reference photo(s)."
    )
    contents.append(full_prompt)
    print(f"🚁 Synthesizing viewpoint keyframe ({out_jpg.name}) via {IMAGE_MODEL}...")
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
            print(f"✅ Saved viewpoint keyframe: {out_jpg}")
            return out_jpg
    raise RuntimeError(f"No keyframe returned by {IMAGE_MODEL}")


def run_omni_video(
    client: genai.Client,
    prompt: str,
    output_mp4: Path,
    first_frame: Path | None = None,
    last_frame: Path | None = None,
    ref_images: list[Path] | None = None,
    duration: int = 5,
    resolution: str = "1080p",
) -> Path:
    """Runs gemini-omni-1.1-flash background video synthesis with File API frame + reference anchoring."""
    omni_script_dir = Path.home() / ".gemini/config/plugins/gemini-api/skills/gemini-omni-flash-api/scripts/video"
    if str(omni_script_dir) not in sys.path:
        sys.path.insert(0, str(omni_script_dir))
    from generate_video import resolve_or_upload_asset

    input_parts = []
    img_idx = 1
    sources_decl = []
    refs_decl = []

    if first_frame:
        f1_uri, f1_mime = resolve_or_upload_asset(str(first_frame), "image/jpeg")
        input_parts.append({"type": "image", "uri": f1_uri, "mime_type": f1_mime})
        sources_decl.append(f"<FIRST_FRAME>@Image{img_idx}")
        img_idx += 1

    if last_frame:
        f2_uri, f2_mime = resolve_or_upload_asset(str(last_frame), "image/jpeg")
        input_parts.append({"type": "image", "uri": f2_uri, "mime_type": f2_mime})
        sources_decl.append(f"<LAST_FRAME>@Image{img_idx}")
        img_idx += 1

    valid_refs = [r for r in (ref_images or []) if r and r.exists()]
    for r_i, ref_p in enumerate(valid_refs):
        r_uri, r_mime = resolve_or_upload_asset(str(ref_p), "image/jpeg")
        input_parts.append({"type": "image", "uri": r_uri, "mime_type": r_mime})
        refs_decl.append(f"<IMAGE_REF_{r_i}>@Image{img_idx}")
        img_idx += 1

    prefix_blocks = []
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

    print(f"🎬 Launching {VIDEO_MODEL} ({resolution}, {duration}s) -> {output_mp4.name} ...")
    print(f"   Prompt: {prompt_text}")
    interaction = client.interactions.create(
        model=VIDEO_MODEL,
        input=input_parts,
        response_format=video_config,
        background=True,
    )
    print(f"   Interaction ID: {interaction.id}")
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
            print(f"✅ Saved AI Creative Video ({len(video_bytes) / (1024*1024):.1f} MB): {output_mp4}")
            return output_mp4
        if getattr(output_video, "uri", None):
            video_bytes = client.files.download(file=output_video.uri)
            output_mp4.parent.mkdir(parents=True, exist_ok=True)
            output_mp4.write_bytes(video_bytes)
            print(f"✅ Saved AI Creative Video ({len(video_bytes) / (1024*1024):.1f} MB): {output_mp4}")
            return output_mp4
    raise RuntimeError("No video output returned.")


def main():
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
        help="4 POV templates (crane_above_to_behind, side_tracking, low_rear_chase, front_lead) or custom",
    )
    parser.add_argument(
        "--rider-ref",
        nargs="+",
        help="Ride-specific photo(s) or video clip of the rider with their bike from that day's ride (required for fpv_drone)",
    )
    parser.add_argument("--rider-ref-timestamp", type=float, default=11.2, help="Timestamp if a rider-ref item is a video")
    parser.add_argument("--prompt", help="Optional custom motion/viewpoint prompt")
    parser.add_argument("--force-keyframes", action="store_true", help="Regenerate keyframes even if cached")
    parser.add_argument("--keyframes-only", action="store_true", help="Only synthesize and save keyframes without running video")
    parser.add_argument("--duration", type=int, default=5, help="Duration in seconds (4-8)")
    parser.add_argument("--output", required=True, help="Output MP4 file path")
    args = parser.parse_args()

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Error: GEMINI_API_KEY environment variable is required.")

    client = genai.Client(api_key=api_key)
    source_path = Path(args.source).resolve()
    output_mp4 = Path(args.output).resolve()
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
            sys.exit(
                "Error: --rider-ref <photo_with_bike.jpg> is required for --mode fpv_drone so the generator "
                "locks onto that day's exact cycling kit and bicycle."
            )
        refs = []
        for idx, ref_str in enumerate(args.rider_ref):
            ref_p = Path(ref_str).resolve()
            if ref_p.suffix.lower() in {".mp4", ".mov", ".m4v"}:
                extracted = work_dir / f"ride_ref_{ref_p.stem}_{idx}.jpg"
                extract_16x9_frame(ref_p, extracted, args.rider_ref_timestamp)
                refs.append(extracted)
            else:
                refs.append(ref_p)

        ref_cache_key = "_".join(p.stem for p in refs)
        spec_cache = work_dir / f"rider_bike_spec_{ref_cache_key}.txt"
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
                f"to reach the close low rear-three-quarter tracking view in Image2. "
                f"Use Image1 as the starting frame, Image2 as the ending frame, and Image3 as the exact bike and rider reference. No dialogue."
            )
            run_omni_video(
                client,
                args.prompt or default_prompt,
                output_mp4,
                first_frame=start_kf,
                last_frame=end_kf,
                ref_images=refs[:1],
                duration=args.duration,
            )

        elif vp == "side_tracking":
            if args.force_keyframes or not start_kf.exists():
                synthesize_viewpoint_keyframe(
                    client,
                    real_16x9,
                    refs,
                    rider_bike_spec,
                    "Generate a photorealistic 16:9 low-angle pro-peloton motorcycle side-profile tracking shot from "
                    "the road on the left looking across the bike lane toward the beach/sea on the right, showing this "
                    "exact cyclist pedaling RIGHT-TO-LEFT (heading forward along the bike path toward the distant "
                    "mountains and marina on the left, in the EXACT same direction as the cyclists in Image 1—NEVER "
                    "riding left-to-right away from the mountains!), clearly showing the left side profile of the bike "
                    "frame, wheels, and rider's kit.",
                    start_kf,
                )
            if args.keyframes_only:
                return
            default_prompt = (
                f"In a single continuous unbroken pro-peloton side-tracking camera shot starting from Image1, "
                f"the camera glides smoothly alongside the cyclist <IMAGE_REF_0> ({rider_bike_spec}) as he pedals "
                f"fast along the road. Use Image1 as the starting frame and Image2 as the exact bike and rider reference. No dialogue."
            )
            run_omni_video(
                client,
                args.prompt or default_prompt,
                output_mp4,
                first_frame=start_kf,
                ref_images=refs[:1],
                duration=args.duration,
            )

        else:
            vp_desc = {
                "low_rear_chase": (
                    "Generate a photorealistic 16:9 low-angle rear-three-quarter pro-peloton follow shot 2 meters behind "
                    "and slightly to the side of this exact cyclist on this exact road bike riding forward on this exact road."
                ),
                "front_lead": (
                    "Generate a photorealistic 16:9 low front-three-quarter lead camera view looking back at this exact "
                    "cyclist on this exact road bike riding forward along this exact road."
                ),
                "custom": args.prompt or "Generate a photorealistic 16:9 dynamic tracking view of this exact cyclist on this exact road bike on this road.",
            }[vp]
            if args.force_keyframes or not start_kf.exists():
                synthesize_viewpoint_keyframe(client, real_16x9, refs, rider_bike_spec, vp_desc, start_kf)
            if args.keyframes_only:
                return
            default_prompt = (
                f"In a single continuous unbroken camera tracking shot starting from Image1, follow the cyclist "
                f"<IMAGE_REF_0> ({rider_bike_spec}) riding smoothly along the road. {args.prompt or ''} "
                f"Use Image1 as the starting frame and Image2 as the exact bike and rider reference. No dialogue."
            )
            run_omni_video(
                client,
                default_prompt,
                output_mp4,
                first_frame=start_kf,
                ref_images=refs[:1],
                duration=args.duration,
            )

    elif args.mode == "living_memory":
        default_prompt = (
            "In a single unbroken shot starting from Image1, the people in the photograph come gently to life "
            "with warm natural smiles, subtle head movement, and gentle ambient motion in the background, "
            "preserving their exact faces and clothing."
        )
        run_omni_video(client, args.prompt or default_prompt, output_mp4, first_frame=real_16x9, duration=args.duration)


if __name__ == "__main__":
    main()
