"""Headless Flickr video publisher (`_RU.mp4` / master), GPX geotagger, and YouTube cross-link comment automation."""

from __future__ import annotations

import argparse
import datetime
import getpass
import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from agvs_core.config import find_binary, get_exports_dir, get_hot_media_dir, get_studio_root, resolve_media_path

TOKEN_DIR = Path("~/.config/antigravity_flickr").expanduser()
TOKEN_FILE = TOKEN_DIR / "token.json"


def get_flickr_index_path() -> Path:
    return get_studio_root() / "00_Archive_Indexes" / "flickr_motion_index.jsonl"


def get_flickr_credentials() -> tuple[str | None, str | None, str | None, str | None]:
    api_key = os.environ.get("FLICKR_API_KEY") or os.environ.get("FLICKR_CONSUMER_KEY")
    api_secret = os.environ.get("FLICKR_API_SECRET") or os.environ.get("FLICKR_CONSUMER_SECRET")
    token = os.environ.get("FLICKR_OAUTH_TOKEN")
    token_secret = os.environ.get("FLICKR_OAUTH_TOKEN_SECRET")

    if TOKEN_FILE.exists():
        try:
            cached = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            api_key = api_key or cached.get("api_key")
            api_secret = api_secret or cached.get("api_secret")
            token = token or cached.get("oauth_token")
            token_secret = token_secret or cached.get("oauth_token_secret")
        except Exception:
            pass

    return api_key, api_secret, token, token_secret


def authenticate_interactive(api_key: str, api_secret: str) -> dict[str, Any]:
    from requests_oauthlib import OAuth1Session

    oauth = OAuth1Session(api_key, client_secret=api_secret, callback_uri="oob")
    fetch_response = oauth.fetch_request_token("https://www.flickr.com/services/oauth/request_token")
    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")
    auth_url = oauth.authorization_url("https://www.flickr.com/services/oauth/authorize", perms="write")

    print(f"\n1. Open this URL in your browser:\n   {auth_url}\n")
    verifier = getpass.getpass("Enter verification code (PIN): ").strip().replace("-", "")

    oauth = OAuth1Session(
        api_key,
        client_secret=api_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )
    tokens = oauth.fetch_access_token("https://www.flickr.com/services/oauth/access_token")
    token_data = {
        "api_key": api_key,
        "api_secret": api_secret,
        "oauth_token": tokens.get("oauth_token"),
        "oauth_token_secret": tokens.get("oauth_token_secret"),
        "user_nsid": tokens.get("user_nsid"),
        "username": tokens.get("username", "apkom"),
        "fullname": tokens.get("fullname", ""),
    }

    TOKEN_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(TOKEN_DIR, 0o700)
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    os.chmod(TOKEN_FILE, 0o600)
    return token_data


def get_oauth_session() -> tuple[Any, dict[str, Any]]:
    from requests_oauthlib import OAuth1Session

    api_key, api_secret, token, token_secret = get_flickr_credentials()
    if not api_key or not api_secret:
        api_key = api_key or getpass.getpass("Enter Flickr API Key: ").strip()
        api_secret = api_secret or getpass.getpass("Enter Flickr API Secret: ").strip()

    if not token or not token_secret:
        token_info = authenticate_interactive(api_key, api_secret)
        token = token_info["oauth_token"]
        token_secret = token_info["oauth_token_secret"]
    else:
        token_info = {
            "api_key": api_key,
            "api_secret": api_secret,
            "oauth_token": token,
            "oauth_token_secret": token_secret,
            "username": os.environ.get("FLICKR_USERNAME", "apkom"),
        }

    session = OAuth1Session(
        api_key,
        client_secret=api_secret,
        resource_owner_key=token,
        resource_owner_secret=token_secret,
    )
    return session, token_info


