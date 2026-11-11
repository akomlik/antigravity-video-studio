#!/usr/bin/env python3
"""
upload_youtube_api.py
Headless YouTube Data API v3 uploader and localization manager:
- Reads GOOGLE_OAUTH_CLIENT_ID, GOOGLE_OAUTH_CLIENT_SECRET, GOOGLE_CLOUD_PROJECT,
  and optionally GOOGLE_OAUTH_REFRESH_TOKEN (via 1Password/direnv for zero-file auth),
  falling back to caching the OAuth refresh token in `~/.config/antigravity_youtube/token.json`.
- Uploads 4K MP4 masters with resumable progress (Private by default)
- Sets English default title/description + Ukrainian (ua -> uk) and Russian (ru) localizations
- Uploads localized 1080p composite thumbnails (thumbnail.jpg, thumbnail_ua.jpg, thumbnail_ru.jpg)
- Assigns playlists by name (e.g., 'Mallorca', '2026 Mallorca Cycling')
- Uploads multi-language .srt subtitle tracks (en, ua -> uk, ru) via captions.insert
- Can also update an existing video (--update-video-id <ID>) with localizations & captions
- Registers the published URL in 00_Archive_Indexes/youtube_motion_index.jsonl
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

STUDIO_ROOT = Path(os.environ.get("ANTIGRAVITY_STUDIO_ROOT", Path(__file__).resolve().parents[4]))
YT_INDEX_PATH = STUDIO_ROOT / "00_Archive_Indexes/youtube_motion_index.jsonl"
OAUTH_DIR = Path("~/.config/antigravity_youtube").expanduser()
TOKEN_FILE = OAUTH_DIR / "token.json"

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]


def load_dotenv_if_needed():
    """Loads STUDIO_ROOT/.env if OAuth client env vars are not already in os.environ."""
    env_file = STUDIO_ROOT / ".env"
    if not os.environ.get("GOOGLE_OAUTH_CLIENT_ID") and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip("\"'"))


def get_youtube_service():
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    load_dotenv_if_needed()
    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    refresh_token = os.environ.get("GOOGLE_OAUTH_REFRESH_TOKEN") or os.environ.get("YOUTUBE_OAUTH_REFRESH_TOKEN")

    creds = None

    # Priority 1: Zero-file 1Password / direnv refresh token
    if refresh_token and client_id and client_secret:
        try:
            creds = Credentials(
                None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=SCOPES,
            )
            creds.refresh(Request())
        except Exception as e:
            print(f"Warning: Failed to refresh credentials from environment refresh token: {e}")
            creds = None

    # Priority 2: Cached token.json on disk (fallback)
    if not creds and TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        except Exception as e:
            print(f"Warning: Failed to load credentials from {TOKEN_FILE}: {e}")
            creds = None

    # Priority 3: Interactive OAuth local server flow if not yet authorized
    if not creds or not creds.valid:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "antigravity-video-studio")
        if not client_id or not client_secret:
            raise RuntimeError(
                "GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET not found in environment. "
                "Set them in your shell environment (e.g. via direnv) or in a local .env file."
            )
        client_config = {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "project_id": project_id,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": ["http://localhost"],
            }
        }
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        creds = flow.run_local_server(port=0)

        # Cache locally on disk whenever interactive OAuth had to run (including when env refresh_token expired)
        OAUTH_DIR.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        os.chmod(TOKEN_FILE, 0o600)

    return build("youtube", "v3", credentials=creds)


def register_in_archive_index(meta: dict, youtube_url: str):
    """Appends the newly published video into 00_Archive_Indexes/youtube_motion_index.jsonl."""
    m = re.search(r"(?:v=|youtu\.be/|video/)([A-Za-z0-9_-]{11})", youtube_url)
    vid_id = m.group(1) if m else youtube_url
    clean_url = f"https://www.youtube.com/watch?v={vid_id}"

    entry = {
        "id": vid_id,
        "url": clean_url,
        "title": meta.get("title", ""),
        "upload_date": datetime.date.today().strftime("%Y%m%d"),
        "description_snippet": meta.get("description", "")[:500],
        "chapters": meta.get("chapters", []),
        "project_name": meta.get("project_name", ""),
    }

    YT_INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(YT_INDEX_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    print(f"Registered {clean_url} in {YT_INDEX_PATH}")


def assign_playlists_and_captions(youtube, vid_id: str, meta: dict, meta_path: Path | None = None):
    from googleapiclient.http import MediaFileUpload

    # 1. Assign Playlists by title (avoiding duplicate insertions)
    target_playlists = set(meta.get("playlists", []))
    if target_playlists:
        try:
            pl_resp = youtube.playlists().list(part="snippet", mine=True, maxResults=50).execute()
            for item in pl_resp.get("items", []):
                pl_title = item.get("snippet", {}).get("title", "")
                if pl_title in target_playlists:
                    youtube.playlistItems().insert(
                        part="snippet",
                        body={
                            "snippet": {
                                "playlistId": item["id"],
                                "resourceId": {"kind": "youtube#video", "videoId": vid_id},
                            }
                        },
                    ).execute()
                    print(f"  Added to playlist: {pl_title}")
        except Exception as e:
            print(f"  Note: Playlist assignment warning: {e}")

    # 2. Upload .srt subtitle tracks (en, ua, ru) with hash-check caching
    # Note: Locally we always use ISO code `ua` for Ukraine; YouTube API's wire language code is `uk`.
    YT_WIRE_LANG = {"en": "en", "ua": "uk", "ru": "ru"}
    lang_names = {"en": "English", "ua": "Українська (UA)", "ru": "Русский"}
    existing_langs = {}
    try:
        cap_list = youtube.captions().list(part="snippet", videoId=vid_id).execute()
        for c in cap_list.get("items", []):
            if c["snippet"].get("trackKind") != "ASR":
                existing_langs.setdefault(c["snippet"]["language"], []).append(c["id"])
    except Exception as e:
        print(f"  Note: captions.list warning: {e}")

    caption_hashes = meta.setdefault("caption_hashes", {})
    if meta_path and Path(meta_path).exists():
        try:
            disk_meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            if "caption_hashes" in disk_meta:
                caption_hashes.update(disk_meta["caption_hashes"])
        except Exception:
            pass

    hashes_changed = False
    for lang, srt_path in meta.get("srt_files", {}).items():
        yt_lang = YT_WIRE_LANG.get(lang, lang)
        srt_file = Path(srt_path)
        if not srt_file.is_absolute() and meta_path:
            srt_file = meta_path.parent / srt_path
        if srt_file.exists():
            current_hash = hashlib.sha256(srt_file.read_bytes()).hexdigest()
            cache_key = f"{vid_id}:{yt_lang}"

            # If caption already exists on YouTube and hash matches cached hash, skip to save 400 quota units!
            if yt_lang in existing_langs and caption_hashes.get(cache_key) == current_hash:
                print(f"  Caption track for {lang} ({yt_lang}) unchanged (SHA256: {current_hash[:8]}), skipping captions.insert to save 400 quota units.")
                continue

            try:
                media = MediaFileUpload(str(srt_file), mimetype="application/x-subrip")
                for old_id in existing_langs.get(yt_lang, []):
                    try:
                        youtube.captions().delete(id=old_id).execute()
                    except Exception as del_err:
                        print(f"  Note: captions.delete ({lang}) warning: {del_err}")
                youtube.captions().insert(
                    part="snippet",
                    body={
                        "snippet": {
                            "videoId": vid_id,
                            "language": yt_lang,
                            "name": lang_names.get(lang, lang),
                            "isDraft": False,
                        }
                    },
                    media_body=media,
                ).execute()
                print(f"  Uploaded {lang} subtitle track: {srt_file.name} (SHA256: {current_hash[:8]})")
                caption_hashes[cache_key] = current_hash
                hashes_changed = True
            except Exception as e:
                print(f"  Note: Caption upload ({lang}) warning: {e}")

    if hashes_changed and meta_path and Path(meta_path).exists():
        try:
            stored_meta = json.loads(Path(meta_path).read_text(encoding="utf-8"))
            stored_meta.setdefault("caption_hashes", {}).update(caption_hashes)
            Path(meta_path).write_text(json.dumps(stored_meta, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as save_err:
            print(f"  Note: Could not persist caption_hashes: {save_err}")


def infer_recording_date_iso(meta: dict, video_path: Path | None = None) -> str | None:
    """
    Infers the YouTube Data API v3 `recordingDetails.recordingDate` (ISO 8601 UTC: YYYY-MM-DDT00:00:00.000Z)
    from `meta['recording_date']`, `meta['project_name']`, `meta['title']`, or `video_path.name`.
    """
    raw = meta.get("recording_date") or ""
    if raw:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(raw))
        if m:
            return f"{m.group(1)}T00:00:00.000Z"
    for candidate in (meta.get("project_name", ""), meta.get("title", ""), video_path.name if video_path else ""):
        m = re.search(r"(\d{4}-\d{2}-\d{2})", str(candidate))
        if m:
            return f"{m.group(1)}T00:00:00.000Z"
    return None


def sanitize_yt_description(desc: str, max_bytes: int = 4850) -> str:
    """Strips '<'/'>' forbidden by YouTube API and caps UTF-8 byte length below 5,000 bytes."""
    cleaned = (desc or "").replace("<", "‹").replace(">", "›")
    encoded = cleaned.encode("utf-8")
    if len(encoded) <= max_bytes:
        return cleaned
    truncated = encoded[:max_bytes].decode("utf-8", errors="ignore")
    last_nl = truncated.rfind("\n")
    if last_nl > max_bytes // 2:
        truncated = truncated[:last_nl]
    return truncated.rstrip()


def update_existing_video_via_api(meta_path: Path, vid_id: str, skip_playlists: bool = False, skip_captions: bool = False):
    youtube = get_youtube_service()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    localizations = meta.get("localizations", {})
    YT_WIRE_LANG = {"en": "en", "ua": "uk", "ru": "ru"}
    rec_date_iso = infer_recording_date_iso(meta)

    body = {
        "id": vid_id,
        "snippet": {
            "title": meta["title"][:100],
            "description": sanitize_yt_description(meta["description"]),
            "tags": meta.get("tags", []),
            "categoryId": str(meta.get("category_id", "17")),
            "defaultLanguage": "en",
            "defaultAudioLanguage": "en",
        },
    }
    parts = ["snippet"]
    if localizations:
        body["localizations"] = {
            YT_WIRE_LANG.get(lang, lang): {
                "title": loc["title"][:100],
                "description": sanitize_yt_description(loc["description"]),
            }
            for lang, loc in localizations.items()
        }
        parts.append("localizations")
    if rec_date_iso:
        body["recordingDetails"] = {"recordingDate": rec_date_iso}
        parts.append("recordingDetails")

    youtube.videos().update(part=",".join(parts), body=body).execute()
    print(f"Updated video {vid_id} with Imperial metadata, recordingDate={rec_date_iso}, and {list(localizations.keys())} localizations.")
    meta_for_sync = dict(meta)
    if skip_playlists:
        meta_for_sync["playlists"] = []
    if skip_captions:
        meta_for_sync["srt_files"] = {}
    if meta_for_sync.get("playlists") or meta_for_sync.get("srt_files"):
        assign_playlists_and_captions(youtube, vid_id, meta_for_sync, meta_path=meta_path)


def upload_raw_video(
    youtube,
    video_path: Path,
    title: str,
    description: str,
    privacy: str = "unlisted",
    default_lang: str = "en",
    tags: list = None,
    category_id: str = "17",
    thumbnail_path: Path = None,
    playlists: list = None,
    srt_files: dict = None,
    localizations: dict = None,
    recording_date_iso: str = None,
    meta_path: Path | None = None,
) -> tuple[str, str]:
    from googleapiclient.http import MediaFileUpload

    YT_WIRE_LANG = {"en": "en", "ua": "uk", "ru": "ru"}
    rec_iso = recording_date_iso or infer_recording_date_iso({"title": title}, video_path)

    body = {
        "snippet": {
            "title": title[:100],
            "description": sanitize_yt_description(description),
            "tags": tags or [],
            "categoryId": str(category_id),
            "defaultLanguage": default_lang,
            "defaultAudioLanguage": default_lang,
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    parts = ["snippet", "status"]
    if localizations:
        body["localizations"] = {
            YT_WIRE_LANG.get(lang, lang): {
                "title": loc["title"][:100],
                "description": sanitize_yt_description(loc["description"]),
            }
            for lang, loc in localizations.items()
        }
        parts.append("localizations")
    if rec_iso:
        body["recordingDetails"] = {"recordingDate": rec_iso}
        parts.append("recordingDetails")

    print(f"Uploading {video_path.name} via API v3 ({privacy}, lang={default_lang}, recordingDate={rec_iso})...")
    media = MediaFileUpload(str(video_path), chunksize=16 * 1024 * 1024, resumable=True)
    req = youtube.videos().insert(part=",".join(parts), body=body, media_body=media)

    response = None
    while response is None:
        status, response = req.next_chunk()
        if status:
            print(f"  Upload progress ({video_path.name}): {int(status.progress() * 100)}%")

    vid_id = response["id"]
    yt_url = f"https://www.youtube.com/watch?v={vid_id}"
    print(f"  Uploaded! URL: {yt_url}")

    if thumbnail_path and thumbnail_path.exists():
        try:
            youtube.thumbnails().set(
                videoId=vid_id,
                media_body=MediaFileUpload(str(thumbnail_path), mimetype="image/jpeg"),
            ).execute()
            print(f"  Custom thumbnail set: {thumbnail_path.name}")
        except Exception as e:
            print(f"  Note: Thumbnail upload warning: {e}")

    meta_tmp = {
        "playlists": playlists or [],
        "srt_files": srt_files or {},
    }
    assign_playlists_and_captions(youtube, vid_id, meta_tmp, meta_path=meta_path)
    return vid_id, yt_url


def post_pinned_language_comment(youtube, video_id: str, edition_urls: dict):
    """Posts a pinned comment on the English master linking to UA and RU voiced editions."""
    if not edition_urls or not any(k in edition_urls for k in ("ua", "ru")):
        return
    comment_lines = ["🔊 Watch with full localized voice-over:"]
    if "ua" in edition_urls:
        comment_lines.append(f"• 🇺🇦 Українська версія: {edition_urls['ua']}")
    if "ru" in edition_urls:
        comment_lines.append(f"• 🇷🇺 Русская версия: {edition_urls['ru']}")
    comment_text = "\n".join(comment_lines)
    try:
        body = {
            "snippet": {
                "videoId": video_id,
                "topLevelComment": {
                    "snippet": {
                        "textOriginal": comment_text
                    }
                }
            }
        }
        res = youtube.commentThreads().insert(part="snippet", body=body).execute()
        print(f"  Posted language switcher comment on EN master: thread_id={res.get('id')}")
    except Exception as e:
        print(f"  Note: Automated language comment notice: {e}")


def upload_option_b_multilingual(
    meta_path: Path,
    privacy_primary: str = "unlisted",
    privacy_editions: str = "unlisted",
    reuse_en_id: str | None = None,
    delete_old_editions: list[str] | None = None,
):
    """
    Option B Workflow:
    1. Uploads 4K UA edition (_UA.mp4) as Unlisted with Ukrainian metadata & captions.
    2. Uploads 4K RU edition (_RU.mp4) as Unlisted with Russian metadata & captions.
    3. Embeds clickable links to both editions inside the primary English description & localizations.
    4. Uploads the 4K Primary English master as Private by default.
    5. Cross-links the primary video back into the UA & RU descriptions.
    """
    youtube = get_youtube_service()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    primary_mp4 = Path(meta["video_file"])
    if not primary_mp4.is_absolute():
        candidate = meta_path.parent / primary_mp4
        if not candidate.exists():
            exports_cand = Path("~/Movies/Exports").expanduser() / meta_path.parent.parent.name / primary_mp4.name
            if exports_cand.exists():
                candidate = exports_cand
        primary_mp4 = candidate
    thumb_path = Path(meta["thumbnail_file"]) if meta.get("thumbnail_file") else None
    if thumb_path and not thumb_path.is_absolute():
        thumb_path = meta_path.parent / thumb_path
    playlists = meta.get("playlists", [])
    tags = meta.get("tags", [])
    cat_id = meta.get("category_id", "17")
    srt_files = meta.get("srt_files", {})
    locs = meta.get("localizations", {})

    ua_mp4 = primary_mp4.with_name(f"{primary_mp4.stem}_UA.mp4")
    ru_mp4 = primary_mp4.with_name(f"{primary_mp4.stem}_RU.mp4")

    proj_dir = meta_path.parent
    ua_thumb = proj_dir / "thumbnail_ua.jpg"
    ru_thumb = proj_dir / "thumbnail_ru.jpg"
    rec_date_iso = infer_recording_date_iso(meta, primary_mp4)

    edition_urls = {}

    # 1. Upload Ukrainian Edition
    if ua_mp4.exists():
        ua_title = locs.get("ua", {}).get("title", f"{meta['title']} (Українська озвучка)")
        ua_base_desc = locs.get("ua", {}).get("description", meta["description"])
        if "🎵 МУЗИКА" in ua_base_desc or not meta.get("music_credits"):
            ua_desc = f"🇺🇦 Українська версія з авторським закадровим голосом (AI Voice Model).\n\n{ua_base_desc}"
        else:
            ua_tags_hash = " ".join(f"#{t.replace(' ', '')}" for t in (tags or [])[:6])
            ua_desc = (
                "🇺🇦 Українська версія з авторським закадровим голосом (AI Voice Model).\n\n"
                f"{ua_base_desc}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎵 МУЗИКА\n"
                + "\n".join(f"• {mc}" for mc in meta.get("music_credits", []))
                + (f"\n\n{ua_tags_hash}" if ua_tags_hash else "")
            )
        ua_srts = {"ua": srt_files["ua"]} if "ua" in srt_files else {}
        ua_id, ua_url = upload_raw_video(
            youtube,
            video_path=ua_mp4,
            title=ua_title,
            description=ua_desc,
            privacy=privacy_editions,
            default_lang="uk",
            tags=tags + ["Майорка", "Українська озвучка"],
            category_id=cat_id,
            thumbnail_path=ua_thumb if ua_thumb.exists() else thumb_path,
            playlists=playlists,
            srt_files=ua_srts,
            recording_date_iso=rec_date_iso,
            meta_path=meta_path,
        )
        edition_urls["ua"] = ua_url
        register_in_archive_index({"title": ua_title, "description": ua_desc, "chapters": meta.get("chapters", []), "project_name": meta.get("project_name", "")}, ua_url)

    # 2. Upload Russian Edition
    if ru_mp4.exists():
        ru_title = locs.get("ru", {}).get("title", f"{meta['title']} (Русская озвучка)")
        ru_base_desc = locs.get("ru", {}).get("description", meta["description"])
        if "🎵 МУЗЫКА" in ru_base_desc or not meta.get("music_credits"):
            ru_desc = f"🇷🇺 Русская версия с авторским закадровым голосом и живыми диалогами.\n\n{ru_base_desc}"
        else:
            ru_tags_hash = " ".join(f"#{t.replace(' ', '')}" for t in (tags or [])[:6])
            ru_desc = (
                "🇷🇺 Русская версия с авторским закадровым голосом (AI Voice Model).\n\n"
                f"{ru_base_desc}\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "🎵 МУЗЫКА\n"
                + "\n".join(f"• {mc}" for mc in meta.get("music_credits", []))
                + (f"\n\n{ru_tags_hash}" if ru_tags_hash else "")
            )
        ru_srts = {"ru": srt_files["ru"]} if "ru" in srt_files else {}
        ru_id, ru_url = upload_raw_video(
            youtube,
            video_path=ru_mp4,
            title=ru_title,
            description=ru_desc,
            privacy=privacy_editions,
            default_lang="ru",
            tags=tags + ["Майорка", "Русская озвучка"],
            category_id=cat_id,
            thumbnail_path=ru_thumb if ru_thumb.exists() else thumb_path,
            playlists=playlists,
            srt_files=ru_srts,
            recording_date_iso=rec_date_iso,
            meta_path=meta_path,
        )
        edition_urls["ru"] = ru_url
        register_in_archive_index({"title": ru_title, "description": ru_desc, "chapters": meta.get("chapters", []), "project_name": meta.get("project_name", "")}, ru_url)

    # 3. Update Primary English Description with Clickable Links to UA and RU
    primary_desc = meta["description"]
    if "ua" in edition_urls:
        ua_link_line = f"🔊 Повна версія з українською озвучкою: {edition_urls['ua']}\n\n"
        if "🇺🇦 УКРАЇНСЬКОЮ" in primary_desc:
            primary_desc = primary_desc.replace("🇺🇦 УКРАЇНСЬКОЮ\n", f"🇺🇦 УКРАЇНСЬКОЮ\n{ua_link_line}")
        if "ua" in locs and edition_urls["ua"] not in locs["ua"]["description"]:
            locs["ua"]["description"] = ua_link_line + locs["ua"]["description"]

    if "ru" in edition_urls:
        ru_link_line = f"🔊 Полная версия с русской озвучкой: {edition_urls['ru']}\n\n"
        if "🇷🇺 ПО-РУССКИ" in primary_desc:
            primary_desc = primary_desc.replace("🇷🇺 ПО-РУССКИ\n", f"🇷🇺 ПО-РУССКИ\n{ru_link_line}")
        if "ru" in locs and edition_urls["ru"] not in locs["ru"]["description"]:
            locs["ru"]["description"] = ru_link_line + locs["ru"]["description"]

    meta["description"] = primary_desc
    meta["localizations"] = locs
    if rec_date_iso:
        meta["recording_date"] = rec_date_iso

    # 4. Upload or Update Primary English Master (Private by default)
    if reuse_en_id:
        en_id = reuse_en_id
        en_url = f"https://www.youtube.com/watch?v={en_id}"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        update_existing_video_via_api(meta_path, en_id, skip_playlists=True)
        print(f"  Updated existing Primary English Master in-place: {en_url}")
    else:
        en_id, en_url = upload_raw_video(
            youtube,
            video_path=primary_mp4,
            title=meta["title"],
            description=primary_desc,
            privacy=privacy_primary,
            default_lang="en",
            tags=tags,
            category_id=cat_id,
            thumbnail_path=thumb_path,
            playlists=playlists,
            srt_files=srt_files,
            localizations=locs,
            recording_date_iso=rec_date_iso,
            meta_path=meta_path,
        )

    if delete_old_editions:
        for old_vid in delete_old_editions:
            old_vid = old_vid.strip()
            if old_vid:
                try:
                    youtube.videos().delete(id=old_vid).execute()
                    print(f"  Deleted superseded edition video: {old_vid}")
                except Exception as del_e:
                    print(f"  Note: Could not delete {old_vid}: {del_e}")

    # 5. Cross-link Primary English Master into the UA and RU Edition Descriptions
    en_link_note_ua = f"\n\n━━━━━━━━━━━━━━━━━━━━\n🇺🇸 Головне відео з англійською доріжкою: {en_url}"
    en_link_note_ru = f"\n\n━━━━━━━━━━━━━━━━━━━━\n🇺🇸 Главное видео с английской дорожкой: {en_url}"
    if "ua" in edition_urls:
        try:
            update_body_ua = {
                "id": edition_urls["ua"].split("v=")[-1],
                "snippet": {
                    "title": locs.get("ua", {}).get("title", meta["title"])[:100],
                    "description": ua_desc + en_link_note_ua,
                    "tags": tags + ["Майорка", "Українська озвучка"],
                    "categoryId": str(cat_id),
                    "defaultLanguage": "uk",
                    "defaultAudioLanguage": "uk",
                },
            }
            parts_ua = ["snippet"]
            if rec_date_iso:
                update_body_ua["recordingDetails"] = {"recordingDate": rec_date_iso}
                parts_ua.append("recordingDetails")
            youtube.videos().update(
                part=",".join(parts_ua),
                body=update_body_ua,
            ).execute()
            print("  Cross-linked primary EN link into UA edition description (preserving tags & recordingDate)")
        except Exception as e:
            print(f"  Note: UA cross-link warning: {e}")

    if "ru" in edition_urls:
        try:
            update_body_ru = {
                "id": edition_urls["ru"].split("v=")[-1],
                "snippet": {
                    "title": locs.get("ru", {}).get("title", meta["title"])[:100],
                    "description": ru_desc + en_link_note_ru,
                    "tags": tags + ["Майорка", "Русская озвучка"],
                    "categoryId": str(cat_id),
                    "defaultLanguage": "ru",
                    "defaultAudioLanguage": "ru",
                },
            }
            parts_ru = ["snippet"]
            if rec_date_iso:
                update_body_ru["recordingDetails"] = {"recordingDate": rec_date_iso}
                parts_ru.append("recordingDetails")
            youtube.videos().update(
                part=",".join(parts_ru),
                body=update_body_ru,
            ).execute()
            print("  Cross-linked primary EN link into RU edition description (preserving tags & recordingDate)")
        except Exception as e:
            print(f"  Note: RU cross-link warning: {e}")

    # Post automated language switcher comment on EN Master
    post_pinned_language_comment(youtube, en_id, edition_urls)

    meta["published_youtube_url"] = en_url
    meta["published_video_id"] = en_id
    meta["edition_urls"] = edition_urls
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    register_in_archive_index(meta, en_url)
    print("\n========================================================")
    print(f"Option B Multilingual Publishing Complete!")
    print(f"  🇺🇸 English 4K Master ({privacy_primary}): {en_url}")
    if "ua" in edition_urls:
        print(f"  🇺🇦 Ukrainian 4K Edition ({privacy_editions}): {edition_urls['ua']}")
    if "ru" in edition_urls:
        print(f"  🇷🇺 Russian 4K Edition ({privacy_editions}):   {edition_urls['ru']}")
    print("========================================================\n")
    output_facebook_promo_after_publish(meta_path, en_url, edition_urls)
    return en_url


def output_facebook_promo_after_publish(meta_path: Path, live_url: str, edition_urls: dict | None = None):
    try:
        from generate_facebook_promo import build_facebook_promo, print_promo_box
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        promo = build_facebook_promo(meta_path.parent, meta, live_url=live_url, edition_urls=edition_urls)
        print_promo_box(promo)
    except Exception as e:
        print(f"Note: Facebook promo generation notice: {e}")


def main():
    p = argparse.ArgumentParser(description="Upload or update YouTube video via YouTube Data API v3")
    p.add_argument("--metadata", required=True, help="Path to youtube_metadata.json")
    p.add_argument("--privacy", choices=["unlisted", "private", "public"], help="Override privacy status")
    p.add_argument("--option-b", action="store_true", help="Upload Ukrainian & Russian editions as Unlisted, cross-link them in the English description, and upload the English master as Private")
    p.add_argument("--reuse-en-id", help="When used with --option-b, update existing English video ID in-place instead of re-uploading")
    p.add_argument("--delete-old-editions", help="Comma-separated old UA/RU video IDs to delete after uploading replacements")
    p.add_argument("--update-video-id", help="Update an existing video ID with localizations & .srt captions")
    p.add_argument("--skip-playlists", action="store_true", help="Skip playlist insertion when updating existing video")
    p.add_argument("--register-url", help="Register an already-uploaded YouTube URL into youtube_motion_index.jsonl")
    args = p.parse_args()

    meta_path = Path(args.metadata).expanduser().resolve()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if args.register_url:
        meta["published_youtube_url"] = args.register_url
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        register_in_archive_index(meta, args.register_url)
        output_facebook_promo_after_publish(meta_path, args.register_url, meta.get("edition_urls"))
        return

    if args.update_video_id:
        update_existing_video_via_api(meta_path, args.update_video_id, args.skip_playlists)
        yt_url = f"https://www.youtube.com/watch?v={args.update_video_id}"
        meta["published_youtube_url"] = yt_url
        meta["published_video_id"] = args.update_video_id
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        output_facebook_promo_after_publish(meta_path, yt_url, meta.get("edition_urls"))
        return

    if args.option_b:
        old_eds = [x.strip() for x in args.delete_old_editions.split(",") if x.strip()] if args.delete_old_editions else None
        upload_option_b_multilingual(
            meta_path,
            privacy_primary=args.privacy or meta.get("privacy_status", "unlisted"),
            privacy_editions="unlisted",
            reuse_en_id=args.reuse_en_id,
            delete_old_editions=old_eds,
        )
        return

    single_mp4 = Path(meta["video_file"])
    if not single_mp4.is_absolute():
        candidate = meta_path.parent / single_mp4
        if not candidate.exists():
            exports_candidate = Path("~/Movies/Exports").expanduser() / meta_path.parent.parent.name / single_mp4.name
            if exports_candidate.exists():
                candidate = exports_candidate
        single_mp4 = candidate
    single_thumb = Path(meta["thumbnail_file"]) if meta.get("thumbnail_file") else None
    if single_thumb and not single_thumb.is_absolute():
        single_thumb = meta_path.parent / single_thumb

    vid_id, yt_url = upload_raw_video(
        get_youtube_service(),
        video_path=single_mp4,
        title=meta["title"],
        description=meta["description"],
        privacy=args.privacy or meta.get("privacy_status", "unlisted"),
        default_lang="en",
        tags=meta.get("tags", []),
        category_id=meta.get("category_id", "17"),
        thumbnail_path=single_thumb,
        playlists=meta.get("playlists", []),
        srt_files=meta.get("srt_files", {}),
        localizations=meta.get("localizations", {}),
        meta_path=meta_path,
    )
    meta["published_youtube_url"] = yt_url
    meta["published_video_id"] = vid_id
    meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    register_in_archive_index(meta, yt_url)
    output_facebook_promo_after_publish(meta_path, yt_url, meta.get("edition_urls"))


if __name__ == "__main__":
    main()
