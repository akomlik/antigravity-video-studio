#!/usr/bin/env python3
"""
generate_voiceover.py
Synthesizes warm multilingual voice-over narration (en, uk, ru) in Alexander Komlik's
voice using Gemini 3.8 Flash TTS (`gemini-3.8-flash-tts`), automatically injecting
`GEMINI_API_KEY` from 1Password via `~/src/ai-workflow/scripts/direnv-mcp`:
- Tier 1 (Exact Voice Replication): Uses `alexander_komlik_reference_24k.wav` (extracted from
  `Zero-T Performance Self-Talk.m4a`) + `alexander_komlik_consent_24k.wav` when present.
- Tier 2 (Audio-Matched Voice Design): Analyzes `alexander_komlik_reference_24k.wav` with
  `gemini-3.8-flash` to capture Alexander's exact vocal timbre, pitch, cadence, and subtle
  Eastern European/American inflection, creates a persistent custom `voice_...` persona via
  `client.voices.create(type="prompted")`, and synthesizes `voiceover_en.wav`, `voiceover_uk.wav`,
  and `voiceover_ru.wav`.
"""

import argparse
import base64
import json
import os
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
DIRENV_MCP = Path(os.environ.get("DIRENV_MCP_BIN", "~/src/ai-workflow/scripts/direnv-mcp")).expanduser()
VOICE_DIR = STUDIO_ROOT / "03_Audio_Library/03_Voice_Profile"
REF_WAV = VOICE_DIR / "alexander_komlik_reference_24k.wav"
CONSENT_WAV = VOICE_DIR / "alexander_komlik_consent_24k.wav"
VOICE_ID_FILE = VOICE_DIR / "voice_id.json"


def ensure_direnv_environment():
    """If launched from a GUI app without GEMINI_API_KEY, re-exec via direnv-mcp."""
    if not os.environ.get("GEMINI_API_KEY") and DIRENV_MCP.exists() and not os.environ.get("_DIRENV_MCP_WRAPPED"):
        os.environ["_DIRENV_MCP_WRAPPED"] = "1"
        os.execv(str(DIRENV_MCP), [str(DIRENV_MCP), sys.executable, *sys.argv])


def ensure_custom_voice(client) -> str:
    """Returns a cached stateful `voice_...` ID or creates one from Alexander's reference audio."""
    if VOICE_ID_FILE.exists():
        data = json.loads(VOICE_ID_FILE.read_text(encoding="utf-8"))
        if data.get("voice_id"):
            return data["voice_id"]

    if not REF_WAV.exists():
        raise FileNotFoundError(f"Reference voice WAV not found at {REF_WAV}")

    source_b64 = base64.b64encode(REF_WAV.read_bytes()).decode("utf-8")

    if CONSENT_WAV.exists():
        consent_b64 = base64.b64encode(CONSENT_WAV.read_bytes()).decode("utf-8")
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
        VOICE_ID_FILE.write_text(
            json.dumps({"voice_id": replicated_voice.id, "mode": "replicated"}, indent=2),
            encoding="utf-8",
        )
        print(f"Created persistent replicated voice ID: {replicated_voice.id}")
        return replicated_voice.id

    # Analyze Alexander's real voice from Zero-T Performance Self-Talk.m4a using gemini-3.8-flash
    print("Analyzing Alexander's vocal timbre from alexander_komlik_reference_24k.wav...")
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
                            "Listen to this speaker's vocal timbre, resonance, pitch register (baritone/tenor), "
                            "and subtle Eastern European-inflected American English accent. Write a concise 2-sentence "
                            "Voice Design prompt for a TTS voice model that captures his exact vocal timbre and accent, "
                            "but speaking at a natural, upbeat, warm, conversational storytelling pace (not slow or clinical). "
                            "Output ONLY the 2-sentence description."
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
    print(f"Extracted vocal profile: {voice_prompt}")

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
    VOICE_ID_FILE.write_text(
        json.dumps(
            {"voice_id": created_voice.id, "mode": "prompted_from_reference", "voice_prompt": voice_prompt},
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Created persistent custom voice ID: {created_voice.id}")
    return created_voice.id


def synthesize_narration(text: str, out_wav: Path, voice_id: str, client):
    """Synthesizes warm conversational narration using `gemini-3.8-flash-tts` and normalizes to 48kHz stereo WAV."""
    import subprocess
    interaction = client.interactions.create(
        model="gemini-3.8-flash-tts",
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
    )
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    raw_wav = out_wav.with_suffix(".raw24k.wav")
    raw_wav.write_bytes(base64.b64decode(interaction.output_audio.data))
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg", "-y",
            "-i", str(raw_wav),
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
            str(out_wav),
        ],
        check=True,
        capture_output=True,
    )
    raw_wav.unlink(missing_ok=True)
    print(f"Synthesized voice-over -> {out_wav} ({out_wav.stat().st_size // 1024} KB)")


def main():
    ensure_direnv_environment()
    from google import genai

    p = argparse.ArgumentParser(description="Generate multilingual voice-over narration in Alexander's voice")
    p.add_argument("--project-dir", required=True, help="Path to 04_Project_Catalog/YEAR/<project_name>")
    p.add_argument("--voice-id", help="Optional explicit Gemini `voice_...` ID")
    p.add_argument("--recreate-voice", action="store_true", help="Recreate custom voice persona with natural pace")
    p.add_argument("--only", help="Optional comma-separated lang:part filter, e.g. ua:part2,ru:part2")
    args = p.parse_args()

    if args.recreate_voice and VOICE_ID_FILE.exists():
        VOICE_ID_FILE.unlink()

    only_set = set(args.only.split(",")) if args.only else None

    proj_dir = Path(args.project_dir).expanduser().resolve()
    scripts_path = proj_dir / "narration_scripts.json"
    if not scripts_path.exists():
        raise FileNotFoundError(f"narration_scripts.json not found in {proj_dir}. Run generate_youtube_metadata.py first.")

    scripts = json.loads(scripts_path.read_text(encoding="utf-8"))
    client = genai.Client()
    voice_id = args.voice_id or ensure_custom_voice(client)

    for lang, val in scripts.items():
        if isinstance(val, dict):
            for seg_key, seg_text in val.items():
                if only_set and f"{lang}:{seg_key}" not in only_set and lang not in only_set:
                    continue
                out_wav = proj_dir / f"voiceover_{lang}_{seg_key}.wav"
                synthesize_narration(seg_text, out_wav, voice_id, client)
        else:
            if only_set and lang not in only_set:
                continue
            out_wav = proj_dir / f"voiceover_{lang}.wav"
            synthesize_narration(val, out_wav, voice_id, client)


if __name__ == "__main__":
    main()