def extract_gpx_coordinates(project_dir: Path) -> tuple[float | None, float | None]:
    candidate_dirs = [project_dir]
    manifest_p = project_dir / "project_manifest.json"
    gpx_candidates: list[str] = []
    if manifest_p.exists():
        try:
            m_data = json.loads(manifest_p.read_text(encoding="utf-8"))
            if m_data.get("gpx_file"):
                gpx_candidates.append(m_data["gpx_file"])
            if m_data.get("raw_media_folder"):
                raw_p = resolve_media_path(m_data["raw_media_folder"])
                if raw_p.exists() and raw_p not in candidate_dirs:
                    candidate_dirs.append(raw_p)
        except Exception:
            pass

    date_m = re.search(r"(\d{4})-\d{2}-\d{2}", project_dir.name)
    year = date_m.group(1) if date_m else "2026"
    fallback_raw = get_hot_media_dir() / year / project_dir.name
    if fallback_raw.exists() and fallback_raw not in candidate_dirs:
        candidate_dirs.append(fallback_raw)

    sb_p = project_dir / "Storyboard.md"
    if sb_p.exists():
        sb_txt = sb_p.read_text(encoding="utf-8")
        m = re.search(r"\*\*GPX Track:\*\*\s*`?([^`\n\(\)]+\.gpx)`?", sb_txt)
        if m:
            gpx_candidates.append(m.group(1).strip())

    found_gpx: Path | None = None
    for c_name in gpx_candidates:
        for c_dir in candidate_dirs:
            p = c_dir / c_name
            if p.exists():
                found_gpx = p
                break
        if found_gpx:
            break

    if not found_gpx:
        for c_dir in candidate_dirs:
            gpxs = list(c_dir.glob("*.gpx"))
            if gpxs:
                found_gpx = gpxs[0]
                break

    if not found_gpx:
        return None, None

    try:
        root = ET.parse(found_gpx).getroot()
        pts: list[tuple[float, float, float]] = []
        for trkpt in root.iter():
            if trkpt.tag.endswith("trkpt"):
                lat = float(trkpt.attrib["lat"])
                lon = float(trkpt.attrib["lon"])
                ele = 0.0
                for c in trkpt.iter():
                    if c.tag.endswith("ele") and c.text:
                        ele = float(c.text)
                pts.append((lat, lon, ele))
        if not pts:
            return None, None
        min_ele = min(p[2] for p in pts)
        max_ele = max(p[2] for p in pts)
        best_pt = max(pts, key=lambda x: x[2]) if (max_ele - min_ele > 50.0) else pts[len(pts) // 2]
        return best_pt[0], best_pt[1]
    except Exception:
        return None, None


def extract_project_metadata(project_dir: Path, edition: str | Path = "ru") -> dict[str, Any]:
    """
    Extract Flickr title, description, tags, GPS coordinates, and `cat_dir` (fixing Commit 9 bug
    where missing `cat_dir` caused `cross_link_flickr_on_youtube()` to silently skip).
    Accepts either an edition code (`"ru"`, `"en"`, `"ua"`) or an explicit video `Path`.
    """
    project_dir = Path(project_dir).expanduser().resolve()
    project_name = project_dir.name

    explicit_video: Path | None = None
    if isinstance(edition, Path) or str(edition).lower().endswith(".mp4"):
        explicit_video = Path(edition)
        stem_low = explicit_video.stem.lower()
        if stem_low.endswith("_ru"):
            edition_code = "ru"
        elif stem_low.endswith("_ua"):
            edition_code = "ua"
        else:
            edition_code = "en"
    else:
        edition_code = str(edition).strip().lower() or "ru"

    meta_json = project_dir / "youtube_metadata.json"
    meta: dict[str, Any] = {}
    if meta_json.exists():
        try:
            meta = json.loads(meta_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", project_name)
    year = date_match.group(1).split("-")[0] if date_match else "2026"
    date_str = date_match.group(1) if date_match else ""

    exports_dir = get_exports_dir() / year
    ru_mp4 = exports_dir / f"{project_name}_RU.mp4"
    en_mp4 = exports_dir / f"{project_name}.mp4"

    if explicit_video is not None:
        target_video: Path | None = explicit_video
    elif edition_code == "ru" and ru_mp4.exists():
        target_video = ru_mp4
    elif en_mp4.exists():
        target_video = en_mp4
    elif ru_mp4.exists():
        target_video = ru_mp4
    else:
        vids = list(project_dir.glob("*.mp4"))
        target_video = vids[0] if vids else None

    locs = meta.get("localizations", {})
    if edition_code in ("ru", "ua") and edition_code in locs:
        raw_title = locs[edition_code].get("title", meta.get("title", project_name.replace("_", " ")))
        raw_desc = locs[edition_code].get("description", meta.get("description", ""))
    else:
        raw_title = meta.get("title", project_name.replace("_", " "))
        raw_desc = meta.get("description", "")

    flickr_title = f"{date_str} · {raw_title}" if (date_str and not raw_title.startswith(date_str)) else raw_title
    clean_paragraphs = [
        para.strip()
        for para in raw_desc.split("\n\n")
        if para.strip() and not para.strip().startswith(("#", "http://", "https://", "🎵", "🔊", "━━━━━━━━"))
    ]
    flickr_desc = "\n\n".join(clean_paragraphs[:4])

    tags = ["Mallorca", "cycling", "roadbike", "BleeqUP", "video"]
    for t in meta.get("tags", []):
        t_clean = t.replace(",", " ").strip()
        if t_clean and t_clean not in tags and len(tags) < 14:
            tags.append(f'"{t_clean}"' if " " in t_clean else t_clean)

    lat, lon = extract_gpx_coordinates(project_dir)

    return {
        "project_name": project_name,
        "cat_dir": str(project_dir),
        "video_file": target_video,
        "title": flickr_title,
        "description": flickr_desc,
        "tags": " ".join(tags),
        "lat": lat,
        "lon": lon,
        "album": "2026 Fall Mallorca Cycling",
    }


def upload_video_to_flickr(
    session: Any,
    video_path: Path,
    title: str,
    description: str,
    tags: str,
    is_public: bool = True,
    is_family: bool = False,
) -> str:
    if video_path.stat().st_size >= 980_000_000:
        ffmpeg_bin = find_binary("ffmpeg") or "ffmpeg"
        transcoded_path = video_path.with_name(f"{video_path.stem}_1080p.mp4")
        subprocess.run(
            [
                ffmpeg_bin, "-y", "-i", str(video_path),
                "-vf", "scale=1920:1080",
                "-c:v", "h264_videotoolbox", "-b:v", "14M",
                "-c:a", "copy",
                str(transcoded_path),
            ],
            check=True,
        )
        video_path = transcoded_path

    upload_url = "https://up.flickr.com/services/upload/"
    data = {
        "title": title,
        "description": description,
        "tags": tags,
        "is_public": "1" if is_public else "0",
        "is_friend": "0",
        "is_family": "1" if is_family else "0",
        "safety_level": "1",
        "content_type": "3",
    }

    import requests
    from oauthlib.oauth1 import Client as OAuth1Client

    api_key, api_secret, token, token_secret = get_flickr_credentials()
    oauth_client = OAuth1Client(
        api_key,
        client_secret=api_secret,
        resource_owner_key=token,
        resource_owner_secret=token_secret,
    )
    _, signed_headers, _ = oauth_client.sign(
        upload_url,
        http_method="POST",
        body=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    with video_path.open("rb") as f:
        files = {"photo": (video_path.name, f, "video/mp4")}
        res = requests.post(
            upload_url,
            data=data,
            files=files,
            headers={"Authorization": signed_headers["Authorization"]},
        )

    if res.status_code != 200:
        raise RuntimeError(f"Flickr upload failed (HTTP {res.status_code}): {res.text[:300]}")

    root = ET.fromstring(res.text)
    if root.attrib.get("stat") != "ok":
        err = root.find("err")
        err_msg = err.attrib.get("msg") if err is not None else res.text
        raise RuntimeError(f"Flickr API Error: {err_msg}")

    photoid_el = root.find("photoid")
    if photoid_el is None or not photoid_el.text:
        raise RuntimeError(f"Failed to parse Flickr photo ID: {res.text}")
    return photoid_el.text.strip()


def set_photo_geolocation(session: Any, photo_id: str, lat: float, lon: float) -> None:
    rest_url = "https://api.flickr.com/services/rest/"
    try:
        session.post(
            rest_url,
            data={
                "method": "flickr.photos.geo.setLocation",
                "photo_id": photo_id,
                "lat": f"{lat:.6f}",
                "lon": f"{lon:.6f}",
                "format": "json",
                "nojsoncallback": "1",
            },
        )
    except Exception:
        pass


def assign_photo_to_album(session: Any, photo_id: str, album_name: str) -> None:
    rest_url = "https://api.flickr.com/services/rest/"
    try:
        r = session.get(rest_url, params={"method": "flickr.photosets.getList", "format": "json", "nojsoncallback": "1"}).json()
        photosets = r.get("photosets", {}).get("photoset", [])
        target_set_id = None
        for ps in photosets:
            if ps.get("title", {}).get("_content", "").strip().lower() == album_name.strip().lower():
                target_set_id = ps["id"]
                break

        if target_set_id:
            session.post(
                rest_url,
                data={
                    "method": "flickr.photosets.addPhoto",
                    "photoset_id": target_set_id,
                    "photo_id": photo_id,
                    "format": "json",
                    "nojsoncallback": "1",
                },
            )
        else:
            session.post(
                rest_url,
                data={
                    "method": "flickr.photosets.create",
                    "title": album_name,
                    "primary_photo_id": photo_id,
                    "format": "json",
                    "nojsoncallback": "1",
                },
            )
    except Exception:
        pass


def register_in_flickr_index(entry: dict[str, Any], flickr_url: str) -> None:
    idx_path = get_flickr_index_path()
    idx_path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project_name": entry.get("project_name", ""),
        "title": entry.get("title", ""),
        "flickr_url": flickr_url,
        "album": entry.get("album", ""),
        "video_file": Path(entry.get("video_file", "")).name if entry.get("video_file") else "",
    }
    with idx_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def cross_link_flickr_on_youtube(entry: dict[str, Any], flickr_url: str) -> None:
    cat_dir = entry.get("cat_dir")
    if not cat_dir:
        return
    yt_meta_path = Path(cat_dir) / "youtube_metadata.json"
    if not yt_meta_path.exists():
        return
    try:
        yt_meta = json.loads(yt_meta_path.read_text(encoding="utf-8"))
        vid_id = yt_meta.get("published_video_id")
        if not vid_id:
            return
        yt_meta["published_flickr_url"] = flickr_url
        yt_meta_path.write_text(json.dumps(yt_meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        from agvs_core.youtube_pub import get_youtube_service

        yt = get_youtube_service()
        existing = yt.commentThreads().list(part="snippet", videoId=vid_id).execute().get("items", [])
        for item in existing:
            txt = item["snippet"]["topLevelComment"]["snippet"].get("textOriginal", "")
            if flickr_url in txt or "flickr.com" in txt:
                return
        comment_text = (
            f"🔊 Русская версия (с русской озвучкой и без блокировок) на Flickr:\n"
            f"👉 {flickr_url}\n\n"
            f"💬 Subtitles [CC] available on this video in English, Українська & Русский."
        )
        yt.commentThreads().insert(
            part="snippet",
            body={
                "snippet": {
                    "videoId": vid_id,
                    "topLevelComment": {"snippet": {"textOriginal": comment_text}},
                }
            },
        ).execute()
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Upload video editions to Flickr via Flickr API")
    p.add_argument("--project-dir", required=True)
    p.add_argument("--edition", choices=["ru", "en", "ua"], default="ru")
    p.add_argument("--video-file")
    p.add_argument("--title")
    p.add_argument("--album", default="2026 Fall Mallorca Cycling")
    p.add_argument("--geo")
    p.add_argument("--privacy", choices=["public", "family", "private"], default="public")
    p.add_argument("--auth", action="store_true")
    args = p.parse_args(argv)

    session, token_info = get_oauth_session()
    if args.auth:
        return 0

    meta = extract_project_metadata(Path(args.project_dir), edition=args.edition)
    video_file = Path(args.video_file).expanduser().resolve() if args.video_file else meta["video_file"]
    if not video_file or not video_file.exists():
        sys.exit(f"Error: Video file not found: {video_file}")

    title = args.title or meta["title"]
    description = meta["description"]
    tags = meta["tags"]
    album = args.album or meta.get("album", "2026 Fall Mallorca Cycling")
    is_public = args.privacy == "public"
    is_family = args.privacy in ("family", "public")

    lat, lon = meta.get("lat"), meta.get("lon")
    if args.geo:
        try:
            parts = [float(x.strip()) for x in args.geo.split(",")]
            lat, lon = parts[0], parts[1]
        except Exception:
            pass

    photo_id = upload_video_to_flickr(
        session,
        video_path=video_file,
        title=title,
        description=description,
        tags=tags,
        is_public=is_public,
        is_family=is_family,
    )
    if lat and lon:
        set_photo_geolocation(session, photo_id, lat, lon)
    if album:
        assign_photo_to_album(session, photo_id, album)

    username = token_info.get("username", "apkom")
    flickr_url = f"https://www.flickr.com/photos/{username}/{photo_id}/"
    register_in_flickr_index(meta, flickr_url)
    cross_link_flickr_on_youtube(meta, flickr_url)
    print(f"Live Flickr URL: {flickr_url}")
    return 0
