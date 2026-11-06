#!/usr/bin/env python3
"""
fetch_creatormix_catalog.py
Direct CreatorMix (creatormix.com) catalog indexer, search engine, and auto-downloader.

Why this exists:
- Eliminates the friction of manual browser driving / clicking to find background music.
- CreatorMix hosts 130+ royalty-free, copyright-safe tracks on a fast CDN with direct MP3 streaming/download URLs.
- Caches the catalog in `03_Audio_Library/01_Curated_BGM/creatormix_online_catalog.json`.
- Integrates with `save_music_track.py` to auto-download, format to `[BPM]_[Mood]_[TrackName]_[Artist].mp3`,
  and file into `03_Audio_Library/01_Curated_BGM/<Category>/`.
- Supports filtering out previously used tracks from `04_Project_Catalog/` to enforce the Anti-Monotony Non-Reuse Law!
"""

import argparse
import concurrent.futures
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
BGM_ROOT = STUDIO_ROOT / "03_Audio_Library/01_Curated_BGM"
CATALOG_CACHE = BGM_ROOT / "creatormix_online_catalog.json"
CATALOG_PROJECTS_DIR = STUDIO_ROOT / "04_Project_Catalog"

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

# Standard genre-to-BGM category & BPM mapping for CreatorMix genres
GENRE_CATEGORY_MAP = {
    "chillhop": ("04_Warm_Social_And_Retro", 85, "WarmChillhop"),
    "lofi": ("04_Warm_Social_And_Retro", 84, "RelaxedLofi"),
    "house": ("01_Rolling_Cadence", 120, "SunnyHouse"),
    "synthwave": ("01_Rolling_Cadence", 118, "CoastalSynthwave"),
    "edm": ("03_Punchy_Climbs", 128, "DrivingEdm"),
    "rock": ("03_Punchy_Climbs", 125, "PunchyRock"),
    "cyberpunk": ("03_Punchy_Climbs", 130, "CyberEnergy"),
    "trap": ("03_Punchy_Climbs", 135, "TrapCadence"),
    "mixes": ("02_Scenic_Wonder", 95, "ScenicAmbient"),
}


def get_previously_used_tracks(studio_root: Path = STUDIO_ROOT) -> set[str]:
    """Scans all existing projects in 04_Project_Catalog/ to find already-used BGM track names/titles."""
    used = set()
    cat_dir = studio_root / "04_Project_Catalog"
    if not cat_dir.exists():
        return used

    for p in cat_dir.rglob("Storyboard.md"):
        try:
            txt = p.read_text(encoding="utf-8")
            for m in re.finditer(r"([0-9]{2,3}bpm_[^_]+_([^_]+)_[^.\s]+\.mp3)", txt):
                used.add(m.group(1).lower())
                used.add(m.group(2).lower())
        except Exception:
            pass

    for fc in cat_dir.rglob("*.fcproj"):
        try:
            txt = fc.read_text(encoding="utf-8")
            for m in re.finditer(r"\"name\":\s*\"([^\"]+\.mp3)\"", txt):
                fname = m.group(1).lower()
                used.add(fname)
                parts = fname.split("_")
                if len(parts) >= 3:
                    used.add(parts[2].lower())
        except Exception:
            pass

    return used


def fetch_album_tracks(album_id: int) -> list[dict]:
    url = f"https://creatormix.com/album/-{album_id}.html"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", errors="ignore")
        alb_m = re.search(r"data-track-info=\"album\">([^<]+)</a>", html)
        album_name = alb_m.group(1).strip() if alb_m else f"Album {album_id}"

        tracks = []
        items = re.findall(
            r"<div class=\"track-item\"[^>]*data-source=\"([^\"]+)\"[^>]*>.*?<div class=\"track-name\">([^<]+)</div>.*?data-track-info-length=\"(\d+)\"",
            html,
            re.DOTALL,
        )
        for src, name, sec in items:
            m = re.search(r"creatormix/([^/]+)/([^/]+)/mp3/", src)
            genre = m.group(1).lower() if m else "general"
            tracks.append({
                "album_id": album_id,
                "album": album_name,
                "genre": genre,
                "title": name.strip(),
                "duration_s": int(sec),
                "duration_formatted": f"{int(sec)//60}:{int(sec)%60:02d}",
                "stream_url": src,
                "clean_url": src.split("?")[0],
                "artist": "CreatorMix",
            })
        return tracks
    except Exception:
        return []


def build_or_load_catalog(refresh: bool = False) -> list[dict]:
    if not refresh and CATALOG_CACHE.exists():
        try:
            data = json.loads(CATALOG_CACHE.read_text(encoding="utf-8"))
            if data.get("tracks"):
                return data["tracks"]
        except Exception:
            pass

    print("Fetching complete CreatorMix catalog (probing albums 1..104)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        res = list(ex.map(fetch_album_tracks, range(1, 105)))

    all_tracks = [t for sub in res for t in sub]
    seen = set()
    unique_tracks = []
    for t in all_tracks:
        key = (t["album"], t["title"])
        if key not in seen:
            seen.add(key)
            unique_tracks.append(t)

    CATALOG_CACHE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": str(CATALOG_CACHE.stat().st_mtime if CATALOG_CACHE.exists() else ""),
        "total_tracks": len(unique_tracks),
        "tracks": unique_tracks,
    }
    CATALOG_CACHE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Cached {len(unique_tracks)} CreatorMix tracks -> {CATALOG_CACHE}")
    return unique_tracks


