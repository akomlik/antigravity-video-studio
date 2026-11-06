#!/usr/bin/env python3
"""
upload_flickr_api.py — Headless & Automated Flickr Video & Photo Publisher for Antigravity Video Studio.

Features:
1. Zero Plaintext Secrets in Code:
   - Reads FLICKR_API_KEY, FLICKR_API_SECRET from environment (injected via 1Password / direnv).
   - Reads FLICKR_OAUTH_TOKEN, FLICKR_OAUTH_TOKEN_SECRET from environment (injected via 1Password)
     or falls back to cached token in `~/.config/antigravity_flickr/token.json`.
2. Seamless Video & Photo Upload:
   - Uploads 4K video editions (_RU.mp4, master .mp4) to Flickr with multipart streaming.
   - Sets date-prefixed Russian or English title, formatted narrative description with timestamps, and tags.
   - Automatically sets Flickr Geotag (lat, lon) from GPX or project_manifest.json.
   - Automatically assigns the video to the specified Flickr Album (e.g., "2026 Fall Mallorca Cycling").
   - Appends published link to 00_Archive_Indexes/flickr_motion_index.jsonl.
   - Prints ready-to-share WhatsApp snippet for family and classmates!
"""

import argparse
import datetime
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
FLICKR_INDEX_PATH = STUDIO_ROOT / "00_Archive_Indexes/flickr_motion_index.jsonl"
TOKEN_DIR = Path("~/.config/antigravity_flickr").expanduser()
TOKEN_FILE = TOKEN_DIR / "token.json"


def get_flickr_credentials() -> tuple[str, str, str | None, str | None]:
    """Retrieves API key, secret, and optional OAuth tokens from environment or cached file."""
    api_key = os.environ.get("FLICKR_API_KEY") or os.environ.get("FLICKR_CONSUMER_KEY")
    api_secret = os.environ.get("FLICKR_API_SECRET") or os.environ.get("FLICKR_CONSUMER_SECRET")

    # If not in env, check cached token file for api_key/secret as fallback
    token = os.environ.get("FLICKR_OAUTH_TOKEN")
    token_secret = os.environ.get("FLICKR_OAUTH_TOKEN_SECRET")

    if TOKEN_FILE.exists():
        try:
            cached = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
            api_key = api_key or cached.get("api_key")
            api_secret = api_secret or cached.get("api_secret")
            token = token or cached.get("oauth_token")
            token_secret = token_secret or cached.get("oauth_token_secret")
        except Exception as e:
            print(f"Note reading {TOKEN_FILE}: {e}")

    return api_key, api_secret, token, token_secret


def authenticate_interactive(api_key: str, api_secret: str) -> dict:
    """Runs interactive OAuth 1.0a authorization flow and returns token dict."""
    from requests_oauthlib import OAuth1Session

    print("\n--- Flickr OAuth 1.0a Authorization ---")
    oauth = OAuth1Session(api_key, client_secret=api_secret, callback_uri="oob")
    request_token_url = "https://www.flickr.com/services/oauth/request_token"

    try:
        fetch_response = oauth.fetch_request_token(request_token_url)
    except Exception as e:
        sys.exit(f"Failed to fetch request token from Flickr: {e}\nCheck FLICKR_API_KEY and FLICKR_API_SECRET.")

    resource_owner_key = fetch_response.get("oauth_token")
    resource_owner_secret = fetch_response.get("oauth_token_secret")

    base_auth_url = "https://www.flickr.com/services/oauth/authorize"
    auth_url = oauth.authorization_url(base_auth_url, perms="write")

    print(f"\n1. Open this URL in your browser:\n   {auth_url}\n")
    print("2. Log in, authorize Antigravity Studio (write permissions), and copy the 9-digit verification code.")
    verifier = input("\nEnter verification code (PIN): ").strip().replace("-", "")

    oauth = OAuth1Session(
        api_key,
        client_secret=api_secret,
        resource_owner_key=resource_owner_key,
        resource_owner_secret=resource_owner_secret,
        verifier=verifier,
    )

    access_token_url = "https://www.flickr.com/services/oauth/access_token"
    try:
        tokens = oauth.fetch_access_token(access_token_url)
    except Exception as e:
        sys.exit(f"Failed to obtain access token: {e}")

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
    TOKEN_FILE.write_text(json.dumps(token_data, indent=2), encoding="utf-8")
    print(f"\n✓ Successfully authorized Flickr account: {token_data['username']} ({token_data['fullname']})")
    print(f"✓ Cached credentials in {TOKEN_FILE}")
    print("\n💡 1Password Integration Tip:")
    print("   To inject via 1Password / direnv and keep filesystem clean, add these to your environment:")
    print(f"   export FLICKR_API_KEY=\"{api_key}\"")
    print(f"   export FLICKR_API_SECRET=\"{api_secret}\"")
    print(f"   export FLICKR_OAUTH_TOKEN=\"{token_data['oauth_token']}\"")
    print(f"   export FLICKR_OAUTH_TOKEN_SECRET=\"{token_data['oauth_token_secret']}\"\n")

    return token_data


