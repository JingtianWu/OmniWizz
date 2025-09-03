import re
import shutil
import time
import requests
from pathlib import Path
from config import TEST_MODE, BEATOVEN_API_KEY

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
            prompt = re.sub(r'\*{1,3}', '', m.group(1)).strip()
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
            prompt = re.sub(r'\*{1,3}', '', prompt).strip()

    return prompt, lyrics


def run_inference(assistant_reply: str, out_dir: Path, *, use_mock: bool = TEST_MODE) -> str:
    """
    Generate music using the Beatoven.ai API.

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
    if not BEATOVEN_API_KEY:
        raise RuntimeError("BEATOVEN_API_KEY not set")

    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    (out_dir / "lyrics.lrc").write_text(lyrics, encoding="utf-8")

    payload = {
        "prompt": {"text": prompt},
        "format": "wav",
        "looping": False,
    }
    headers = {
        "Authorization": f"Bearer {BEATOVEN_API_KEY}",
        "Content-Type": "application/json",
    }

    res = requests.post(
        "https://public-api.beatoven.ai/api/v1/tracks/compose",
        json=payload,
        headers=headers,
        timeout=120,
    )
    if res.status_code == 401:
        raise RuntimeError("Unauthorized: check BEATOVEN_API_KEY")
    res.raise_for_status()
    resp_data = res.json()
    task_id = resp_data.get("task_id")
    if not task_id:
        raise RuntimeError("No task_id returned from Beatoven API")

    for _ in range(75):
        stat_res = requests.get(
            f"https://public-api.beatoven.ai/api/v1/tasks/{task_id}",
            headers=headers,
            timeout=60,
        )
        if stat_res.status_code == 401:
            raise RuntimeError("Unauthorized: check BEATOVEN_API_KEY")
        stat_res.raise_for_status()
        stat_data = stat_res.json()
        status = stat_data.get("status")
        if status == "composed":
            track_url = stat_data.get("meta", {}).get("track_url")
            if track_url:
                wav_res = requests.get(track_url, timeout=120)
                wav_res.raise_for_status()
                audio_path = out_dir / "audio.wav"
                audio_path.write_bytes(wav_res.content)
                return str(audio_path)
            raise RuntimeError("No track URL found in composed task")
        if status in {"failed", "error"}:
            raise RuntimeError(f"Beatoven task failed: {status}")
        time.sleep(5)
    raise TimeoutError("Beatoven API timed out")
