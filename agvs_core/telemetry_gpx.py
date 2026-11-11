"""
agvs_core/telemetry_gpx.py
Unified GPX 1.1 parser (>= 40m horizontal grade smoothing + 3s rolling speed/power),
ride-date primary GPX selector, HUD visibility policy, and Mallorca RU/UA phonetic toponym engine.
"""

from __future__ import annotations

import datetime as dt
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Optional

ACTIVITY_SPEED_THRESHOLDS: dict[str, float] = {
    "cycling_ride": 2.0,
    "cycling": 2.0,
    "ride": 2.0,
    "run": 1.5,
    "running": 1.5,
    "hike_outdoor": 0.8,
    "hike": 0.8,
    "hiking": 0.8,
    "walk": 0.8,
    "walking": 0.8,
}

# Mallorca Yeísmo Phonetic Transliteration Rules (`ll` -> `й` between/before vowels; `l` before consonant)
_FORBIDDEN_TOPONYM_PATTERNS: list[tuple[re.Pattern[str], str, str]] = [
    (re.compile(r"Мальорк([а-яіїєґ']*)", re.IGNORECASE), r"Майорк\1", r"Майорк\1"),
    (re.compile(r"Поль[еє]нс([а-яіїєґ']*)", re.IGNORECASE), r"Пойенс\1", r"Поєнс\1"),
    (re.compile(r"Соль[еє]р([а-яіїєґ']*)", re.IGNORECASE), r"Сойер\1", r"Соєр\1"),
    (re.compile(r"\bЛьюк([а-яіїєґ']*)", re.IGNORECASE), r"Йук\1", r"Йук\1"),
    (re.compile(r"Вальдемосс?([а-яіїєґ']*)", re.IGNORECASE), r"Валдемос\1", r"Валдемос\1"),
]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dp / 2.0) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def parse_gpx_with_summary(
    gpx_path: Path,
    min_grade_window_m: float = 40.0,
) -> tuple[list[dict[str, Any]], float, float]:
    """
    Parses a Garmin/Strava GPX 1.1 file into a unified Imperial + Metric 1Hz stream.
    Enforces a `>= 40.0 m` horizontal lookback window so quantized 0.2m-1.0m barometric steps
    never produce artificial 18-22% gradient spikes.
    """
    root = ET.parse(gpx_path).getroot()
    pts: list[dict[str, Any]] = []
    tot_m = 0.0
    tot_elev_gain_m = 0.0

    for trkpt in root.iter():
        if not trkpt.tag.endswith("trkpt"):
            continue
        lat = float(trkpt.attrib["lat"])
        lon = float(trkpt.attrib["lon"])
        ele: float = 0.0
        ts: Optional[dt.datetime] = None
        hr: Optional[int] = None
        cad: Optional[int] = None
        pwr: Optional[int] = None

        for child in trkpt.iter():
            tag = child.tag.split("}")[-1]
            if tag == "ele" and child.text:
                ele = float(child.text)
            elif tag == "time" and child.text:
                ts = dt.datetime.fromisoformat(child.text.strip().replace("Z", "+00:00"))
            elif tag == "hr" and child.text:
                hr = int(float(child.text))
            elif tag == "cad" and child.text:
                cad = int(float(child.text))
            elif tag in ("power", "watts") and child.text:
                pwr = int(float(child.text))

        if ts is None:
            continue

        spd_kmh = 0.0
        grad_pct = 0.0
        if pts:
            prev = pts[-1]
            d = haversine_m(prev["lat"], prev["lon"], lat, lon)
            dts = max((ts - prev["time"]).total_seconds(), 0.001)
            spd_kmh = (d / dts) * 3.6
            tot_m += d
            dele = ele - prev["_raw_ele"]
            if dele > 0.2:
                tot_elev_gain_m += dele

            # Search backward for the first point at least `min_grade_window_m` behind along the cumulative track
            anchor = pts[0]
            for p_back in reversed(pts):
                if (tot_m - p_back["_tot_m"]) >= min_grade_window_m:
                    anchor = p_back
                    break
            horiz_m = tot_m - anchor["_tot_m"]
            if horiz_m >= max(15.0, min_grade_window_m * 0.4):
                grad_pct = ((ele - anchor["_raw_ele"]) / horiz_m) * 100.0

        clamped_grad = round(max(-25.0, min(25.0, grad_pct)), 1)
        clamped_spd_kmh = round(min(spd_kmh, 93.3), 1)
        clamped_spd_mph = round(min(spd_kmh * 0.621371, 58.0), 1)

        pts.append({
            "time": ts,
            "lat": lat,
            "lon": lon,
            "_raw_ele": ele,
            "_tot_m": tot_m,
            "ele": round(ele, 1),
            "ele_m": int(round(ele)),
            "ele_ft": int(round(ele * 3.28084)),
            "dist_km": round(tot_m / 1000.0, 2),
            "dist_mi": round(tot_m / 1609.344, 2),
            "speed_kmh": clamped_spd_kmh,
            "spd_kmh": clamped_spd_kmh,
            "spd_mph": clamped_spd_mph,
            "grad_pct": clamped_grad,
            "gradient_pct": clamped_grad,
            "hr": hr if hr is not None else 0,
            "cad": cad if cad is not None else 0,
            "pwr": pwr if pwr is not None else 0,
            "power": pwr,
        })

    # 3-second rolling average for speed, power, and gradient to prevent 1Hz integer-step flicker
    if len(pts) > 3:
        raw_spd_mph = [p["spd_mph"] for p in pts]
        raw_spd_kmh = [p["speed_kmh"] for p in pts]
        raw_pwr = [p["pwr"] for p in pts]
        raw_grad = [p["grad_pct"] for p in pts]
        for i in range(len(pts)):
            i0, i1 = max(0, i - 1), min(len(pts), i + 2)
            n_w = i1 - i0
            pts[i]["spd_mph"] = round(sum(raw_spd_mph[i0:i1]) / n_w, 1)
            avg_kmh = round(sum(raw_spd_kmh[i0:i1]) / n_w, 1)
            pts[i]["speed_kmh"] = avg_kmh
            pts[i]["spd_kmh"] = avg_kmh
            avg_grad = round(sum(raw_grad[i0:i1]) / n_w, 1)
            pts[i]["grad_pct"] = avg_grad
            pts[i]["gradient_pct"] = avg_grad
            if any(raw_pwr[i0:i1]):
                avg_p = int(round(sum(raw_pwr[i0:i1]) / n_w))
                pts[i]["pwr"] = avg_p
                pts[i]["power"] = avg_p

    for p in pts:
        p.pop("_raw_ele", None)
        p.pop("_tot_m", None)

    return pts, round(tot_m / 1000.0, 2), round(tot_elev_gain_m, 1)


