#!/usr/bin/env python3
"""
register_replicated_voice.py
Registers a stateful replicated voice using Google GenAI SDK (google-genai 2.25.0+)
from reference audio (source_audio) and spoken consent statement (consent_audio).
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
VOICE_CLONING_DIR = STUDIO_ROOT / "03_Audio_Library/00_Voice_Cloning"
VOICE_PROFILE_DIR = STUDIO_ROOT / "03_Audio_Library/03_Voice_Profile"
DEFAULT_REF = VOICE_CLONING_DIR / "my_voice_sample.wav"
DEFAULT_CONSENT = VOICE_CLONING_DIR / "voice_consent.wav"


def load_dotenv():
    env_file = STUDIO_ROOT / ".env"
    if not os.environ.get("GEMINI_API_KEY") and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def ensure_24k_mono_wav(src_path: Path, out_path: Path) -> Path:
    """Converts any audio file to 24kHz mono PCM WAV required by Gemini voice replication."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg", "-y", "-i", str(src_path),
            "-ar", "24000", "-ac", "1", "-c:a", "pcm_s16le",
            str(out_path),
        ],
        check=True,
        capture_output=True,
    )
    return out_path


def store_voice_id_securely(new_voice_id: str, project_dir: Path | None = None):
    print(f"\nStoring replicated voice ID securely as a secret credential...")

    # 1. Store in 1Password following Alexander's direnv-manager convention
    try:
        check = subprocess.run(
            ["op", "item", "get", "envvar:GEMINI_VOICE_ID", "--vault", "Private"],
            capture_output=True,
            text=True,
        )
        if check.returncode == 0:
            subprocess.run(
                ["op", "item", "edit", "envvar:GEMINI_VOICE_ID", f"credential[concealed]={new_voice_id}", "--vault", "Private"],
                check=True,
                capture_output=True,
            )
            print("  🔒 Updated 1Password -> Private / envvar:GEMINI_VOICE_ID")
        else:
            subprocess.run(
                ["op", "item", "create", "--category", "API_CREDENTIAL", "--vault", "Private", "--title", "envvar:GEMINI_VOICE_ID", f"credential[concealed]={new_voice_id}"],
                check=True,
                capture_output=True,
            )
            print("  🔒 Created in 1Password -> Private / envvar:GEMINI_VOICE_ID")
    except Exception as e:
        print(f"  ⚠️  Note: 1Password CLI update skipped or unavailable: {e}")

    # 2. Store in local git-ignored .env file
    env_file = STUDIO_ROOT / ".env"
    lines = env_file.read_text(encoding="utf-8").splitlines() if env_file.exists() else []
    found = False
    new_lines = []
    for line in lines:
        if line.startswith("GEMINI_VOICE_ID="):
            new_lines.append(f"GEMINI_VOICE_ID={new_voice_id}")
            found = True
        else:
            new_lines.append(line)
    if not found:
        new_lines.append(f"GEMINI_VOICE_ID={new_voice_id}")
    env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    print(f"  ✅ Updated local git-ignored .env file")

    # 3. Store in local git-ignored 03_Audio_Library/03_Voice_Profile/voice_id.json
    voice_json = VOICE_PROFILE_DIR / "voice_id.json"
    voice_json.parent.mkdir(parents=True, exist_ok=True)
    voice_json.write_text(
        json.dumps(
            {
                "voice_id": new_voice_id,
                "mode": "replicated",
                "display_name": "Alexander",
                "registered_via": "register_replicated_voice.py",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"  ✅ Updated git-ignored voice cache -> {voice_json.relative_to(STUDIO_ROOT)}")

    # 4. In active Storyboard.md (catalog is git-ignored), update voiceover_persona
    if project_dir and (project_dir / "Storyboard.md").exists():
        sb_file = project_dir / "Storyboard.md"
        text = sb_file.read_text(encoding="utf-8")
        text = re.sub(r'voiceover_persona:\s*(?:"[^"]+"|\S+)', f'voiceover_persona: "$GEMINI_VOICE_ID"', text)
        sb_file.write_text(text, encoding="utf-8")
        print(f"  ✅ Updated Storyboard.md persona -> $GEMINI_VOICE_ID")

    # CRITICAL: Never write raw voice IDs to tracked repository files (assemble_engine.py, editing_constitution.md, etc.)
    print("  🛡️  Zero-leak standard enforced: No raw voice IDs written to git-tracked files.")


def main():
    load_dotenv()
    from google import genai

    parser = argparse.ArgumentParser(description="Register a replicated voice via Gemini 3.8 Flash TTS")
    parser.add_argument("--ref", type=Path, default=DEFAULT_REF, help="Path to reference speech WAV (10-30s)")
    parser.add_argument("--consent", type=Path, default=DEFAULT_CONSENT, help="Path to consent statement WAV")
    parser.add_argument("--display-name", default="Alexander", help="Display name for custom voice")
    parser.add_argument("--project-dir", type=Path, default=STUDIO_ROOT / "04_Project_Catalog/2026/2026-11-07_PCH_Saturday_partial", help="Project catalog directory to update")
    parser.add_argument("--resynthesize", action="store_true", default=True, help="Automatically resynthesize voiceover cues with new ID")
    args = parser.parse_args()

    ref_file = args.ref.expanduser().resolve()
    consent_file = args.consent.expanduser().resolve()

    if not ref_file.exists():
        raise FileNotFoundError(f"Reference voice audio not found: {ref_file}")
    if not consent_file.exists():
        raise FileNotFoundError(f"Consent statement audio not found: {consent_file}")

    print("=" * 70)
    print("AGVS Replicated Voice Registration (Gemini 3.8 Flash TTS)")
    print("=" * 70)
    print(f"Reference audio : {ref_file} ({ref_file.stat().st_size // 1024} KB)")
    print(f"Consent audio   : {consent_file} ({consent_file.stat().st_size // 1024} KB)")

    # Normalize to 24k mono WAV
    tmp_ref = VOICE_CLONING_DIR / ".tmp_ref_24k.wav"
    tmp_consent = VOICE_CLONING_DIR / ".tmp_consent_24k.wav"
    ensure_24k_mono_wav(ref_file, tmp_ref)
    ensure_24k_mono_wav(consent_file, tmp_consent)

    source_b64 = base64.b64encode(tmp_ref.read_bytes()).decode("utf-8")
    consent_b64 = base64.b64encode(tmp_consent.read_bytes()).decode("utf-8")

    client = genai.Client(http_options={"api_version": "v1beta"})

    payload = {
        "model": "gemini-3.8-flash-tts",
        "type": "replicated",
        "display_name": args.display_name,
        "replicated": {
            "source_audio": {"mime_type": "audio/wav", "data": source_b64},
            "consent_audio": {"mime_type": "audio/wav", "data": consent_b64},
        },
    }

    print("\nCalling client.voices.create(store=True, type_='replicated')...")
    try:
        replicated_voice = client.voices.create(store=True, voice=payload)
    except Exception as e:
        tmp_ref.unlink(missing_ok=True)
        tmp_consent.unlink(missing_ok=True)
        print(f"\n❌ Voice replication failed: {e}\n")
        err_msg = str(e)
        if "Voice mismatch detected" in err_msg or "Consent flow failed" in err_msg:
            print("💡 BIOMETRIC SPEAKER VERIFICATION TROUBLESHOOTING:")
            print("   Google's security system compares the vocal embeddings of your reference sample")
            print("   and consent recording to prevent unauthorized voice cloning.")
            print("   If the two files were recorded on different devices (e.g. laptop mic vs iPad),")
            print("   at different distances, or months apart in different speaking registers (fry vs modal),")
            print("   the model flags a mismatch.")
            print("\n👉 Quick 1-minute fix:")
            print("   Record a fresh 15–30 second voice sample on the EXACT SAME iPad/microphone where you")
            print(f"   recorded voice_consent.wav, and save it as: {DEFAULT_REF}")
            print("   Then re-run this script!")
        sys.exit(1)

    tmp_ref.unlink(missing_ok=True)
    tmp_consent.unlink(missing_ok=True)

    voice_id = replicated_voice.id
    print(f"\n🎉 SUCCESS! Replicated voice registered successfully!")
    print(f"  Voice ID    : {voice_id}")
    print(f"  Display Name: {getattr(replicated_voice, 'display_name', args.display_name)}")
    print(f"  Model       : {getattr(replicated_voice, 'model', 'gemini-3.8-flash-tts')}")

    # Store securely in 1Password, .env, and local cache (zero Git leaks)
    store_voice_id_securely(voice_id, project_dir=args.project_dir)

    # Resynthesize if requested
    if args.resynthesize and args.project_dir.exists():
        print(f"\nRe-rendering voiceovers for {args.project_dir.name} using {voice_id}...")
        gen_script = STUDIO_ROOT / ".agents/skills/build-timeline/scripts/generate_voiceover.py"
        subprocess.run(
            [sys.executable, str(gen_script), "--project-dir", str(args.project_dir), "--voice-id", voice_id],
            check=True,
        )
        print("Re-building timeline with authentic voice mix...")
        build_script = STUDIO_ROOT / ".agents/skills/build-timeline/scripts/build_timeline.py"
        subprocess.run(
            [sys.executable, str(build_script), "--project-dir", str(args.project_dir)],
            check=True,
        )
        print("\n✅ All voiceover tracks re-rendered and updated in FilmCraft!")


if __name__ == "__main__":
    main()
