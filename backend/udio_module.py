import re
import shutil
import time
import requests
from pathlib import Path
from config import TEST_MODE, PIAPI_KEY

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
    Generate music using the Udio model via PiAPI.

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

    payload = {
        "model": "music-u",
        "task_type": "generate_music",
        "input": {
            "prompt": prompt,
            "lyrics_type": "user",
            "lyrics": lyrics,
        },
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
        # print("📄 Udio poll status data:", stat_data)
        if status == "completed":
            # NEW: Check audio inside songs[]
            songs = stat_data.get("data", {}).get("output", {}).get("songs", [])
            for song in songs:
                audio_url = song.get("song_path")
                if audio_url:
                    wav_res = requests.get(audio_url, timeout=120)
                    wav_res.raise_for_status()
                    audio_path = out_dir / "audio.wav"
                    audio_path.write_bytes(wav_res.content)
                    return str(audio_path)

            # FALLBACK: Previous formats
            audio_url = (
                stat_data.get("data", {}).get("output", {}).get("audio_url")
                or stat_data.get("data", {}).get("outputs", [{}])[0].get("url")
                or stat_data.get("data", {}).get("works", [{}])[0].get("resource", {}).get("resource")
                or stat_data.get("output", {}).get("audio_url")
                or stat_data.get("outputs", [{}])[0].get("url")
                or stat_data.get("works", [{}])[0].get("resource", {}).get("resource")
            )

            if audio_url:
                wav_res = requests.get(audio_url, timeout=120)
                wav_res.raise_for_status()
                audio_path = out_dir / "audio.wav"
                audio_path.write_bytes(wav_res.content)
                return str(audio_path)

            raise RuntimeError("No audio URL found in completed task")
        if status in {"failed", "error"}:
            raise RuntimeError(f"Udio task failed: {status}")
        time.sleep(5)
    raise TimeoutError("Udio API timed out")
