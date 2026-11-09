# AGVS Replicated Voice Setup & Biometric Privacy Guide (Gemini 3.8 Flash TTS)

Google Gemini 3.8 Flash TTS (`gemini-3.8-flash-tts`) allows you to narrate your films in your **authentic, warm personal voice** through voice replication.

> [!IMPORTANT]
> **Mandatory Verbal Consent & Biometric Matching:**
> You cannot activate voice cloning simply by pointing Antigravity to an existing audio recording. Google’s Voice Replication API requires a **mandatory verbal consent audio recording** from the speaker before generating a model. Google runs automated biometric speaker verification comparing the reference sample against the consent clip. If there is a mismatch (e.g., recorded on different devices or speaking registers), the API rejects voice creation with `Consent flow failed. Voice mismatch detected.`

> [!CAUTION]
> **Biometric Voice ID Security Law (Zero Git Leaks):**
> Your custom replicated voice identifier (`voice_...`) is a **biometric credential** that allows synthetic speech generation in your exact voice. **It MUST NEVER be checked into the Git repository or hardcoded into tracked files!** Store it strictly in **1Password** under `envvar:GEMINI_VOICE_ID` (or local git-ignored `.env`) and resolve it dynamically via `$GEMINI_VOICE_ID` and `studio_config.get_gemini_voice_id()`.

---

## The Mandatory Consent Statement

When prompted by Google AI Studio or when recording your consent file, you must speak the exact phrase:

> *"I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model."*

---

## Option 1: Create Your Voice in Google AI Studio (Web UI)

The dedicated interface is the **Speech Playground** in Google AI Studio:

* **Direct URL:** [https://aistudio.google.com/generate-speech](https://aistudio.google.com/generate-speech)

### Step-by-Step Instructions:

1. **Sign in** with your Google account.
2. Select **Voice Replication** (or click the microphone / *Create custom voice* option).
3. Upload your speech sample (`.wav` or `.m4a`, ideally 20–30 seconds of clean, continuous narration without background noise) as the **Reference Audio**.
4. Read and record the mandatory consent phrase into your microphone when prompted:
   > *"I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model."*
5. Once verified, AI Studio will generate your persistent voice identifier (e.g., `voice_abcdef123456`).
6. **Save into Variable (Zero Git Leaks):**
   
   #### Path A: 1Password (Recommended — Alexander's Convention)
   Add or update the item in your `Private` vault:
   ```bash
   op item edit "envvar:GEMINI_VOICE_ID" "credential[concealed]=PASTE_YOUR_VOICE_ID_HERE" --vault Private
   # Or create if it does not yet exist:
   op item create --category API_CREDENTIAL --vault Private --title "envvar:GEMINI_VOICE_ID" "credential[concealed]=PASTE_YOUR_VOICE_ID_HERE"
   ```

   #### Path B: Local Git-Ignored `.env` (Quick Fallback)
   Add it to your studio `.env` file:
   ```bash
   echo "GEMINI_VOICE_ID=PASTE_YOUR_VOICE_ID_HERE" >> .env
   ```

   #### Path C: Prompt Antigravity in Chat
   ```text
   I created my custom voice ID in Google AI Studio: [PASTE_YOUR_VOICE_ID_HERE].
   Please save it to my 1Password vault Private (envvar:GEMINI_VOICE_ID) and local .env with zero git leaks, and re-render the narration tracks with my authentic voice.
   ```

---

## Option 2: Automated Antigravity Script Registration via API (CLI / Chat)

If you prefer to register the voice without using the browser UI, Antigravity provides an automated registration script: [`register_replicated_voice.py`](../../.agents/skills/build-timeline/scripts/register_replicated_voice.py).

### Step-by-Step Instructions:

1. **Record the Reference Sample & Consent Phrase on the Same Device:**
   - Use Voice Memos, QuickTime, or your phone in a quiet room:
     - **Sample (`my_voice_sample.wav` or `.m4a`):** 20–30 seconds of natural storytelling (e.g. reading Scene 00 of `Storyboard.md`).
     - **Consent (`voice_consent.wav` or `.m4a`):** Recite:
       > *"I am the owner of this voice and I consent to Google using this voice to create a synthetic voice model."*
   > [!TIP]
   > **Avoid Voice Mismatches:** Always record both files on the **exact same microphone/device in the same sitting** with the same vocal register and distance from the mic.

2. **Stage Files in `03_Audio_Library/00_Voice_Cloning/`:**
   ```bash
   03_Audio_Library/00_Voice_Cloning/my_voice_sample.wav
   03_Audio_Library/00_Voice_Cloning/voice_consent.wav
   ```
   *(All `.wav`, `.m4a`, and `.mp3` files in this directory are git-ignored).*

3. **Run Registration:**
   
   #### In Shell:
   ```bash
   python3 .agents/skills/build-timeline/scripts/register_replicated_voice.py
   ```

   #### Or Prompt Antigravity:
   ```text
   Please register my replicated voice from 03_Audio_Library/00_Voice_Cloning/my_voice_sample.wav and voice_consent.wav. 
   Save the resulting voice ID securely to 1Password (Private / envvar:GEMINI_VOICE_ID) and .env with zero git leaks, then re-render the voiceovers.
   ```

### What the Script Automatically Does:
1. Converts audio inputs to 24 kHz mono PCM WAV format required by Gemini.
2. Calls `client.voices.create(store=True, type_="replicated", ...)` via `google-genai` `v1beta`.
3. Verifies voice creation and receives the persistent `voice_...` ID.
4. Stores the ID in **1Password** under `envvar:GEMINI_VOICE_ID` (vault `Private`).
5. Updates local git-ignored `.env` and `03_Audio_Library/03_Voice_Profile/voice_id.json`.
6. **Enforces Zero Git Leaks:** Guarantees zero raw voice IDs are ever written to git-tracked files!
7. Triggers re-synthesis of narration stems through the **Studio-Dry Anti-Reverb Chain** and rebuilds the FilmCraft timeline.

---

## Studio-Dry Anti-Reverb Law for Authentic Voices

Because voice samples recorded in residential rooms capture room reflections and acoustic boxiness, voice-over tracks **MUST NEVER be processed with aggressive dynamic normalizers (`dynaudnorm`) that pump room reverb tails between words!**

All voiceover stems (`A4`) are processed through the Studio-Dry Anti-Reverb filter chain:
1. **Sub-bass Rumble Cut:** `highpass=f=95`
2. **Room Boxiness Notch:** `equalizer=f=380:width_type=q:w=1.4:g=-4.5,equalizer=f=600:width_type=q:w=1.6:g=-2.5`
3. **Spectral Dereverberation:** `afftdn=nr=12:nf=-38:tn=1`
4. **Downward Expander / Tail Gate:** `agate=range=0.06:threshold=0.040:ratio=3.5:attack=10:release=90`
5. **Clean Broadcast Normalization:** `loudnorm=I=-16:TP=-1.5:LRA=9` (EBU R128 integrated loudness).
