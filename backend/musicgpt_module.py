import time
import requests
from pathlib import Path
from config import TEST_MODE, MUSICGPT_API_KEY
from udio_module import extract_prompt_and_lyrics

API_BASE = "https://api.musicgpt.com/api/public/v1"


def run_inference(assistant_reply: str, out_dir: Path) -> str:
    """Generate music using the MusicGPT API.

    Writes ``lyrics.lrc`` and ``audio.wav`` into ``out_dir`` and returns the
    path to the audio file.
    """
    if TEST_MODE or not MUSICGPT_API_KEY:
        raise RuntimeError("MusicGPT disabled in test mode or missing API key")

    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    (out_dir / "lyrics.lrc").write_text(lyrics, encoding="utf-8")

    headers = {
        "Authorization": MUSICGPT_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": prompt,
        "lyrics": lyrics,
        "music_style": "",
        "make_instrumental": False,
        "vocal_only": False,
        "voice_id": "",
        "webhook_url": "",
    }

    res = requests.post(f"{API_BASE}/MusicAI", json=payload, headers=headers, timeout=120)
    res.raise_for_status()
    data = res.json()

    conv_ids = [data.get("conversion_id_1"), data.get("conversion_id_2")]
    conv_ids = [cid for cid in conv_ids if cid]
    if not conv_ids:
        raise RuntimeError("No conversion id returned from MusicGPT API")

    for conv_id in conv_ids:
        for _ in range(60):
            poll = requests.get(f"{API_BASE}/conversion/{conv_id}", headers=headers, timeout=120)
            if poll.status_code == 200:
                j = poll.json()
                audio_url = j.get("conversion_path_wav") or j.get("conversion_path")
                status = j.get("status")
                if audio_url:
                    wav_res = requests.get(audio_url, timeout=120)
                    wav_res.raise_for_status()
                    audio_path = out_dir / "audio.wav"
                    audio_path.write_bytes(wav_res.content)
                    return str(audio_path)
                if status in {"failed", "error"}:
                    break
            time.sleep(5)
    raise RuntimeError("MusicGPT API timed out")
