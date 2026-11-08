
We are adding signature iMovie-style (but funny, unique, and data-driven) Starting Title and Finishing Credit bookends to our `antigravity-video-studio` pipeline so every video feels like an unmistakable **AGVS (AntiGravity Video Studio)** production.

Please implement this in 3 steps:

### 1. New Generator Script: `agvs_bookends.py`
Create a Python module `agvs_bookends.py` (using Pillow/Matplotlib/FFmpeg, matching our `gpx_widgets.py` styling) that generates two 4K (3840x2160) composited bookend assets or FFmpeg filtergraphs for a project folder:

#### A. Opening "AGVS Pre-Flight Postcard" (First 3.5 seconds of Scene 00)
Instead of cutting away from the video, composite the first 3.5 seconds of the opening clip inside a slightly tilted (-2.0 degree) white-bordered "Postcard Frame" (70% scale, centered-right with soft drop shadow) over a 4K themed background canvas:
1. **Background Canvas:**
   - If a `.gpx` file exists in the project, render a stylizedvintage-parchment or dark-slate topographic route map canvas showing the full GPX route trace, a red start pin, and a bold location tag (e.g., `📍 MALLORCA // BONAIRE → SA BATALLA`).
   - If no `.gpx` file exists, use a blurred, warm-tinted 4K frame from the project's hero photo with a travel-grid texture overlay.
2. **Top-Left AGVS Studio Stamp:**
   - Render a distressed aerospace/rubber-stamp badge:
     `🚀 AGVS // ANTIGRAVITY VIDEO STUDIO`
   - Below the badge, render a dynamic witty tagline selected from `Storyboard.md` (or auto-selected by ride stats):
     - If total climbing > 1,500 ft: `"Gravity Reduction Module: FAILED (Climbing Anyway)"`
     - If flat ride / cafe stop: `"Powered by Espresso, Pastries & 0.2s FFmpeg Remux"`
     - If group ride: `"No Riders Were Dropped in the Making of This Film (Mostly)"`
     - If off-bike / travel: `"Off-Bike Field Division • Zero Watts Required"`
3. **Bottom Ticket-Stub Manifest Bar:**
   - Clean horizontal strip at the bottom:
     `📅 {date}   |   🎬 {short_title}   |   🚴 {distance_mi} mi • ⛰️ {elevation_ft} ft`
4. **Transition to Full Screen:**
   - At `t = 3.5s` (or right when the first Voice-Over A4 clip begins), smoothly transition/cut from the postcard frame to 100% full-screen video.

#### B. Closing "AGVS Post-Ride Bar Tab & Credits" (Final 4.5 seconds of Final Scene)
Do NOT cut to a dead black screen. Take the final 4.5 seconds of the last timeline clip (keeping its live A1 ambient audio/banter and A2 music tail intact!):
1. **Left Side (Tilted +1.5° Postcard Frame, 58% scale):**
   - Continues playing the final 4.5 seconds of live video inside a warm white-bordered postcard frame with `"Wish you were here! — AGVS"` script on the bottom border.
2. **Right Side ("AGVS Production Receipt / Credits Card"):**
   - Header: `CREATED BY ALEXANDER KOMLIK`
   - Subheader: `AN ANTIGRAVITY VIDEO STUDIO PRODUCTION`
   - Auto-populated credit lines read from `Storyboard.md` Section 5 YAML (with sensible defaults from `my_digital_brain.md`):
     - **THE CREW / PELOTON:** (e.g., Bruce, Nina, Brian, Ian — with short funny role titles from Storyboard)
     - **LEAD STEED:** (e.g., `Trek Madone 7 (Craigslist Class of '16)`)
     - **CAMERA & GIMBAL:** `BleeqUP Ranger AI Glasses (100% Organic Head-Turns) & iPhone 15 Pro`
     - **TELEMETRY:** `Garmin Edge 1040 (Smoothed — 0% Fake Altimeter Spikes)`
     - **MEMORY BANK:** `my_digital_brain.md`
     - **FUEL & SPONSORS:** (Auto-extracted cafe/food stops from Storyboard, e.g., `Forn Can Rafel • Pro Cycle Cafe VIP Card • 1x Cold Shandy`)
3. **Bottom Footer Stamp:**
   - `"⚠️ 0% Gravity Guaranteed on Descents Only  •  No Argon Quotas Were Harmed in This Render"`

### 2. Update `Storyboard.md` Schema & `/storyboard` Skill
In `Storyboard.md` Section 5 (Production & YouTube Publishing Spec YAML), add a new `agvs_bookends:` block that `/storyboard` auto-drafts with funny, episode-specific jokes based on the clips and `my_digital_brain.md`:
```yaml
agvs_bookends:
  enabled: true
  intro_duration_s: 3.5
  outro_duration_s: 4.5
  studio_motto: "Gravity Reduction Module: FAILED (Climbing Anyway)"
  location_badge: "MALLORCA // BONAIRE ➔ COLL DE SA BATALLA"
  cast_credits:
    - "Bruce — Chief Recovery-Ride Trap Setter"
    - "Ian — 43 mph Descent Draft Tractor"
    - "Pete — 3rd Floor Post-Ride Shandy Consultant"
  steed_credit: "Trek Madone 7 (Craigslist '16 Vintage)"
  fuel_sponsors: "Sa Ruta Verda • Almond Cake • Pro Cycle Bar"

```

### 3. Wire into `/build-timeline` & Keep Lossless Remux Intact

* In `/build-timeline`, automatically invoke `agvs_bookends.py` before final assembly so the 3.5s opening postcard and 4.5s closing credit card are placed on the master timeline without creating any V1 black-frame gaps (`verify_and_repair_v1_continuity` must still pass).
* Ensure A4 Voice-Over starts after `t = 3.5s` (or ducks cleanly) and finishes before the final 4.5s outro card so live finale dialogue/laughter on A1 or the final music swell on A2 shines during the credits.
* Keep all bookend text universal across editions so `option_b` (`_UA.mp4` and `_RU.mp4`) continues to use 0.2s lossless `ffmpeg -c:v copy` remuxing with zero video re-encoding.