def get_oauth_session() -> tuple[object, dict]:
    """Returns an authenticated requests_oauthlib OAuth1Session and token info."""
    from requests_oauthlib import OAuth1Session

    api_key, api_secret, token, token_secret = get_flickr_credentials()

    if not api_key or not api_secret:
        print("\n[!] Missing Flickr API credentials.")
        print("Please set FLICKR_API_KEY and FLICKR_API_SECRET via 1Password / environment.")
        print("Create a free API key at: https://www.flickr.com/services/apps/create/apply/\n")
        api_key = input("Enter Flickr API Key: ").strip()
        api_secret = input("Enter Flickr API Secret: ").strip()

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


def extract_project_metadata(project_dir: Path, edition: str = "ru") -> dict:
    """Extracts title, description, tags, and coordinates from project artifacts."""
    project_dir = Path(project_dir).expanduser().resolve()
    project_name = project_dir.name

    # 1. Check youtube_metadata.json
    meta_json = project_dir / "youtube_metadata.json"
    meta = {}
    if meta_json.exists():
        try:
            meta = json.loads(meta_json.read_text(encoding="utf-8"))
        except Exception:
            pass

    # 2. Determine target video file
    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", project_name)
    year = date_match.group(1).split("-")[0] if date_match else "2026"
    date_str = date_match.group(1) if date_match else ""

    exports_dir = Path("~/Movies/Exports").expanduser() / year
    ru_mp4 = exports_dir / f"{project_name}_RU.mp4"
    en_mp4 = exports_dir / f"{project_name}.mp4"

    if edition.lower() == "ru" and ru_mp4.exists():
        target_video = ru_mp4
    elif en_mp4.exists():
        target_video = en_mp4
    elif ru_mp4.exists():
        target_video = ru_mp4
    else:
        # Fallback to project dir
        vids = list(project_dir.glob("*.mp4"))
        target_video = vids[0] if vids else None

    # 3. Title & Description per edition
    locs = meta.get("localizations", {})
    if edition.lower() == "ru" and "ru" in locs:
        raw_title = locs["ru"].get("title", meta.get("title", project_name.replace("_", " ")))
        raw_desc = locs["ru"].get("description", meta.get("description", ""))
    else:
        raw_title = meta.get("title", project_name.replace("_", " "))
        raw_desc = meta.get("description", "")

    # Date prefix formatting: YYYY-MM-DD · Title
    if date_str and not raw_title.startswith(date_str):
        flickr_title = f"{date_str} · {raw_title}"
    else:
        flickr_title = raw_title

    # Clean description: keep narrative paragraphs + chapters, strip raw tags and URLs
    clean_paragraphs = []
    for para in raw_desc.split("\n\n"):
        p = para.strip()
        if p and not p.startswith(("#", "http://", "https://", "🎵", "🔊", "━━━━━━━━")):
            clean_paragraphs.append(p)
    flickr_desc = "\n\n".join(clean_paragraphs[:4])

    # 4. Tags
    tags = ["Mallorca", "cycling", "roadbike", "BleeqUP", "video"]
    for t in meta.get("tags", []):
        t_clean = t.replace(",", " ").strip()
        if t_clean and t_clean not in tags and len(tags) < 14:
            tags.append(f'"{t_clean}"' if " " in t_clean else t_clean)

    # 5. Geolocation from GPX or project_manifest.json
    lat, lon = None, None
    manifest_p = project_dir / "project_manifest.json"
    if manifest_p.exists():
        try:
            m_data = json.loads(manifest_p.read_text(encoding="utf-8"))
            gpx_pts = m_data.get("gpx_points") or []
            if gpx_pts:
                mid_pt = gpx_pts[len(gpx_pts) // 2]
                lat, lon = mid_pt.get("lat"), mid_pt.get("lon")
        except Exception:
            pass

    return {
        "project_name": project_name,
        "video_file": target_video,
        "title": flickr_title,
        "description": flickr_desc,
        "tags": " ".join(tags),
        "lat": lat,
        "lon": lon,
        "album": "2026 Fall Mallorca Cycling",
    }


def upload_video_to_flickr(
    session,
    video_path: Path,
    title: str,
    description: str,
    tags: str,
    is_public: bool = True,
    is_family: bool = False,
) -> str:
    """Uploads a video to Flickr and returns the photo_id."""
    upload_url = "https://up.flickr.com/services/upload/"
    print(f"\nUploading {video_path.name} to Flickr ({round(video_path.stat().st_size / 1024 / 1024, 1)} MB)...")

    data = {
        "title": title,
        "description": description,
        "tags": tags,
        "is_public": "1" if is_public else "0",
        "is_friend": "0",
        "is_family": "1" if is_family else "0",
        "safety_level": "1",  # 1 = Safe
        "content_type": "3",  # 3 = Video / Other
    }

    with open(video_path, "rb") as f:
        files = {"photo": (video_path.name, f, "video/mp4")}
        res = session.post(upload_url, data=data, files=files)

    if res.status_code != 200:
        sys.exit(f"Upload failed (HTTP {res.status_code}): {res.text[:300]}")

    # Parse XML response
    root = ET.fromstring(res.text)
    if root.attrib.get("stat") != "ok":
        err = root.find("err")
        err_msg = err.attrib.get("msg") if err is not None else res.text
        sys.exit(f"Flickr API Error: {err_msg}")

    photoid_el = root.find("photoid")
    if photoid_el is None or not photoid_el.text:
        sys.exit(f"Failed to parse photo ID from response: {res.text}")

    photo_id = photoid_el.text.strip()
    print(f"✓ Video successfully uploaded to Flickr! Photo ID: {photo_id}")
    return photo_id


def set_photo_geolocation(session, photo_id: str, lat: float, lon: float):
    """Sets photo GPS coordinates on Flickr."""
    rest_url = "https://api.flickr.com/services/rest/"
    params = {
        "method": "flickr.photos.geo.setLocation",
        "photo_id": photo_id,
        "lat": f"{lat:.6f}",
        "lon": f"{lon:.6f}",
        "format": "json",
        "nojsoncallback": "1",
    }
    try:
        r = session.post(rest_url, data=params).json()
        if r.get("stat") == "ok":
            print(f"✓ Applied GPS Geotag: {lat:.4f}, {lon:.4f}")
        else:
            print(f"Note setting geotag: {r.get('message')}")
    except Exception as e:
        print(f"Note setting geotag: {e}")


def assign_photo_to_album(session, photo_id: str, album_name: str):
    """Adds the uploaded photo/video to an existing Flickr album or creates it."""
    rest_url = "https://api.flickr.com/services/rest/"
    try:
        # Check existing photosets
        r = session.get(rest_url, params={"method": "flickr.photosets.getList", "format": "json", "nojsoncallback": "1"}).json()
        photosets = r.get("photosets", {}).get("photoset", [])
        target_set_id = None
        for ps in photosets:
            title_text = ps.get("title", {}).get("_content", "")
            if title_text.strip().lower() == album_name.strip().lower():
                target_set_id = ps["id"]
                break

        if target_set_id:
            add_res = session.post(
                rest_url,
                data={
                    "method": "flickr.photosets.addPhoto",
                    "photoset_id": target_set_id,
                    "photo_id": photo_id,
                    "format": "json",
                    "nojsoncallback": "1",
                },
            ).json()
            if add_res.get("stat") == "ok":
                print(f"✓ Added to existing Flickr Album: \"{album_name}\"")
            else:
                print(f"Note adding to album: {add_res.get('message')}")
        else:
            # Create new photoset
            create_res = session.post(
                rest_url,
                data={
                    "method": "flickr.photosets.create",
                    "title": album_name,
                    "primary_photo_id": photo_id,
                    "format": "json",
                    "nojsoncallback": "1",
                },
            ).json()
            if create_res.get("stat") == "ok":
                print(f"✓ Created new Flickr Album: \"{album_name}\"")
            else:
                print(f"Note creating album: {create_res.get('message')}")
    except Exception as e:
        print(f"Note managing Flickr album: {e}")


def register_in_flickr_index(entry: dict, flickr_url: str):
    """Appends uploaded video record to 00_Archive_Indexes/flickr_motion_index.jsonl."""
    FLICKR_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "timestamp_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "project_name": entry.get("project_name", ""),
        "title": entry.get("title", ""),
        "flickr_url": flickr_url,
        "album": entry.get("album", ""),
        "video_file": str(entry.get("video_file", "")),
    }
    with open(FLICKR_INDEX_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"✓ Registered in {FLICKR_INDEX_PATH.name}")


