# Generate a Practical Punting presenter render via the HeyGen API — THE way we
# make the presenter (no more browser). Locked Floyd/Gordon avatar + locked
# "PP Gordon Floyd" cloned voice (Auto engine, English-Australia accent),
# captions/subtitles OFF (no burn-in).
# Creates the video, polls to completion (matching on video_url present — skips
# the phantom `pending` duplicates), and downloads the CLEAN MP4. We do NOT fetch
# HeyGen's SRT — timings come from build_shot_map.py, so this job ends at the MP4.
#
# Uses the CURRENT endpoint POST /v3/videos. (The old /v2/video/generate is
# legacy — HeyGen's API explicitly tells AI agents not to use it; removed
# 2026-10-31.) In v3 there is NO "talking_photo" type: a photo avatar is
# referenced by `type:"avatar"` + `avatar_id`, and burned-in captions are
# disabled by OMITTING the `caption` field entirely.
#
# Usage:
#   python heygen_generate.py <spoken-words.txt> <out.mp4> [options]
#     --dry-run                 build + print the payload (key redacted), don't POST
#     --test-text "..."         use this short text instead of the .txt (proof runs)
#     --background-url URL       grandstand background as a public image URL
#     --background-asset-id ID   grandstand background as a HeyGen asset id
#     --resolution 1080p|720p|4k (default 1080p)
#     --poll-timeout SECONDS     default 2400 (40 min)
#
# LOCKED INGREDIENTS (validated against the API 2026-07-21; see heygen-api-setup memory):
#   avatar_id de774dd2f3ef4a52bc31dee6fc91f118  (Floyd/Gordon — image matches the EP renders;
#     it is a legacy /v1/talking_photo.list id. v3 `avatar_id` accepts photo-avatar looks;
#     CONFIRM on the first credited run that v3 accepts this legacy id — if not, the Floyd
#     look must be re-created as a v3 photo avatar. The account's newer "Gordon" photo-avatar
#     GROUP look is a DIFFERENT face, so do not substitute it.)
#   voice a6d512a13a3c40c1b79fdd39856a2b72  ("PP Gordon Floyd" — INSTANT VOICE CLONE of
#     Jodie's real good Floyd voice, cloned from 99s of clean EP01 audio 2026-07-22 via
#     POST /v3/voices/clone. THE locked series voice, ear-confirmed PERFECT by Jodie on a
#     real web-app render. Ends the Floyd/Patrick confusion for all ~50 videos.)
#     Voice engine = Auto ; Accent = English (Australia) — as saved on the voice in HeyGen.
#   *** NEVER set the voice engine to ElevenLabs. *** ElevenLabs removes the accent option
#     and forces an American accent — that is the exact bug that made EP04 sound wrong.
#     Leave the engine at its saved default (Auto) so the Australian accent baked into the
#     clone is used. Do NOT add an engine/model override to the payload.
#   caption: OMITTED  (never burned into the frame)
#
# GRANDSTAND BACKGROUND — FLAGGED, not hard-coded. The saved grandstand image is a
# HeyGen Upload; this account exposes NO asset-list endpoint (v1/v2 asset.list all
# 404), so its id/URL can't be discovered via the API. Pass --background-url (or
# --background-asset-id), or set HEYGEN_GRANDSTAND_URL / HEYGEN_GRANDSTAND_ASSET_ID
# in .env. With none set, the render uses the avatar's own backdrop — fine for a
# proof, NOT for a real episode.
import argparse, json, os, pathlib, re, sys, time, urllib.request, urllib.error

BASE = "https://api.heygen.com"
AVATAR_ID = "de774dd2f3ef4a52bc31dee6fc91f118"   # Floyd/Gordon
# LOCKED SERIES VOICE — "PP Gordon Floyd" instant voice clone (Auto engine, EN-Australia
# accent). Ear-confirmed PERFECT by Jodie 2026-07-22. NEVER switch the engine to
# ElevenLabs (it strips the accent -> American). Keep the payload engine-agnostic (voice_id
# only, no engine/model field) so the voice's saved Auto+AU default is used.
VOICE_ID = "a6d512a13a3c40c1b79fdd39856a2b72"     # PP Gordon Floyd (cloned; Auto / EN-AU)

