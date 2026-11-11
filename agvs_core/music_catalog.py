"""
agvs_core/music_catalog.py
Unified CreatorMix + local BGM search, Anti-Monotony Non-Reuse filter,
standardized [BPM]_[Mood]_[TrackName]_[Artist].mp3 importer, and timeline A2 swapper.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import shutil
import urllib.request
from pathlib import Path
from typing import Any, Optional

from agvs_core.config import get_bgm_root, get_studio_root

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}

CATEGORIES = [
    "01_Rolling_Cadence",
    "02_Scenic_Wonder",
    "03_Punchy_Climbs",
    "04_Warm_Social_And_Retro",
    "05_Short_Transitions",
]

GENRE_CATEGORY_MAP: dict[str, tuple[str, int, str]] = {
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


def camel_clean(text: str) -> str:
    """Converts 'Circuit Rush - The Mini Vandals' or 'circuit_rush' into 'CircuitRush'."""
    words = re.findall(r"[A-Za-z0-9]+", text)
    return "".join(w.capitalize() for w in words) or "Untitled"


def get_previously_used_tracks(studio_root: Optional[Path] = None) -> set[str]:
    """Scans all existing projects in 04_Project_Catalog/ to find already-used BGM track names/titles."""
    root = studio_root or get_studio_root()
    used: set[str] = set()
    cat_dir = root / "04_Project_Catalog"
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

    for ts in cat_dir.rglob("timeline_spec.json"):
        try:
            data = json.loads(ts.read_text(encoding="utf-8"))
            tracks = []
            if data.get("bgm_track"):
                tracks.append(str(data["bgm_track"]))
            for bt in data.get("bgm_tracks") or []:
                if isinstance(bt, dict) and bt.get("track"):
                    tracks.append(str(bt["track"]))
            for t_str in tracks:
                fname = Path(t_str).name.lower()
                used.add(fname)
                parts = fname.split("_")
                if len(parts) >= 3:
                    used.add(parts[2].lower())
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


def fetch_album_tracks(album_id: int) -> list[dict[str, Any]]:
    url = f"https://creatormix.com/album/-{album_id}.html"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", errors="ignore")
        alb_m = re.search(r"data-track-info=\"album\">([^<]+)</a>", html)
        album_name = alb_m.group(1).strip() if alb_m else f"Album {album_id}"

        tracks: list[dict[str, Any]] = []
        items = re.findall(
            r"<div class=\"track-item\"[^>]*data-source=\"([^\"]+)\"[^>]*>.*?<div class=\"track-name\">([^<]+)</div>.*?data-track-info-length=\"(\d+)\"",
            html,
            re.DOTALL,
        )
        for src, name, sec in items:
            m = re.search(r"creatormix/([^/]+)/([^/]+)/mp3/", src)
            genre = m.group(1).lower() if m else "general"
            tracks.append(
                {
                    "album_id": album_id,
                    "album": album_name,
                    "genre": genre,
                    "title": name.strip(),
                    "duration_s": int(sec),
                    "duration_formatted": f"{int(sec) // 60}:{int(sec) % 60:02d}",
                    "stream_url": src,
                    "clean_url": src.split("?")[0],
                    "artist": "CreatorMix",
                }
            )
        return tracks
    except Exception:
        return []


def build_or_load_catalog(refresh: bool = False, bgm_root: Optional[Path] = None) -> list[dict[str, Any]]:
    root = bgm_root or get_bgm_root()
    catalog_cache = root / "creatormix_online_catalog.json"
    if not refresh and catalog_cache.exists():
        try:
            data = json.loads(catalog_cache.read_text(encoding="utf-8"))
            if data.get("tracks"):
                return data["tracks"]
        except Exception:
            pass

    print("Fetching complete CreatorMix catalog (probing albums 1..104)...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as ex:
        res = list(ex.map(fetch_album_tracks, range(1, 105)))

    all_tracks = [t for sub in res for t in sub]
    seen: set[tuple[str, str]] = set()
    unique_tracks: list[dict[str, Any]] = []
    for t in all_tracks:
        key = (t["album"], t["title"])
        if key not in seen:
            seen.add(key)
            unique_tracks.append(t)

    catalog_cache.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "total_tracks": len(unique_tracks),
        "tracks": unique_tracks,
    }
    catalog_cache.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Cached {len(unique_tracks)} CreatorMix tracks -> {catalog_cache}")
    return unique_tracks


def search_catalog(
    query: str = "",
    genre: str = "",
    max_duration_s: int = 180,
    min_duration_s: int = 45,
    exclude_used: bool = True,
    limit: int = 10,
    studio_root: Optional[Path] = None,
) -> list[dict[str, Any]]:
    tracks = build_or_load_catalog(refresh=False)
    used_tokens = get_previously_used_tracks(studio_root=studio_root) if exclude_used else set()

    results: list[dict[str, Any]] = []
    q_lower = query.lower().strip()
    g_lower = genre.lower().strip()

    for t in tracks:
        dur = t.get("duration_s", 0)
        if dur > max_duration_s or dur < min_duration_s:
            continue

        t_title = t.get("title", "").lower()
        t_album = t.get("album", "").lower()
        t_genre = t.get("genre", "").lower()

        title_clean = re.sub(r"[^a-z0-9]", "", t_title)
        if exclude_used and any(token in title_clean or title_clean in token for token in used_tokens if len(token) > 3):
            continue

        if g_lower and g_lower not in t_genre and g_lower not in t_album:
            continue

        if q_lower:
            if not (q_lower in t_title or q_lower in t_album or q_lower in t_genre):
                continue

        results.append(t)
        if len(results) >= limit:
            break

    return results


def _upsert_music_catalog_entry(bgm_root: Path, entry: dict[str, Any]) -> None:
    catalog_json = bgm_root / "music_catalog.json"
    catalog: dict[str, Any] = {"tracks": []}
    if catalog_json.exists():
        try:
            catalog = json.loads(catalog_json.read_text(encoding="utf-8"))
        except Exception:
            catalog = {"tracks": []}
    catalog["tracks"] = [t for t in catalog.get("tracks", []) if t.get("filename") != entry["filename"]]
    catalog["tracks"].append(entry)
    catalog_json.parent.mkdir(parents=True, exist_ok=True)
    catalog_json.write_text(json.dumps(catalog, indent=2), encoding="utf-8")


def download_and_import_track(
    track: dict[str, Any],
    category: Optional[str] = None,
    bpm: Optional[int] = None,
    mood: Optional[str] = None,
    bgm_root: Optional[Path] = None,
) -> Path:
    """Downloads track from CreatorMix CDN, formats filename, and indexes in music_catalog.json."""
    root = bgm_root or get_bgm_root()
    genre = str(track.get("genre", "general")).lower()
    default_cat, default_bpm, default_mood = GENRE_CATEGORY_MAP.get(genre, ("01_Rolling_Cadence", 115, "UpbeatBeat"))

    target_category = category or default_cat
    target_bpm = bpm or default_bpm
    target_mood = mood or default_mood
    clean_title = camel_clean(str(track.get("title", "Track")))
    dest_name = f"{target_bpm:03d}bpm_{target_mood}_{clean_title}_Creatormix.mp3"

    dest_dir = root / target_category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / dest_name

    if dest_path.exists():
        print(f"Track already downloaded: {dest_path}")
        return dest_path

    print(f"Downloading [{genre.upper()}] '{track['title']}' ({track.get('duration_formatted', '')}) from CreatorMix...")
    stream_url = str(track.get("stream_url", ""))
    try:
        req = urllib.request.Request(stream_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()
    except Exception:
        album_id = track.get("album_id")
        if album_id:
            for ft in fetch_album_tracks(int(album_id)):
                if ft["title"].strip().lower() == str(track["title"]).strip().lower():
                    stream_url = ft["stream_url"]
                    break
        req = urllib.request.Request(stream_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()

    dest_path.write_bytes(data)

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
    _upsert_music_catalog_entry(root, entry)
    print(f"Downloaded and indexed: {dest_path.name} in {target_category}/")
    return dest_path


def find_latest_download(downloads_dir: Optional[Path] = None, since_minutes: int = 30) -> Path:
    dl_dir = (downloads_dir or Path.home() / "Downloads").expanduser()
    cutoff = dt.datetime.now().timestamp() - (since_minutes * 60)
    candidates = [
        f
        for f in dl_dir.iterdir()
        if f.is_file()
        and f.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac")
        and not f.name.startswith(".")
        and f.stat().st_mtime >= cutoff
    ]
    if not candidates:
        raise FileNotFoundError(
            f"No recent audio files (.mp3/.wav/.m4a) found in {dl_dir} from the last {since_minutes} minutes."
        )
    candidates.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return candidates[0]


def save_music_track_to_catalog(
    source: str,
    bpm: int,
    mood: str,
    title: str,
    artist: str,
    category: str,
    source_site: str = "CreatorMix",
    notes: str = "",
    bgm_root: Optional[Path] = None,
) -> Path:
    """Renames a downloaded audio file to [BPM]_[Mood]_[TrackName]_[Artist].ext and indexes it."""
    root = bgm_root or get_bgm_root()
    src_path = find_latest_download() if source == "latest" else Path(source).expanduser().resolve()
    if not src_path.exists():
        raise FileNotFoundError(f"Source audio file not found: {src_path}")

    ext = src_path.suffix.lower()
    mood_clean = camel_clean(mood)
    title_clean = camel_clean(title)
    artist_clean = camel_clean(artist)

    new_filename = f"{bpm:03d}bpm_{mood_clean}_{title_clean}_{artist_clean}{ext}"
    dest_dir = root / category
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / new_filename

    shutil.move(str(src_path), str(dest_path))

    entry = {
        "filename": new_filename,
        "path": f"03_Audio_Library/01_Curated_BGM/{category}/{new_filename}",
        "relpath": f"{category}/{new_filename}",
        "category": category,
        "bpm": bpm,
        "beat_interval_s": round(60.0 / max(bpm, 1), 3),
        "mood": mood_clean,
        "title": title,
        "artist": artist,
        "source_site": source_site,
        "notes": notes,
        "saved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    _upsert_music_catalog_entry(root, entry)
    print(f"Saved & indexed track -> {dest_path}")
    return dest_path


def recommend_music_tracks(genre: str, studio_root: Optional[Path] = None, allow_online_probe: bool = True) -> list[dict[str, Any]]:
    """
    Scans 03_Audio_Library/01_Curated_BGM/ and CreatorMix cached/online catalog.
    Enforces the Anti-Monotony Non-Reuse Law by excluding tracks already used in 04_Project_Catalog/.
    """
    root = studio_root or get_studio_root()
    music_root = root / "03_Audio_Library" / "01_Curated_BGM"
    genre_folder_map = {
        "cycling_ride": (["01_Rolling_Cadence", "03_Punchy_Climbs"], ["synthwave", "house", "rock"]),
        "hike_outdoor": (["02_Scenic_Wonder", "04_Warm_Social_And_Retro"], ["lofi", "chillhop", "mixes"]),
        "social_event": (["04_Warm_Social_And_Retro", "01_Rolling_Cadence"], ["chillhop", "lofi"]),
        "archival_slideshow": (["04_Warm_Social_And_Retro", "02_Scenic_Wonder"], ["lofi", "mixes"]),
    }
    preferred_subs, cm_genres = genre_folder_map.get(genre, (["01_Rolling_Cadence"], ["synthwave"]))
    used_tracks = get_previously_used_tracks(root)

    candidates: list[dict[str, Any]] = []
    if music_root.exists():
        for f in sorted(music_root.rglob("*")):
            if f.is_file() and f.suffix.lower() in (".mp3", ".wav", ".m4a", ".aac") and not f.name.startswith("."):
                tax_match = re.match(r"^(\d{2,3})bpm_([^_]+)_([^_]+)_(.+)\.\w+$", f.name, re.IGNORECASE)
                if tax_match:
                    bpm = int(tax_match.group(1))
                    mood_tag = tax_match.group(2)
                    track_title = tax_match.group(3)
                    artist = tax_match.group(4)
                else:
                    bpm_match = re.search(r"(\d{2,3})\s*bpm", f.name.lower())
                    bpm = int(bpm_match.group(1)) if bpm_match else 115
                    mood_tag = f.parent.name
                    track_title = f.stem
                    artist = "CreatorMix_Or_YTAudio"

                clean_title = re.sub(r"[^a-z0-9]", "", track_title.lower())
                if any(u in clean_title or clean_title in u for u in used_tracks if len(u) > 3):
                    continue

                beat_interval_s = round(60.0 / max(bpm, 1), 3)
                parent_name = f.parent.name
                priority = 1 if parent_name == preferred_subs[0] else (2 if parent_name in preferred_subs else 3)
                try:
                    rel_to_studio = str(f.relative_to(root))
                except Exception:
                    rel_to_studio = f"03_Audio_Library/01_Curated_BGM/{parent_name}/{f.name}"

                candidates.append(
                    {
                        "filename": f.name,
                        "path": rel_to_studio,
                        "relpath": f"{parent_name}/{f.name}",
                        "mood_folder": parent_name,
                        "mood_tag": mood_tag,
                        "track_title": track_title,
                        "artist": artist,
                        "estimated_bpm": bpm,
                        "beat_interval_s": beat_interval_s,
                        "recommended_cut_4bars_s": round(beat_interval_s * 8, 2),
                        "genre_match_priority": priority,
                        "source": "local_pool",
                    }
                )

    if allow_online_probe and len(candidates) < 3:
        try:
            for g in cm_genres:
                online_matches = search_catalog(genre=g, max_duration_s=180, exclude_used=True, limit=3, studio_root=root)
                for om in online_matches:
                    candidates.append(
                        {
                            "filename": f"[ONLINE] {om['title']} ({om['duration_formatted']}) - {om['genre'].upper()}",
                            "path": None,
                            "relpath": None,
                            "mood_folder": preferred_subs[0],
                            "mood_tag": str(om["genre"]).capitalize(),
                            "track_title": om["title"],
                            "artist": "CreatorMix",
                            "album": om["album"],
                            "duration_s": om["duration_s"],
                            "stream_url": om["stream_url"],
                            "genre_match_priority": 1,
                            "source": "creatormix_online",
                            "download_command": (
                                f'python3 ./.agents/skills/find-music/scripts/fetch_creatormix_catalog.py '
                                f'--search "{om["title"]}" --download-idx 1'
                            ),
                        }
                    )
                if len(candidates) >= 5:
                    break
        except Exception as exc:
            print(f"CreatorMix online catalog check note: {exc}")

    candidates.sort(key=lambda x: (x.get("genre_match_priority", 3), x.get("track_title", "")))
    return candidates[:5]


def swap_project_music(project_dir: Path, new_track_relpath: str) -> Path:
    """Updates `bgm_track` in `timeline_spec.json` with a relative studio BGM path."""
    spec_path = project_dir / "timeline_spec.json"
    if not spec_path.exists():
        raise FileNotFoundError(f"timeline_spec.json not found in {project_dir}")
    norm_rel = new_track_relpath.strip()
    if not norm_rel.startswith("03_Audio_Library/"):
        norm_rel = f"03_Audio_Library/01_Curated_BGM/{norm_rel.lstrip('/')}"
    data = json.loads(spec_path.read_text(encoding="utf-8"))
    data["bgm_track"] = norm_rel
    if "bgm_tracks" in data and isinstance(data["bgm_tracks"], list) and len(data["bgm_tracks"]) == 1:
        data["bgm_tracks"][0]["track"] = norm_rel
    spec_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return spec_path


def creatormix_cli_main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Direct CreatorMix Catalog Search, Non-Reuse Filter & Downloader")
    p.add_argument("--search", default="", help="Keyword search (e.g. 'ocean', 'chill', 'arcade')")
    p.add_argument("--genre", default="", help="Genre filter: chillhop, lofi, house, synthwave, edm, rock, cyberpunk, trap, mixes")
    p.add_argument("--max-duration", type=int, default=180, help="Max duration in seconds (default: 180s for < 3:00 rule)")
    p.add_argument("--allow-used", action="store_true", help="Allow tracks that were already used in past projects")
    p.add_argument("--limit", type=int, default=10, help="Max results to show")
    p.add_argument("--download-idx", type=int, help="1-based index from search results to immediately download")
    p.add_argument("--refresh-cache", action="store_true", help="Force re-fetch of the CreatorMix catalog")
    args = p.parse_args(argv)

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
        download_and_import_track(results[args.download_idx - 1])


def save_music_cli_main(argv: Optional[list[str]] = None) -> None:
    p = argparse.ArgumentParser(
        description="Auto-rename and save downloaded YouTube Audio Library / CreatorMix track into 03_Audio_Library/01_Curated_BGM/"
    )
    p.add_argument("--source", default="latest", help="Path to downloaded file, or 'latest' to grab newest audio file in ~/Downloads")
    p.add_argument("--bpm", type=int, required=True, help="Track BPM (e.g. 118)")
    p.add_argument("--mood", required=True, help="Short mood descriptor (e.g. ChillBeat, AmbientWonder)")
    p.add_argument("--title", required=True, help="Track title (e.g. 'Circuit Rush')")
    p.add_argument("--artist", required=True, help="Artist or source (e.g. 'The Mini Vandals' or 'CreatorMix')")
    p.add_argument("--category", choices=CATEGORIES, required=True, help="Target mood folder inside 03_Audio_Library/01_Curated_BGM/")
    p.add_argument("--source-site", choices=["YouTube_Audio_Library", "CreatorMix", "Other"], default="CreatorMix")
    p.add_argument("--notes", default="", help="Optional notes on what video scenes this track fits best")
    args = p.parse_args(argv)

    save_music_track_to_catalog(
        source=args.source,
        bpm=args.bpm,
        mood=args.mood,
        title=args.title,
        artist=args.artist,
        category=args.category,
        source_site=args.source_site,
        notes=args.notes,
    )