def main():
    p = argparse.ArgumentParser(description="Upload video editions to Flickr via Flickr API (1Password/direnv supported)")
    p.add_argument("--project-dir", required=True, help="Path to project folder in 04_Project_Catalog/ or ~/Movies/")
    p.add_argument("--edition", choices=["ru", "en", "ua"], default="ru", help="Which audio edition to publish (default: ru)")
    p.add_argument("--video-file", help="Explicit path to video file override")
    p.add_argument("--title", help="Explicit title override")
    p.add_argument("--album", default="2026 Fall Mallorca Cycling", help="Target Flickr album name")
    p.add_argument("--privacy", choices=["public", "family", "private"], default="public", help="Flickr privacy setting")
    p.add_argument("--auth", action="store_true", help="Run interactive authorization flow only")
    args = p.parse_args()

    session, token_info = get_oauth_session()

    if args.auth:
        print("Flickr authorization verified and active.")
        return

    meta = extract_project_metadata(Path(args.project_dir), edition=args.edition)

    video_file = Path(args.video_file).expanduser().resolve() if args.video_file else meta["video_file"]
    if not video_file or not video_file.exists():
        sys.exit(f"Error: Video file not found: {video_file}\nPlease build the video first with /build-timeline.")

    title = args.title or meta["title"]
    description = meta["description"]
    tags = meta["tags"]
    album = args.album or meta.get("album", "2026 Fall Mallorca Cycling")
    is_public = args.privacy == "public"
    is_family = args.privacy in ("family", "public")

    photo_id = upload_video_to_flickr(
        session,
        video_path=video_file,
        title=title,
        description=description,
        tags=tags,
        is_public=is_public,
        is_family=is_family,
    )

    if meta.get("lat") and meta.get("lon"):
        set_photo_geolocation(session, photo_id, meta["lat"], meta["lon"])

    if album:
        assign_photo_to_album(session, photo_id, album)

    username = token_info.get("username", "apkom")
    flickr_url = f"https://www.flickr.com/photos/{username}/{photo_id}/"

    register_in_flickr_index(meta, flickr_url)

    print("\n========================================================")
    print("📸 FLICKR PUBLISHING COMPLETE!")
    print("========================================================")
    print(f"  🎬 Live Video URL: {flickr_url}")
    print(f"  📁 Album:          {album}")
    print(f"  🏷️  Title:          {title}")
    print("\n💬 Ready-to-Paste WhatsApp Message:")
    print("────────────────────────────────────────────────────────")
    print(f"{title}\n\nСмотрите новое видео у меня на Flickr:\n👉 {flickr_url}")
    print("========================================================\n")


if __name__ == "__main__":
    main()
