import time
import mimetypes
import requests
from pathlib import Path
from config import TEST_MODE, MUSIC_AI_API_KEY


def _auth_header() -> dict:
    """Return the Authorization header for Music AI."""
    if not MUSIC_AI_API_KEY:
        raise RuntimeError("MUSIC_AI_API_KEY not configured")
    if MUSIC_AI_API_KEY.lower().startswith("bearer "):
        token = MUSIC_AI_API_KEY
    else:
        token = f"Bearer {MUSIC_AI_API_KEY}"
    return {"Authorization": token}

BASE_URL = "https://api.music.ai/v1"
WORKFLOW_SLUG = "chord-transcription"


def _upload_file(audio_path: Path):
    headers = _auth_header()
    res = requests.get(f"{BASE_URL}/upload", headers=headers, timeout=30)
    res.raise_for_status()
    data = res.json()
    with open(audio_path, "rb") as f:
        ct, _ = mimetypes.guess_type(str(audio_path))
        requests.put(data["uploadUrl"], data=f, headers={"Content-Type": ct or "audio/mpeg"}, timeout=60).raise_for_status()
    return data["downloadUrl"]


def transcribe_chords(audio_path: str):
    """Return {{'key': str, 'chords': list}}"""
    if TEST_MODE:
        return {"key": "C major", "chords": ["C", "G", "Am", "F"]}

    dl_url = _upload_file(Path(audio_path))
    headers = _auth_header()
    headers["Content-Type"] = "application/json"
    payload = {
        "name": "Chord transcription",
        "workflow": WORKFLOW_SLUG,
        "params": {"inputUrl": dl_url},
    }
    res = requests.post(f"{BASE_URL}/job", json=payload, headers=headers, timeout=30)
    res.raise_for_status()
    job_id = res.json()["id"]

    for _ in range(60):
        jr = requests.get(f"{BASE_URL}/job/{job_id}", headers=headers, timeout=30)
        jr.raise_for_status()
        info = jr.json()
        if info.get("status") == "SUCCEEDED":
            result = info.get("result", {})
            url = result.get("chords") or result.get("downloadUrl")
            if url:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                return r.json()
            return result
        if info.get("status") == "FAILED":
            raise RuntimeError(f"Music AI job failed: {info.get('error')}")
        time.sleep(5)
    raise TimeoutError("Music AI job timed out")