def load_key():
    # THE .env IS ON DRIVE AND STAYS THERE — TIER 1, never in the repo.
    # This script moved into the repo on 28 Jul 2026 ("code in GitHub, media on
    # Drive"), so walking up from __file__ no longer reaches PP Videos/.env — it
    # reaches the repo root, which has no .env and a .gitignore forbidding one.
    # Look at PP_VIDEOS explicitly first, then fall back to the old parent walk
    # so the script still works if it is ever run from a Drive copy.
    key = os.environ.get("HEYGEN_API_KEY")
    if not key:
        pp = pathlib.Path(os.environ.get("PP_VIDEOS_DIR", r"G:\My Drive\PP Videos"))
        env = pp / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.startswith("HEYGEN_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break
    if not key:
        for parent in pathlib.Path(__file__).resolve().parents:
            env = parent / ".env"
            if env.exists():
                for line in env.read_text(encoding="utf-8").splitlines():
                    if line.startswith("HEYGEN_API_KEY="):
                        key = line.split("=", 1)[1].strip().strip('"').strip("'")
                        break
            if key:
                break
    if not key:
        sys.exit("HEYGEN_API_KEY not found (checked env + a .env up the tree)")
    return key

def redact(s, key):
    return s.replace(key, "***REDACTED***") if key else s

def api(method, path, key, body=None, query=""):
    url = f"{BASE}{path}{query}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
        headers={"x-api-key": key, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit(f"HTTP {e.code} on {method} {path}: {redact(e.read().decode(errors='replace'), key)}")

def strip_header(txt):
    # same convention as build_shot_map.py: drop a production-notes header
    m = re.search(r"(?im)^.*paste\b.*\bbelow\b.*$", txt)
    if m: txt = txt[m.end():]
    paras = [p.strip() for p in txt.split("\n\n") if p.strip()]
    while paras and all(ln.lstrip().startswith("#") for ln in paras[0].splitlines()):
        paras.pop(0)
    return "\n\n".join(paras)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("words"); ap.add_argument("out")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--test-text", default=None)
    ap.add_argument("--background-url", default=os.environ.get("HEYGEN_GRANDSTAND_URL"))
    ap.add_argument("--background-asset-id", default=os.environ.get("HEYGEN_GRANDSTAND_ASSET_ID"))
    ap.add_argument("--resolution", default="1080p")
    ap.add_argument("--poll-timeout", type=int, default=2400)
    a = ap.parse_args()
    key = load_key()

    text = a.test_text if a.test_text else strip_header(pathlib.Path(a.words).read_text(encoding="utf-8"))
    if not text.strip():
        sys.exit("empty script text")

    payload = {
        "type": "avatar",
        "avatar_id": AVATAR_ID,
        "script": text,
        "voice_id": VOICE_ID,
        "resolution": a.resolution,
        # caption field OMITTED entirely -> no burned-in captions (v3 rule)
    }
    if a.background_url:
        payload["background"] = {"type": "image", "url": a.background_url}
    elif a.background_asset_id:
        payload["background"] = {"type": "image", "image_asset_id": a.background_asset_id}

    if a.dry_run:
        preview = dict(payload)
        preview["script"] = text[:80] + ("…" if len(text) > 80 else "")
        print("DRY RUN — POST /v3/videos payload:")
        print(json.dumps(preview, indent=2))
        print(f"\n(script chars: {len(text)}; background set: {'background' in payload})")
        if "background" not in payload:
            print("NOTE: no grandstand background set — see the header flag.")
        return

    if "background" not in payload:
        print("WARNING: generating with NO grandstand background (avatar's own backdrop). "
              "Set --background-url/--background-asset-id for a real episode.", file=sys.stderr)

    print("creating video (POST /v3/videos)…", flush=True)
    res = api("POST", "/v3/videos", key, body=payload)
    vid = (res.get("data") or {}).get("video_id") or res.get("video_id")
    if not vid:
        sys.exit(f"no video_id in response: {redact(json.dumps(res), key)}")
    print(f"video_id: {vid} — polling…", flush=True)

    deadline = time.time() + a.poll_timeout
    delay = 10
    while time.time() < deadline:
        st = api("GET", "/v1/video_status.get", key, query=f"?video_id={vid}")
        d = st.get("data") or {}
        status, url = d.get("status"), d.get("video_url")
        if status == "failed":
            sys.exit(f"render failed: {redact(json.dumps(d.get('error') or d), key)}")
        if status == "completed" and url:   # completion = video_url actually present
            print("completed.", flush=True)
            out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(out))
            print(f"downloaded clean MP4 -> {out}  ({out.stat().st_size} bytes)")
            return
        print(f"  status={status} (waiting {delay}s)", flush=True)
        time.sleep(delay); delay = min(delay + 5, 30)
    sys.exit("timed out waiting for completion")

if __name__ == "__main__":
    main()
