"""Warm Vintage Parchment palette, Cyrillic stroke-weight parity, emoji stripping, and pagination tests (Commits 1 & 6)."""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from conftest import load_script_module


def test_warm_parchment_palette_and_cyrillic_bold_parity(tmp_path: Path):
    gw = load_script_module("legacy_gpx_widgets", ".agents/skills/build-timeline/scripts/gpx_widgets.py")

    out_ru = tmp_path / "sub_runners_joke_ru.png"
    gw.render_translation_subtitle_card(
        translation_text="Ребята, бегом быстрее будет!",
        out_png=out_ru,
        single_language=True,
        target_lang="ru",
    )
    out_strava = tmp_path / "strava_card.png"
    gw.render_strava_comparison_vintage_card(out_strava)

    for p in (out_ru, out_strava):
        with Image.open(p) as im:
            assert im.size == (3840, 2160)
            assert im.mode == "RGBA"
            bbox = im.getbbox()
            assert bbox is not None, f"{p.name} rendered completely transparent!"
            crop = im.crop(bbox)
            colors = crop.getcolors(maxcolors=200_000) or []
            rgb_set = {(r, g, b) for _cnt, (r, g, b, a) in colors if a > 200}
            # Warm Parchment (#F4EFE6 = 244,239,230) and Postmark Crimson (#B83A2A = 184,58,42)
            assert any(abs(r - 244) <= 4 and abs(g - 239) <= 4 and abs(b - 230) <= 4 for (r, g, b) in rgb_set)
            assert any(abs(r - 184) <= 4 and abs(g - 58) <= 4 and abs(b - 42) <= 4 for (r, g, b) in rgb_set)

    # Cyrillic font loader must select a Bold face (never thin fallback)
    cyr_font = gw.load_apple_font("card_title", 76, text="Привет Майорка")
    _, style = cyr_font.getname()
    assert "bold" in style.lower() or "heavy" in style.lower()


def test_auto_speech_pagination_primary_translation_and_emoji_ban(tmp_path: Path):
    from agvs_core.bookends import OUTRO_CREDITS_SUBLINE_EN, OUTRO_CREDITS_SUBLINE_RU
    from agvs_core.vintage_cards import (
        paginate_speech_segments,
        render_corner_map_widget,
        render_translation_subtitle_card,
        strip_unicode_emojis,
    )

    # 1. Comprehensive Unicode emoji stripping (including emojis outside legacy 10-char regex)
    cleaned = strip_unicode_emojis("Sunny ride 🎉☀️🇪🇸🚴‍♂️ to Pollensa! ✨")
    assert "🎉" not in cleaned and "☀️" not in cleaned and "🇪🇸" not in cleaned and "✨" not in cleaned
    assert "Sunny ride" in cleaned and "Pollensa!" in cleaned

    # 2. Automatic multi-sentence speech pagination (> 95 chars) with word-proportional durations summing to dur_s
    long_text = (
        "After forty-two years of continuous service at the village bakery, Encarnacio finally retired this autumn. "
        "Every cyclist climbing out of Pollensa still waves at her sunny terrace window."
    )
    pages = paginate_speech_segments(long_text, start_s=10.0, total_dur_s=8.0, max_chars_per_page=95)
    assert len(pages) >= 2
    assert round(sum(p["dur_s"] for p in pages), 2) == pytest.approx(8.0, abs=0.02)
    assert pages[0]["start_s"] == pytest.approx(10.0, abs=0.01)
    assert pages[1]["start_s"] == pytest.approx(10.0 + pages[0]["dur_s"], abs=0.02)

    # 3. Bilingual card: Primary translation is rendered ABOVE dimmer spoken original
    bi_png = tmp_path / "bilingual_card.png"
    layout_meta = render_translation_subtitle_card(
        spoken_text="¡Hola amigos, buen viaje!",
        translation_text="Hello friends, have a great ride!",
        out_png=bi_png,
        single_language=False,
        target_lang="en",
        return_layout_meta=True,
    )
    assert layout_meta["translation_y"] < layout_meta["spoken_y"]
    assert layout_meta["translation_font_pt"] > layout_meta["spoken_font_pt"]

    # 4. Localized RU metric corner map header & Google AI Ultra bookend credits
    pts = [
        {"lat": 39.88, "lon": 3.01, "ele": 120.0, "ele_ft": 394, "dist_mi": 0.0, "dist_km": 0.0},
        {"lat": 39.89, "lon": 2.95, "ele": 515.0, "ele_ft": 1690, "dist_mi": 8.5, "dist_km": 13.7},
    ]
    ru_map = tmp_path / "map_ru.png"
    hdr = render_corner_map_widget(pts, 1, "Перевал Фемения", ru_map, lang="ru", return_header_text=True)
    assert "КМ" in hdr and "М" in hdr and "MILE" not in hdr

    assert "ARGON QUOTAS" not in OUTRO_CREDITS_SUBLINE_EN.upper()
    assert "4K" in OUTRO_CREDITS_SUBLINE_EN and "4K" in OUTRO_CREDITS_SUBLINE_RU
