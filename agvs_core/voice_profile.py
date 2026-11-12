"""
agvs_core/voice_profile.py
Secure stateful replicated voice registration & multilingual voice-over TTS synthesis
via Google GenAI SDK (`gemini-3.8-flash-tts`), persisting `$GEMINI_VOICE_ID` exclusively
to 1Password (`Private/envvar:GEMINI_VOICE_ID`) and 0o600 local `~/.config/antigravity_studio/voice_id.json`.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

from agvs_core.audio_dsp import STUDIO_DRY_CORE_FILTER
from agvs_core.config import (
    find_binary,
    get_gemini_voice_id,
    get_local_secret_voice_cache_file,
    get_studio_root,
    mask_secret,
)


def load_dotenv_if_needed(studio_root: Optional[Path] = None) -> None:
    root = studio_root or get_studio_root()
    env_file = root / ".env"
    if not os.environ.get("GEMINI_API_KEY") and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def ensure_24k_mono_wav(src_path: Path, out_path: Path) -> Path:
    """Converts any audio file to 24kHz mono PCM WAV required by Gemini voice replication."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = find_binary("ffmpeg")
    subprocess.run(
        [ffmpeg_bin, "-y", "-i", str(src_path), "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le", str(out_path)],
        check=True,
        capture_output=True,
    )
    return out_path


