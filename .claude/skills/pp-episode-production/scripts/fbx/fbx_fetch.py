#!/usr/bin/env python3
"""fbx_fetch.py — fetch the week's HeyGen render BY ITS EXACT NAME, byte-checked.

    python fbx_fetch.py <job_dir>

The name comes from overlay/fbx-week.json -> heygen_name. Exactly one COMPLETED render must
carry it; two is a refusal (picking wrong means the whole video is the wrong take), none is a
plain "not there yet". The API video_url master is downloaded (never the web Download button,
which re-encodes to ~123 kbps) and refused if the byte count differs from what HeyGen stated.
The id is written to renders/heygen-render.json the moment it is known. Never prints the key.
"""
import hashlib
import json
import sys
import time
import urllib.request
from pathlib import Path

job = Path(sys.argv[1]).resolve()
NAME = json.loads((job / "overlay" / "fbx-week.json").read_text(encoding="utf-8"))["heygen_name"]
ENV = job.parents[1] / ".env"
key = next((ln.split("=", 1)[1].strip().strip('"').strip("'") for ln in ENV.read_text(encoding="utf-8").splitlines()
            if ln.strip().startswith("HEYGEN_API_KEY=")), None)
if not key:
    sys.exit("HEYGEN_API_KEY not found in PP Videos\\.env")
H = {"x-api-key": key}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=H), timeout=60) as r:
        return json.load(r)


vids, token = [], None
for _ in range(10):
    d = get("https://api.heygen.com/v1/video.list?limit=100" + (f"&token={token}" if token else "")).get("data", {})
    vids += d.get("videos", [])
    token = d.get("token")
    if not token:
        break
hits = [v for v in vids if (v.get("video_title") or "").strip() == NAME and v.get("status") == "completed"]
if not hits:
    sys.exit(f"No completed HeyGen render named {NAME!r} yet ({len(vids)} listed). Nothing downloaded.")
if len(hits) > 1:
    sys.exit(f"{len(hits)} completed renders are named {NAME!r}: " +
             ", ".join(f"{v['video_id']} (created {v.get('created_at')})" for v in hits) +
             ". Not guessing which take is the right one. Nothing downloaded.")
vid = hits[0]["video_id"]
st = get(f"https://api.heygen.com/v1/video_status.get?video_id={vid}").get("data", {})
meta = {"video_id": vid, "title": NAME, "status": st.get("status"), "duration": st.get("duration"),
        "created_at": st.get("created_at"), "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S")}
(job / "renders").mkdir(exist_ok=True)
(job / "renders" / "heygen-render.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
url = st.get("video_url")
if not url:
    sys.exit("render found but HeyGen gave no video_url yet")
dest = job / "renders" / "presenter-master.mp4"
tmp = dest.with_suffix(".part")
for attempt in range(1, 4):
    got, h = 0, hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=600) as r, open(tmp, "wb") as f:
            stated = int(r.headers.get("Content-Length") or 0) or None
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                f.write(b); h.update(b); got += len(b)
    except Exception as e:  # noqa: BLE001
        print(f"attempt {attempt}: {e}")
        continue
    if not stated or got != stated:
        print(f"attempt {attempt}: server stated {stated} bytes, received {got:,} — not promoted")
        continue
    tmp.replace(dest)
    meta.update(bytes_stated=stated, bytes_received=got, sha256=h.hexdigest())
    (job / "renders" / "heygen-render.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"{NAME}: {vid}, {got:,} bytes = stated, {meta['duration']} s -> {dest}")
    break
else:
    sys.exit("download failed 3 times; nothing promoted")
