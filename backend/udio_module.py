"""Udio fallback client that mirrors the Ace Step PiAPI workflow."""

import base64
import mimetypes
import time
from pathlib import Path

import requests

from config import PIAPI_KEY


def _to_data_url(path: str) -> str:
    """Encode a local audio file as a data URL."""
    mime, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime or 'audio/wav'};base64,{b64}"


def _download_audio(audio_url: str, out_dir: Path) -> str:
    wav_res = requests.get(audio_url, timeout=120)
    wav_res.raise_for_status()
    audio_path = out_dir / "audio.wav"
    audio_path.write_bytes(wav_res.content)
    return str(audio_path)


def run_udio_inference(
    prompt: str,
    lyrics: str,
    out_dir: Path,
    style_audio_path: str | None = None,
) -> str:
    """Generate music via Udio (Suno) using PiAPI."""

    input_payload = {
        "gpt_description_prompt": prompt,
        "prompt": prompt,
        "title": (prompt[:60] + "…") if len(prompt) > 60 else prompt,
        "duration": 30,
    }
    if lyrics.strip():
        input_payload["lyrics"] = lyrics
    if style_audio_path:
        input_payload["audio"] = _to_data_url(style_audio_path)

    payload = {
        "model": "suno",
        "task_type": "generate_music",
        "input": input_payload,
        "config": {},
    }
    headers = {"X-API-Key": PIAPI_KEY}

    res = requests.post(
        "https://api.piapi.ai/api/v1/task",
        json=payload,
        headers=headers,
        timeout=120,
    )
    res.raise_for_status()
    resp_data = res.json()
    task_id = resp_data.get("data", {}).get("task_id") or resp_data.get("task_id")
    if not task_id:
        raise RuntimeError("No task_id returned from Udio API")

    for _ in range(75):
        stat_res = requests.get(
            f"https://api.piapi.ai/api/v1/task/{task_id}",
            headers=headers,
            timeout=60,
        )
        stat_res.raise_for_status()
        stat_data = stat_res.json()
        status = stat_data.get("data", {}).get("status") or stat_data.get("status")
        if status == "completed":
            clips = (
                stat_data.get("data", {})
                .get("output", {})
                .get("clips", {})
            )
            audio_url = None
            if isinstance(clips, dict):
                for clip in clips.values():
                    if isinstance(clip, dict) and clip.get("audio_url"):
                        audio_url = clip["audio_url"]
                        break
            if not audio_url:
                raise RuntimeError("No audio URL found in completed Udio task")
            return _download_audio(audio_url, out_dir)
        if status in {"failed", "error"}:
            raise RuntimeError(f"Udio task failed: {status}")
        time.sleep(5)
    raise TimeoutError("Udio API timed out")