def load_gpx_track(gpx_path: Path, min_grade_window_m: float = 40.0) -> list[dict[str, Any]]:
    """Returns the smoothed 1Hz GPX trackpoint stream (`>= 40m` grade lookback)."""
    pts, _, _ = parse_gpx_with_summary(gpx_path, min_grade_window_m=min_grade_window_m)
    return pts


def _probe_gpx_date_and_count(gpx_path: Path) -> tuple[Optional[dt.date], int]:
    try:
        root = ET.parse(gpx_path).getroot()
    except Exception:
        return None, 0
    first_date: Optional[dt.date] = None
    count = 0
    for trkpt in root.iter():
        if not trkpt.tag.endswith("trkpt"):
            continue
        count += 1
        if first_date is None:
            for c in trkpt.iter():
                if c.tag.split("}")[-1] == "time" and c.text:
                    try:
                        ts = dt.datetime.fromisoformat(c.text.strip().replace("Z", "+00:00"))
                        first_date = ts.date()
                    except ValueError:
                        pass
                    break
    return first_date, count


def select_primary_ride_gpx(
    folder: Path,
    project_name: Optional[str] = None,
) -> tuple[Optional[Path], list[Path]]:
    """
    Selects the primary ride GPX in `folder` by matching `<trkpt><time>` date against `YYYY-MM-DD`
    in `project_name` (or `folder.name`) before falling back to largest trackpoint count.
    Returns `(primary_gpx, archival_gpx_list)`.
    """
    candidates = sorted({*folder.glob("*.gpx"), *folder.glob("*.GPX")})
    if not candidates:
        return None, []
    if len(candidates) == 1:
        return candidates[0], []

    ref_name = project_name or folder.name
    m_date = re.search(r"(\d{4}-\d{2}-\d{2})", ref_name)
    target_date = dt.date.fromisoformat(m_date.group(1)) if m_date else None

    scored: list[tuple[int, int, Path]] = []
    for gp in candidates:
        g_date, n_pts = _probe_gpx_date_and_count(gp)
        date_rank = 0
        if target_date is not None and g_date is not None:
            day_diff = abs((g_date - target_date).days)
            if day_diff == 0:
                date_rank = 2
            elif day_diff == 1:
                date_rank = 1
        scored.append((date_rank, n_pts, gp))

    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    primary = scored[0][2]
    archival = [gp for gp in candidates if gp != primary]
    return primary, archival


