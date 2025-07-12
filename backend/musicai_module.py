import requests
from pathlib import Path
from config import TEST_MODE, MUSIC_AI_API_KEY

MOCK_RESULT = {"key": "C major", "chords": ["C", "G", "Am", "F"]}

TRANSCRIBE_URL = "https://api.musicai.example/transcribe"


def transcribe_chords(audio_path: str):
    """Return a dict with 'key' and 'chords' from the given audio file."""
    if TEST_MODE:
        return MOCK_RESULT

    if not MUSIC_AI_API_KEY:
        raise RuntimeError("MUSIC_AI_API_KEY not set")

    with open(audio_path, "rb") as f:
        files = {"file": (Path(audio_path).name, f, "audio/wav")}
        headers = {"Authorization": f"Bearer {MUSIC_AI_API_KEY}"}
        resp = requests.post(TRANSCRIBE_URL, files=files, headers=headers, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        return {"key": data.get("key"), "chords": data.get("chords")}
