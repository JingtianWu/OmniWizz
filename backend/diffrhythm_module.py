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
            r"\*\*Music(?:al)? Prompt\*\*[:：]?\s*(.*?)(?:\n{2,}|\*\*Lyrics)",
            r"Music(?:al)? Prompt[:：]?\s*(.*?)(?:\n{2,}|Lyrics)",
        ]
        l_pats = [
            r"\*\*Lyrics\*\*[:：]?\s*([\s\S]+)",
            r"Lyrics[:：]?\s*([\s\S]+)",
        ]
    else:
        p_pats = [
            r"\*\*音乐风格\*\*[:：]?\s*(.*?)(?:\n{2,}|\*\*歌词)",
            r"音乐风格[:：]?\s*(.*?)(?:\n{2,}|歌词)",
        ]
        l_pats = [
            r"\*\*歌词\*\*[:：]?\s*([\s\S]+)",
            r"歌词[:：]?\s*([\s\S]+)",
        ]

    prompt = ""
    lyrics = ""
    for pat in p_pats:
        m = re.search(pat, output, re.IGNORECASE | re.DOTALL)
        if m:
            prompt = m.group(1).strip()
            break

    for pat in l_pats:
        m = re.search(pat, output, re.IGNORECASE | re.DOTALL)
        if m:
            lyrics = m.group(1).strip()
            break

    if not prompt:
        # Fallback to the first line if pattern failed
        lines = output.strip().splitlines()
        if lines:
            prompt = lines[0].split(":", 1)[-1].strip().lstrip("*- ")

    return prompt, lyrics

def normalize_lrc(raw_lyrics):
    timestamp_pattern = re.compile(r"(\[\d{2}:\d{2}\.\d{2}\])")
    parts = timestamp_pattern.split(raw_lyrics)
    lines = []
    
    for i in range(1, len(parts), 2):
        ts = parts[i]
        txt = parts[i+1].strip() if (i+1) < len(parts) else ""
        txt = re.sub(r"[\[\]]+", "", txt).strip()
        if txt:
            lines.append(f"{ts}{txt}")
            
    return "\n".join(lines)

def run_inference(assistant_reply: str, out_dir: Path, *, use_mock: bool = TEST_MODE) -> str:
    """
    Run DiffRhythm’s infer.py in-process, writing
    - out_dir/lyrics.lrc
    - out_dir/audio.wav
    Returns path to audio.wav
    """
    if use_mock:
        # ==== MOCK MODE ====

        # 1) extract prompt & lyrics normally (so you're still exercising extraction logic)
        prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
        lrc = normalize_lrc(lyrics)
        (out_dir / "lyrics.lrc").write_text(lrc, encoding="utf-8")

        # 2) copy real mock audio file
        mock_wav_path = Path(__file__).parent / "mock_data" / "mock_audio.wav"
        fake_wav = out_dir / "audio.wav"
        shutil.copy(mock_wav_path, fake_wav)

        return str(fake_wav)

    # ==== NORMAL REAL MODE ====
    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    lrc = normalize_lrc(lyrics)
    (out_dir / "lyrics.lrc").write_text(lrc, encoding="utf-8")

    payload = {
        "model": "Qubico/diffrhythm",
        "task_type": "txt2audio-base",
        "input": {
            "lyrics": lrc,
            "style_prompt": prompt,
            "style_audio": "",
        },
        "config": {},
    }
    headers = {"x-api-key": PIAPI_KEY}

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
        raise RuntimeError("No task_id returned from DiffRhythm API")

    for _ in range(60):
        stat_res = requests.get(
            f"https://api.piapi.ai/api/v1/task/{task_id}",
            headers={"X-API-Key": PIAPI_KEY},
            timeout=60,
        )
        stat_res.raise_for_status()
        stat_data = stat_res.json()
        status = stat_data.get("data", {}).get("status") or stat_data.get("status")
        if status == "completed":
            works = stat_data.get("data", {}).get("works") or stat_data.get("works")
            if works:
                audio_url = works[0]["resource"]["resource"]
                wav_res = requests.get(audio_url, timeout=120)
                wav_res.raise_for_status()
                audio_path = out_dir / "audio.wav"
                audio_path.write_bytes(wav_res.content)
                return str(audio_path)
            raise RuntimeError("No works found in completed task")
        if status in {"failed", "error"}:
            raise RuntimeError(f"DiffRhythm task failed: {status}")
        time.sleep(5)
    raise TimeoutError("DiffRhythm API timed out")
