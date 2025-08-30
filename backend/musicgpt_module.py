import re
import shutil
import time
from pathlib import Path

import requests
from requests import RequestException

from config import TEST_MODE, MUSICGPT_API_KEY

API_BASE = "https://api.musicgpt.com/api/public/v1"


def extract_prompt_and_lyrics(output, lang="en"):
    """Return (prompt, lyrics) parsed from raw model output."""
    if lang == "en":
        p_pats = [
            r"\*\*Music(?:al)? Prompt:\*\*\s*(.*?)(?:\n{2,}|\*\*Lyrics)",
            r"\*\*Music(?:al)? Prompt\*\*[:：]?\s*(.*?)(?:\n{2,}|\*\*Lyrics)",
            r"Music(?:al)? Prompt[:：]?\s*(.*?)(?:\n{2,}|Lyrics)",
        ]
        l_pats = [
            r"\*\*Lyrics[:：]\*\*\s*([\s\S]+)",
            r"\*\*Lyrics\*\*[:：]?\s*([\s\S]+)",
            r"Lyrics[:：]?\s*([\s\S]+)",
        ]
    else:
        p_pats = [
            r"\*\*音乐风格\*\*[:：]?\s*(.*?)(?:\n{2,}|\*\*歌词)",
            r"音乐风格[:：]?\s*(.*?)(?:\n{2,}|歌词)",
        ]
        l_pats = [
            r"\*\*歌词[:：]\*\*\s*([\s\S]+)",
            r"\*\*歌词\*\*[:：]?\s*([\s\S]+)",
            r"歌词[:：]?\s*([\s\S]+)",
        ]

    prompt = ""
    lyrics = ""

    # Try to extract the prompt
    for pat in p_pats:
        m = re.search(pat, output, re.IGNORECASE | re.DOTALL)
        if m:
            prompt = re.sub(r"\*{1,3}", "", m.group(1)).strip()
            break

    # Try to extract the lyrics
    for pat in l_pats:
        m = re.search(pat, output, re.IGNORECASE | re.DOTALL)
        if m:
            lyrics = m.group(1).strip()
            break

    # Fallback: use the first line if prompt patterns failed
    if not prompt:
        lines = output.strip().splitlines()
        if lines:
            prompt = lines[0].split(":", 1)[-1].strip().lstrip("*- ")
            prompt = re.sub(r"\*{1,3}", "", prompt).strip()

    return prompt, lyrics


def run_inference(assistant_reply: str, out_dir: Path, *, use_mock: bool = TEST_MODE) -> str:
    """Generate music using the MusicGPT API.

    Writes ``lyrics.lrc`` (plain text) and ``audio.wav`` into ``out_dir`` and
    returns the path to the audio file.
    """
    if use_mock:
        # ==== MOCK MODE ====
        prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
        (out_dir / "lyrics.lrc").write_text(lyrics, encoding="utf-8")
        mock_wav_path = Path(__file__).parent / "mock_data" / "mock_audio.wav"
        fake_wav = out_dir / "audio.wav"
        shutil.copy(mock_wav_path, fake_wav)
        return str(fake_wav)

    # ==== REAL MODE ====
    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    (out_dir / "lyrics.lrc").write_text(lyrics, encoding="utf-8")

    if not MUSICGPT_API_KEY:
        raise RuntimeError("MUSICGPT_API_KEY not set")

    payload = {
        "prompt": prompt,
        "lyrics": lyrics,
    }
    headers = {
        "Authorization": MUSICGPT_API_KEY,
        "Content-Type": "application/json",
    }

    try:
        res = requests.post(
            f"{API_BASE}/MusicAI",
            json=payload,
            headers=headers,
            timeout=120,
        )
    except RequestException as e:
        raise RuntimeError(f"MusicGPT request failed: {e}") from e
    if res.status_code == 429:
        raise RuntimeError("MusicGPT rate limit exceeded")
    if res.status_code >= 400:
        try:
            err = res.json().get("error") or res.text
        except Exception:
            err = res.text
        raise RuntimeError(f"MusicGPT API error {res.status_code}: {err}")
    data = res.json()
    if not data.get("success", True):
        raise RuntimeError(data.get("error") or data.get("message") or "MusicGPT API error")
    conv_id = data.get("conversion_id_1") or data.get("conversion_id")
    if not conv_id:
        raise RuntimeError("No conversion id returned from MusicGPT API")

    # Poll for completion
    for _ in range(75):
        try:
            poll = requests.get(
                f"{API_BASE}/conversion/{conv_id}",
                headers=headers,
                timeout=60,
            )
        except RequestException as e:
            raise RuntimeError(f"MusicGPT polling failed: {e}") from e
        if poll.status_code == 404:
            time.sleep(5)
            continue
        if poll.status_code == 429:
            time.sleep(10)
            continue
        if poll.status_code >= 400:
            try:
                err = poll.json().get("error") or poll.text
            except Exception:
                err = poll.text
            raise RuntimeError(f"MusicGPT polling error {poll.status_code}: {err}")
        poll_data = poll.json()
        if not poll_data.get("success", True):
            raise RuntimeError(
                poll_data.get("error") or poll_data.get("message") or "MusicGPT polling error"
            )
        status = poll_data.get("status") or poll_data.get("data", {}).get("status")
        if status in {"completed", "succeeded", "success", True}:
            audio_url = (
                poll_data.get("conversion_path")
                or poll_data.get("audio_url")
                or poll_data.get("data", {}).get("conversion_path")
                or poll_data.get("data", {}).get("audio_url")
            )
            if audio_url:
                try:
                    wav_res = requests.get(audio_url, timeout=120)
                except RequestException as e:
                    raise RuntimeError(f"MusicGPT download failed: {e}") from e
                if wav_res.status_code >= 400:
                    raise RuntimeError(
                        f"MusicGPT download error {wav_res.status_code}: {wav_res.text}"
                    )
                audio_path = out_dir / "audio.wav"
                audio_path.write_bytes(wav_res.content)
                return str(audio_path)
            raise RuntimeError("No audio URL found in completed task")
        if status in {"failed", "error"}:
            raise RuntimeError(f"MusicGPT task failed: {status}")
        time.sleep(5)
    raise TimeoutError("MusicGPT API timed out")