def store_voice_id_securely(new_voice_id: str, project_dir: Optional[Path] = None) -> None:
    """Stores replicated voice ID in 1Password (`Private`) and 0o600 local cache, keeping `$GEMINI_VOICE_ID` in Storyboard.md."""
    op_bin = find_binary("op", required=False)
    if op_bin:
        try:
            check = subprocess.run(
                [op_bin, "item", "get", "envvar:GEMINI_VOICE_ID", "--vault", "Private"],
                capture_output=True,
                text=True,
                check=False,
            )
            if check.returncode == 0:
                subprocess.run(
                    [op_bin, "item", "edit", "envvar:GEMINI_VOICE_ID", f"credential[concealed]={new_voice_id}", "--vault", "Private"],
                    check=True,
                    capture_output=True,
                )
            else:
                subprocess.run(
                    [
                        op_bin,
                        "item",
                        "create",
                        "--category",
                        "API_CREDENTIAL",
                        "--vault",
                        "Private",
                        "--title",
                        "envvar:GEMINI_VOICE_ID",
                        f"credential[concealed]={new_voice_id}",
                    ],
                    check=True,
                    capture_output=True,
                )
        except Exception as exc:
            print(f"  Note: 1Password CLI update skipped or unavailable: {exc}")

    voice_json = get_local_secret_voice_cache_file()
    voice_json.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(voice_json.parent, 0o700)
    voice_json.write_text(
        json.dumps(
            {
                "voice_id": new_voice_id,
                "mode": "replicated",
                "display_name": "Alexander",
                "registered_via": "agvs_core.voice_profile",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    os.chmod(voice_json, 0o600)

    if project_dir and (project_dir / "Storyboard.md").exists():
        sb_file = project_dir / "Storyboard.md"
        text = sb_file.read_text(encoding="utf-8")
        text = re.sub(r'voiceover_persona:\s*(?:"[^"]+"|\S+)', 'voiceover_persona: "$GEMINI_VOICE_ID"', text)
        sb_file.write_text(text, encoding="utf-8")


DEFAULT_STANDARD_VOICE = "Charon"


def ensure_custom_voice(client: Any, use_replicated: bool = False) -> str:
    """
    Returns the configured Gemini TTS voice (`$GEMINI_VOICE_ID`, e.g. standard voice `Charon` / `Orus`
    or a prompted/studio voice persona), defaulting to Google's clean standard baritone (`Charon`)
    unless `use_replicated=True` is explicitly requested (replicated voice cloning was retired as
    inaudible/unreliable and burned API quota).
    """
    resolved = get_gemini_voice_id()
    if resolved:
        return resolved

    voice_id_file = get_local_secret_voice_cache_file()
    if voice_id_file.exists():
        data = json.loads(voice_id_file.read_text(encoding="utf-8"))
        if data.get("voice_id"):
            return str(data["voice_id"])

    if not use_replicated:
        return DEFAULT_STANDARD_VOICE

    voice_dir = get_studio_root() / "03_Audio_Library/03_Voice_Profile"
    ref_wav = voice_dir / "alexander_komlik_reference_24k.wav"
    consent_wav = voice_dir / "alexander_komlik_consent_24k.wav"
    if not ref_wav.exists():
        raise FileNotFoundError(f"Reference voice WAV not found at {ref_wav}")

    source_b64 = base64.b64encode(ref_wav.read_bytes()).decode("utf-8")
    if consent_wav.exists():
        consent_b64 = base64.b64encode(consent_wav.read_bytes()).decode("utf-8")
        replicated_voice = client.voices.create(
            store=True,
            voice={
                "model": "gemini-3.8-flash-tts",
                "type": "replicated",
                "display_name": "Alexander Komlik Replicated Voice",
                "replicated": {
                    "source_audio": {"mime_type": "audio/wav", "data": source_b64},
                    "consent_audio": {"mime_type": "audio/wav", "data": consent_b64},
                },
            },
        )
        store_voice_id_securely(replicated_voice.id)
        print(f"Created persistent replicated voice ID: {mask_secret(replicated_voice.id)}")
        return str(replicated_voice.id)

    analysis = client.interactions.create(
        model="gemini-3.8-flash",
        input=[
            {
                "type": "user_input",
                "content": [
                    {"type": "audio", "mime_type": "audio/wav", "data": source_b64},
                    {
                        "type": "text",
                        "text": (
                            "Listen to this speaker's vocal timbre, resonance, pitch register, and subtle Eastern European-"
                            "inflected American English accent. Write a concise 2-sentence Voice Design prompt for a TTS voice "
                            "model speaking at a natural, upbeat, warm conversational storytelling pace."
                        ),
                    },
                ],
            }
        ],
    )
    voice_prompt = (analysis.output_text or "").strip() or (
        "A warm, grounded male baritone in his early 60s with a natural, upbeat conversational cadence and a subtle "
        "Eastern European-inflected American accent, speaking with relaxed storytelling warmth and friendly energy."
    )
    created_voice = client.voices.create(
        store=True,
        voice={
            "model": "gemini-3.8-flash-tts",
            "type": "prompted",
            "display_name": "Alexander Komlik Narrator Persona",
            "gender": "male",
            "language_code": "en-US",
            "prompted": {"input": voice_prompt},
        },
    )
    store_voice_id_securely(created_voice.id)
    print(f"Created persistent custom voice ID: {mask_secret(created_voice.id)}")
    return str(created_voice.id)


def synthesize_narration(text: str, out_wav: Path, voice_id: str, client: Any, lang: str = "en") -> Path:
    """Synthesizes warm conversational narration via Gemini TTS and normalizes once with Studio-Dry Anti-Reverb."""
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    raw_wav = out_wav.with_suffix(".raw24k.wav")

    last_err: Optional[Exception] = None
    for attempt in range(3):
        try:
            interaction = client.interactions.create(
                model="gemini-3.8-flash-lite-tts",
                input=[
                    {
                        "type": "user_input",
                        "content": [
                            {
                                "type": "text",
                                "text": text,
                                "annotations": [
                                    {
                                        "type": "speech_metadata",
                                        "style": "warm, upbeat, natural conversational storytelling pace",
                                    }
                                ],
                            }
                        ],
                    }
                ],
                response_format={"type": "audio"},
                generation_config={"speech_config": [{"voice": voice_id}]},
                timeout=30.0,
                automatic_continuation=False,
                store=False,
            )
            raw_wav.write_bytes(base64.b64decode(interaction.output_audio.data))
            last_err = None
            break
        except Exception as exc:
            last_err = exc
            print(f"  [Attempt {attempt + 1}/3] Gemini TTS retry ({exc})...", flush=True)
            time.sleep(2.0 * (attempt + 1))

    if last_err is not None:
        raise RuntimeError(f"Gemini TTS failed after 3 attempts: {last_err}")

    ffmpeg_bin = find_binary("ffmpeg")
    subprocess.run(
        [
            ffmpeg_bin,
            "-y",
            "-i",
            str(raw_wav),
            "-af",
            STUDIO_DRY_CORE_FILTER,
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            "-metadata",
            "comment=agvs_studio_dry=1",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )
    raw_wav.unlink(missing_ok=True)
    print(f"Synthesized voice-over -> {out_wav} ({out_wav.stat().st_size // 1024} KB)", flush=True)
    return out_wav


def generate_voiceover_cli_main(argv: Optional[list[str]] = None) -> None:
    load_dotenv_if_needed()
    from google import genai
    from google.genai.types import HttpRetryOptions

    p = argparse.ArgumentParser(description="Generate multilingual voice-over narration in Alexander's voice")
    p.add_argument("--project-dir", required=True, help="Path to 04_Project_Catalog/YEAR/<project_name>")
    p.add_argument("--voice-id", help="Optional explicit Gemini `voice_...` ID")
    p.add_argument("--recreate-voice", action="store_true")
    p.add_argument("--only", help="Optional comma-separated lang:part filter, e.g. ua:part2,ru:part2")
    p.add_argument("--skip-existing", action="store_true")
    args = p.parse_args(argv)

    voice_id_file = get_local_secret_voice_cache_file()
    if args.recreate_voice and voice_id_file.exists():
        voice_id_file.unlink()

    only_set = set(args.only.split(",")) if args.only else None
    proj_dir = Path(args.project_dir).expanduser().resolve()
    scripts_path = proj_dir / "narration_scripts.json"
    if not scripts_path.exists():
        raise FileNotFoundError(f"narration_scripts.json not found in {proj_dir}.")

    scripts = json.loads(scripts_path.read_text(encoding="utf-8"))
    client = genai.Client(
        http_options={
            "api_version": "v1beta",
            "client_args": {"timeout": 45.0},
            "retry_options": HttpRetryOptions(attempts=1),
        }
    )
    voice_id = args.voice_id or ensure_custom_voice(client)

    tasks: list[tuple[str, Path, str]] = []
    for lang, val in scripts.items():
        if isinstance(val, dict):
            for seg_key, seg_text in val.items():
                if only_set and f"{lang}:{seg_key}" not in only_set and lang not in only_set:
                    continue
                tasks.append((seg_text, proj_dir / f"voiceover_{lang}_{seg_key}.wav", lang))
        else:
            if only_set and lang not in only_set:
                continue
            tasks.append((val, proj_dir / f"voiceover_{lang}.wav", lang))

    for idx, (t_txt, t_wav, t_lang) in enumerate(tasks, 1):
        if args.skip_existing and t_wav.exists() and t_wav.stat().st_size > 10000:
            continue
        print(f"[{idx}/{len(tasks)}] Synthesizing {t_lang.upper()} -> {t_wav.name}...", flush=True)
        synthesize_narration(t_txt, t_wav, voice_id, client, t_lang)
        if idx < len(tasks):
            time.sleep(6.0)


def register_voice_cli_main(argv: Optional[list[str]] = None) -> None:
    root = get_studio_root()
    load_dotenv_if_needed(root)
    from google import genai

    voice_cloning_dir = root / "03_Audio_Library/00_Voice_Cloning"
    parser = argparse.ArgumentParser(description="Register a replicated voice via Gemini 3.8 Flash TTS")
    parser.add_argument("--ref", type=Path, default=voice_cloning_dir / "my_voice_sample.wav")
    parser.add_argument("--consent", type=Path, default=voice_cloning_dir / "voice_consent.wav")
    parser.add_argument("--display-name", default="Alexander")
    parser.add_argument("--project-dir", type=Path, default=None)
    parser.add_argument("--resynthesize", action="store_true", default=False)
    args = parser.parse_args(argv)

    ref_file = args.ref.expanduser().resolve()
    consent_file = args.consent.expanduser().resolve()
    if not ref_file.exists():
        raise FileNotFoundError(f"Reference voice audio not found: {ref_file}")
    if not consent_file.exists():
        raise FileNotFoundError(f"Consent statement audio not found: {consent_file}")

    tmp_ref = voice_cloning_dir / ".tmp_ref_24k.wav"
    tmp_consent = voice_cloning_dir / ".tmp_consent_24k.wav"
    ensure_24k_mono_wav(ref_file, tmp_ref)
    ensure_24k_mono_wav(consent_file, tmp_consent)

    source_b64 = base64.b64encode(tmp_ref.read_bytes()).decode("utf-8")
    consent_b64 = base64.b64encode(tmp_consent.read_bytes()).decode("utf-8")
    tmp_ref.unlink(missing_ok=True)
    tmp_consent.unlink(missing_ok=True)

    client = genai.Client(http_options={"api_version": "v1beta"})
    replicated_voice = client.voices.create(
        store=True,
        voice={
            "model": "gemini-3.8-flash-tts",
            "type": "replicated",
            "display_name": args.display_name,
            "replicated": {
                "source_audio": {"mime_type": "audio/wav", "data": source_b64},
                "consent_audio": {"mime_type": "audio/wav", "data": consent_b64},
            },
        },
    )
    voice_id = replicated_voice.id
    print(f"Registered replicated voice {mask_secret(voice_id)} -> storing in 1Password & 0o600 cache.")
    store_voice_id_securely(voice_id, project_dir=args.project_dir)

    if args.resynthesize and args.project_dir and args.project_dir.exists():
        child_env = dict(os.environ, GEMINI_VOICE_ID=voice_id)
        gen_script = root / ".agents/skills/build-timeline/scripts/generate_voiceover.py"
        build_script = root / ".agents/skills/build-timeline/scripts/build_timeline.py"
        subprocess.run([sys.executable, str(gen_script), "--project-dir", str(args.project_dir)], env=child_env, check=True)
        subprocess.run([sys.executable, str(build_script), "--project-dir", str(args.project_dir)], check=True)
