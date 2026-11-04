#!/usr/bin/env python3
"""
upload_youtube_studio_chrome.py
End-to-end automated YouTube Studio uploader using Google Chrome's AppleEvent
JavaScript bridge (osascript via stdin). Bypasses macOS TCC DevToolsActivePort
restrictions and YouTube Studio CSP while streaming full 4K MP4 masters,
attaching custom 1080p thumbnails, setting Title, Chapter-indexed Description,
Playlists ('Mallorca', '2026 Mallorca Cycling'), 'Not Made for Kids', Tags,
and 'Private' visibility by default.
"""

import argparse
import base64
import json
import subprocess
import time
from pathlib import Path


def run_js(code: str) -> str:
    escaped = code.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")
    osa = f'''
    tell application "Google Chrome"
        repeat with w in windows
            repeat with t in tabs of w
                if URL of t contains "studio.youtube.com" then
                    return execute t javascript "{escaped}"
                end if
            end repeat
        end repeat
    end tell
    '''
    res = subprocess.run(["osascript"], input=osa, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"osascript error: {res.stderr}")
    return res.stdout.strip()


def upload_to_youtube_studio(meta_path: Path) -> str:
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    video_path = Path(meta["video_file"])
    thumb_path = Path(meta["thumbnail_file"])

    # 1. Ensure Upload modal is open
    has_input = run_js("Boolean(document.querySelector('input[name=Filedata]'))")
    if has_input != "true":
        run_js("const btn = document.querySelector('#create-icon, ytcp-button#create-icon, [aria-label*=Create]'); if (btn) btn.click();")
        time.sleep(1.0)
        run_js("const u = Array.from(document.querySelectorAll('tp-yt-paper-item, ytcp-ve, [test-id=upload-beta]')).find(el => el.innerText && el.innerText.includes('Upload videos')); if (u) u.click();")
        time.sleep(1.5)

    # 2. Stream video file in 12MB chunks into window.__ytVideoChunks
    raw_bytes = video_path.read_bytes()
    total_len = len(raw_bytes)
    chunk_size = 12 * 1024 * 1024
    run_js("window.__ytVideoChunks = []; 'ok'")
    print(f"Transferring {video_path.name} ({total_len / (1024*1024):.1f} MB) into YouTube Studio...")

    for offset in range(0, total_len, chunk_size):
        chunk = raw_bytes[offset:offset + chunk_size]
        b64 = base64.b64encode(chunk).decode("ascii")
        js_chunk = (
            f"(() => {{"
            f"const bin = atob('{b64}');"
            f"const arr = new Uint8Array(bin.length);"
            f"for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);"
            f"window.__ytVideoChunks.push(arr);"
            f"return window.__ytVideoChunks.length;"
            f"}})()"
        )
        idx = run_js(js_chunk)
        print(f"  Chunk {idx} transferred ({min(offset + chunk_size, total_len) * 100 // total_len}%)")

    # 3. Assemble File and dispatch to input[name=Filedata]
    fname = video_path.name
    run_js(
        f"(() => {{"
        f"const blob = new Blob(window.__ytVideoChunks, {{ type: 'video/mp4' }});"
        f"window.__ytVideoChunks = [];"
        f"const file = new File([blob], '{fname}', {{ type: 'video/mp4' }});"
        f"const dt = new DataTransfer();"
        f"dt.items.add(file);"
        f"const inp = document.querySelector('input[name=Filedata]');"
        f"inp.files = dt.files;"
        f"inp.dispatchEvent(new Event('change', {{ bubbles: true }}));"
        f"return 'dispatched:' + file.size;"
        f"}})()"
    )

    # 4. Wait for Details wizard to open
    for _ in range(30):
        time.sleep(1.0)
        ready = run_js("Boolean(document.querySelector('#title-textarea #textbox'))")
        if ready == "true":
            break
    time.sleep(2.0)

    video_url = run_js(
        "Array.from(document.querySelectorAll('a')).map(a => a.href).find(h => h && (h.includes('youtu.be/') || h.includes('youtube.com/watch'))) || ''"
    )
    print("Assigned YouTube URL:", video_url)

    # 5. Set Title & Description
    title_b64 = base64.b64encode(meta["title"].encode("utf-8")).decode("ascii")
    desc_b64 = base64.b64encode(meta["description"].encode("utf-8")).decode("ascii")
    run_js(
        f"(() => {{"
        f"const dec = (b64) => new TextDecoder().decode(Uint8Array.from(atob(b64), c => c.charCodeAt(0)));"
        f"const tBox = document.querySelector('#title-textarea #textbox');"
        f"if (tBox) {{ tBox.focus(); tBox.textContent = dec('{title_b64}'); tBox.dispatchEvent(new Event('input', {{ bubbles: true }})); }}"
        f"const dBox = document.querySelector('#description-textarea #textbox');"
        f"if (dBox) {{ dBox.focus(); dBox.textContent = dec('{desc_b64}'); dBox.dispatchEvent(new Event('input', {{ bubbles: true }})); }}"
        f"}})()"
    )

    # 6. Attach Custom Thumbnail
    if thumb_path.exists():
        thumb_b64 = base64.b64encode(thumb_path.read_bytes()).decode("ascii")
        run_js(
            f"(() => {{"
            f"const bin = atob('{thumb_b64}');"
            f"const arr = new Uint8Array(bin.length);"
            f"for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);"
            f"const file = new File([arr], 'thumbnail.jpg', {{ type: 'image/jpeg' }});"
            f"const dt = new DataTransfer();"
            f"dt.items.add(file);"
            f"const inp = document.querySelector('input#file-loader');"
            f"if (inp) {{ inp.files = dt.files; inp.dispatchEvent(new Event('change', {{ bubbles: true }})); }}"
            f"}})()"
        )

    # 7. Select Playlists
    playlists = meta.get("playlists", ["Mallorca", "2026 Mallorca Cycling"])
    run_js("const pl = document.querySelector('ytcp-video-metadata-playlists ytcp-text-dropdown-trigger'); if (pl) pl.click();")
    time.sleep(1.5)
    pl_json = json.dumps(playlists)
    run_js(
        f"(() => {{"
        f"const targets = {pl_json};"
        f"const ves = Array.from(document.querySelectorAll('ytcp-checkbox-group ytcp-ve'));"
        f"for (const ve of ves) {{"
        f"  const txt = ve.innerText.trim();"
        f"  if (targets.includes(txt)) {{"
        f"    const cb = ve.querySelector('ytcp-checkbox-lit, label');"
        f"    if (cb) cb.click();"
        f"  }}"
        f"}}"
        f"const done = document.querySelector('ytcp-playlist-dialog .done-button, ytcp-playlist-dialog ytcp-button[label=Done]');"
        f"if (done) done.click();"
        f"}})()"
    )
    time.sleep(1.0)

    # 8. Audience (Not Made For Kids) + Show More -> Tags
    run_js(
        "(() => {"
        "const r = document.querySelector('tp-yt-paper-radio-button[name=VIDEO_MADE_FOR_KIDS_NOT_MFK]');"
        "if (r) r.click();"
        "const t = document.querySelector('#toggle-button');"
        "if (t && t.innerText.includes('Show more')) t.click();"
        "})()"
    )
    time.sleep(1.0)

    tags_csv = ", ".join(meta.get("tags", [])) + ","
    run_js(
        f"(() => {{"
        f"const inp = document.querySelector('input[aria-label=Tags], #tags-container input#text-input');"
        f"if (!inp) return;"
        f"inp.focus();"
        f"const dt = new DataTransfer();"
        f"dt.setData('text/plain', '{tags_csv}');"
        f"inp.dispatchEvent(new ClipboardEvent('paste', {{ clipboardData: dt, bubbles: true, cancelable: true }}));"
        f"}})()"
    )
    time.sleep(1.0)

    # 9. Go to Visibility step, select PRIVATE by default, wait for upload completion, and click Save
    run_js("const visStep = document.querySelector('#step-title-3, [test-id=REVIEW]'); if (visStep) visStep.click();")
    time.sleep(1.0)
    privacy = meta.get("privacy_status", "private").upper()
    run_js(f"const p = document.querySelector('tp-yt-paper-radio-button[name={privacy}]'); if (p) p.click();")

    for _ in range(120):
        disabled = run_js("document.querySelector('#done-button')?.getAttribute('aria-disabled') || 'false'")
        if disabled != "true":
            break
        time.sleep(2.0)

    run_js("const doneBtn = document.querySelector('#done-button'); if (doneBtn) doneBtn.click();")
    time.sleep(3.0)
    return video_url


def main():
    parser = argparse.ArgumentParser(description="Upload 4K video and metadata to YouTube Studio via Chrome")
    parser.add_argument(
        "--metadata",
        required=True,
        help="Path to youtube_metadata.json",
    )
    args = parser.parse_args()
    url = upload_to_youtube_studio(Path(args.metadata))
    print("Completed upload:", url)


if __name__ == "__main__":
    main()