def search_catalog(
    query: str = "",
    genre: str = "",
    max_duration_s: int = 180,
    min_duration_s: int = 45,
    exclude_used: bool = True,
    limit: int = 10,
) -> list[dict]:
    tracks = build_or_load_catalog(refresh=False)
    used_tokens = get_previously_used_tracks() if exclude_used else set()

    results = []
    q_lower = query.lower().strip()
    g_lower = genre.lower().strip()

    for t in tracks:
        dur = t.get("duration_s", 0)
        if dur > max_duration_s or dur < min_duration_s:
            continue

        t_title = t.get("title", "").lower()
        t_album = t.get("album", "").lower()
        t_genre = t.get("genre", "").lower()

        # Anti-Monotony Check: skip if used in a past project
        title_clean = re.sub(r"[^a-z0-9]", "", t_title)
        if exclude_used and any(token in title_clean or title_clean in token for token in used_tokens if len(token) > 3):
            continue

        if g_lower and g_lower not in t_genre and g_lower not in t_album:
            continue

        if q_lower:
            match = q_lower in t_title or q_lower in t_album or q_lower in t_genre
            if not match:
                continue

        results.append(t)
        if len(results) >= limit:
            break

    return results


def download_and_import_track(track: dict, category: str = None, bpm: int = None, mood: str = None) -> Path:
    """Downloads track via clean_url / stream_url, formats filename, and moves into 03_Audio_Library/01_Curated_BGM/."""
    genre = track.get("genre", "general").lower()
    default_cat, default_bpm, default_mood = GENRE_CATEGORY_MAP.get(genre, ("01_Rolling_Cadence", 115, "UpbeatBeat"))

    target_category = category or default_cat
    target_bpm = bpm or default_bpm
    target_mood = mood or default_mood
    clean_title = "".join(w.capitalize() for w in re.findall(r"[A-Za-z0-9]+", track["title"])) or "Track"
    dest_name = f"{target_bpm:03d}bpm_{target_mood}_{clean_title}_Creatormix.mp3"

    dest_dir = BGM_ROOT / target_category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / dest_name

    if dest_path.exists():
        print(f"Track already downloaded: {dest_path}")
        return dest_path

    print(f"Downloading [{track['genre'].upper()}] '{track['title']}' ({track['duration_formatted']}) from CreatorMix...")
    stream_url = track.get("stream_url", "")
    try:
        req = urllib.request.Request(stream_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception:
        # Re-fetch album to get fresh signed token
        album_id = track.get("album_id")
        if album_id:
            fresh_tracks = fetch_album_tracks(album_id)
            for ft in fresh_tracks:
                if ft["title"].strip().lower() == track["title"].strip().lower():
                    stream_url = ft["stream_url"]
                    break
        req = urllib.request.Request(stream_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()

    with dest_path.open("wb") as out_f:
        out_f.write(data)

    # Update music_catalog.json index
    catalog_json = BGM_ROOT / "music_catalog.json"
    catalog = {"tracks": []}
    if catalog_json.exists():
        try:
            catalog = json.loads(catalog_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    entry = {
        "filename": dest_name,
        "path": f"03_Audio_Library/01_Curated_BGM/{target_category}/{dest_name}",
        "relpath": f"{target_category}/{dest_name}",
        "category": target_category,
        "bpm": target_bpm,
        "beat_interval_s": round(60.0 / max(target_bpm, 1), 3),
        "mood": target_mood,
        "title": track["title"],
        "artist": "CreatorMix",
        "album": track.get("album", "CreatorMix"),
        "source_site": "CreatorMix",
        "duration_s": track.get("duration_s"),
        "notes": f"Auto-fetched from CreatorMix (Album: {track.get('album')})",
    }
    catalog["tracks"] = [t for t in catalog.get("tracks", []) if t.get("filename") != dest_name]
    catalog["tracks"].append(entry)
    catalog_json.write_text(json.dumps(catalog, indent=2), encoding="utf-8")

    print(f"✅ Downloaded and indexed: {dest_path.name} in {target_category}/")
    return dest_path


def main():
    p = argparse.ArgumentParser(description="Direct CreatorMix Catalog Search, Non-Reuse Filter & Downloader")
    p.add_argument("--search", default="", help="Keyword search (e.g. 'ocean', 'chill', 'arcade')")
    p.add_argument("--genre", default="", help="Genre filter: chillhop, lofi, house, synthwave, edm, rock, cyberpunk, trap, mixes")
    p.add_argument("--max-duration", type=int, default=180, help="Max duration in seconds (default: 180s for < 3:00 rule)")
    p.add_argument("--allow-used", action="store_true", help="Allow tracks that were already used in past projects")
    p.add_argument("--limit", type=int, default=10, help="Max results to show")
    p.add_argument("--download-idx", type=int, help="1-based index from search results to immediately download")
    p.add_argument("--refresh-cache", action="store_true", help="Force re-fetch of the 134-track catalog from creatormix.com")
    args = p.parse_args()

    if args.refresh_cache:
        build_or_load_catalog(refresh=True)

    used = get_previously_used_tracks()
    results = search_catalog(
        query=args.search,
        genre=args.genre,
        max_duration_s=args.max_duration,
        exclude_used=not args.allow_used,
        limit=args.limit,
    )

    print(f"\nCreatorMix Online Catalog ({len(results)} matches, {len(used)} past project tracks excluded):")
    for i, t in enumerate(results, 1):
        print(f"  [{i}] {t['title']} ({t['duration_formatted']}) | Genre: {t['genre'].upper()} | Album: {t['album']}")

    if args.download_idx and 1 <= args.download_idx <= len(results):
        target_track = results[args.download_idx - 1]
        download_and_import_track(target_track)


if __name__ == "__main__":
    main()