def should_show_telemetry_hud(
    clip_name: str,
    gpx_points: Optional[list[dict[str, Any]]] = None,
    clip_ts: Optional[dt.datetime] = None,
    rolling_speed_mph: Optional[float] = None,
    activity_type: str = "cycling_ride",
    mode: str = "auto",
    window_s: float = 3.0,
    speed_threshold_mph: Optional[float] = None,
) -> bool:
    """Evaluates whether the Telemetry HUD should be visible on a clip."""
    if clip_name.lower().endswith((".jpg", ".jpeg", ".png", ".heic")):
        return False

    mode_clean = (mode or "auto").strip().lower()
    if mode_clean == "off":
        return False
    if mode_clean == "always":
        return True

    if speed_threshold_mph is None:
        act_key = (activity_type or "cycling_ride").strip().lower()
        speed_threshold_mph = ACTIVITY_SPEED_THRESHOLDS.get(act_key, 2.0)

    if rolling_speed_mph is not None:
        return rolling_speed_mph > speed_threshold_mph

    if gpx_points and clip_ts is not None:
        pts_in_win = [p for p in gpx_points if abs((p["time"] - clip_ts).total_seconds()) <= window_s]
        if pts_in_win:
            avg_spd = sum(p["spd_mph"] for p in pts_in_win) / len(pts_in_win)
            return avg_spd > speed_threshold_mph

    return False


def validate_mallorca_toponyms(text: str) -> list[str]:
    """Returns a list of forbidden orthographical Mallorca toponym matches in Russian/Ukrainian text."""
    if not text:
        return []
    violations: list[str] = []
    for pat, _ru_rep, _ua_rep in _FORBIDDEN_TOPONYM_PATTERNS:
        for m in pat.finditer(text):
            violations.append(m.group(0))
    return violations


def normalize_mallorca_toponyms(text: str, lang: str = "ru") -> str:
    """Normalizes RU/UA Mallorca place names to phonetic yeísmo spelling (`Майорка`, `Пойенса`/`Поєнса`, `Сойер`/`Соєр`, `Йук`, `Валдемоса`)."""
    if not text:
        return text
    out = text
    is_ua = lang.strip().lower() in ("ua", "uk")
    for pat, ru_rep, ua_rep in _FORBIDDEN_TOPONYM_PATTERNS:
        rep = ua_rep if is_ua else ru_rep
        out = pat.sub(rep, out)
    return out
