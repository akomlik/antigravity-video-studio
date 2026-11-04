# Sound Design Library (`03_Audio_Library/02_SFX/`)

Curated and translated from Igor Brehov's 209-sound cinematic SFX package (*«Звуки для саунд-дизайна»*). All 209 `.wav` files are 48 kHz, 24-bit stereo, normalized to `-1.0 dBFS` (`-6.0 dBFS` for ambient pads), and indexed in [`catalog.json`](./03_Audio_Library/02_SFX/catalog.json) with exact **`duration_ms`** and **`peak_ms`** (the exact millisecond of peak loudness).

## Peak-Alignment Rule for AI Timeline Placement (`Track A3`)
When placing any SFX on Audio Track **`A3`**:
- **Align `peak_ms` to the visual peak of motion or cut boundary:** Every entry in `catalog.json` specifies `peak_ms`. Calculate the timeline start time as:
  $$\text{SFX Start Time (s)} = \text{Visual Event / Cut Timestamp (s)} - \frac{\text{peak\_ms}}{1000.0}$$
  so the crest of the whoosh, riser, shutter click, or impact lands on the exact frame of the visual transition or caption pop-up.
- **Restraint Law:** Never place an SFX on every routine camera angle cut. Reserve `A3` SFX for title cards, `Scene 00` flashback boundaries, lower-third punchline captions (`09_UI_Appears`, `14_Success_Done`, `15_Error_Wrong`), still photo freeze-frames (`12_Camera_Shutter`), and rolling telemetry/price counters (`10_Ticks_Clicks`).

## English Folder Mapping & Gain Guide (Relative to `A1` Voice / Foreground)

| English Folder (`02_SFX/`) | Original Russian Name | Files | Editorial Usage in `@akomlik` Videos | Gain Relative to Voice (`A1`) |
| :--- | :--- | :--- | :--- | :--- |
| `01_Whooshes_Soft/` | `01_Вжухи_мягкие` | 20 | Lower-third caption entries/exits, subtle UI slides | `-6` to `-10 dB` quieter |
| `02_Whooshes_Medium/` | `02_Вжухи_средние` | 20 | Medium movement, Ken Burns slide transitions, map pops | `-4` to `-7 dB` quieter |
| `03_Whooshes_Cinematic/` | `03_Вжухи_крупные` | 15 | Opening title reveal, entering/exiting `Scene 00` flashback | Near voice level (`0` to `-3 dB`) |
| `04_Drops_Falls/` | `04_Падения_уходы` | 10 | Object dropping off-screen, comedic deflation (e.g. brake pad drop) | `-4` to `-7 dB` quieter |
| `05_Risers/` | `05_Подъёмы` | 12 | Build-up before a main chapter title or key punchline reveal | `-3` to `-6 dB` quieter |
| `06_Reverse_Swells/` | `06_Реверс_вдохи` | 8 | Inhale swell leading directly into a flashback or scenic vista | `-4` to `-8 dB` quieter |
| `07_Impacts/` | `07_Удары` | 15 | Main title card hit, dramatic milestone accent | At or slightly above voice |
| `08_Sub_Drops/` | `08_Саб_дропы` | 6 | Deep bass drop under black screen or dramatic slow-motion | `-3` to `-6 dB` quieter |
| `09_UI_Appears/` | `09_Появления_интерфейса` | 15 | Lower-third story captions (`V2`), GPX telemetry badge pop-up | `-6` to `-10 dB` quieter |
| `10_Ticks_Clicks/` | `10_Тики_щелчки` | 24 | Rolling numbers (`tick_counter`), €20 $\rightarrow$ €30 inflation counter, GPX stats | `-10` to `-12 dB` quieter |
| `11_Screen_Taps/` | `11_Касания_экрана` | 8 | Phone/camera button press animations | `-8` to `-10 dB` quieter |
| `12_Camera_Shutter/` | `12_Затвор_камеры` | 4 | Still photo freeze-frames (`IMG_*.jpg`), 1977+ B&W & 1980–84 archival snaps | `-6` to `-8 dB` quieter |
| `13_Notifications/` | `13_Уведомления` | 12 | Soft alert chime on map pin or tip callout | `-6` to `-10 dB` quieter |
| `14_Success_Done/` | `14_Итог_готово` | 8 | Mission accomplished chime (jacket found, home-cooked *Llampuga* payoff) | `-4` to `-8 dB` quieter |
| `15_Error_Wrong/` | `15_Ошибка` | 6 | Comedic fail / veto tone (Bar Casa Miss veto, un-chewable *entrecôte*, brake pad!) | `-6` to `-10 dB` quieter |
| `16_Shimmer_Sparkle/` | `16_Блеск` | 8 | "Wow" reveal, rainbow on the ride, fresh croissant at Forn Can Torres | `-10` to `-12 dB` quieter |
| `17_Keyboard_Typing/` | `17_Клавиатура` | 4 | Typewriter effect on archival dates or chapter headers | `-10` to `-12 dB` quieter |
| `18_Transitions/` | `18_Переходы` | 8 | Full chapter boundary transition (riser into impact) | Near voice level |
| `19_Ambient_Pads/` | `19_Подложки_эмбиент` | 6 | 30s subtle atmospheric bed under voice when `A2` music is paused | `-20 dB` under voice |
