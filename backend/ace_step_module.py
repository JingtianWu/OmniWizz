import re
import shutil
import time
import base64
import mimetypes
import requests
from pathlib import Path
from config import TEST_MODE, PIAPI_KEY

def extract_prompt_and_lyrics(output, lang="en"):
    """Return (style_prompt, lyrics) parsed from raw model output."""
    if lang == "en":
        p_pats = [
            r"\*\*Style Prompt:\*\*\s*(.*?)(?:\n{2,}|\*\*Lyrics)",
            r"\*\*Style Prompt\*\*[:：]?\s*(.*?)(?:\n{2,}|\*\*Lyrics)",
            r"Style Prompt[:：]?\s*(.*?)(?:\n{2,}|Lyrics)",
            # Fallback to older wording
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

    for pat in p_pats:
        m = re.search(pat, output, re.IGNORECASE | re.DOTALL)
        if m:
            prompt = re.sub(r"\*{1,3}", "", m.group(1)).strip()
            break

    for pat in l_pats:
        m = re.search(pat, output, re.IGNORECASE | re.DOTALL)
        if m:
            lyrics = m.group(1).strip()
            break

    if not prompt:
        lines = output.strip().splitlines()
        if lines:
            prompt = lines[0].split(":", 1)[-1].strip().lstrip("*- ")
            prompt = re.sub(r"\*{1,3}", "", prompt).strip()

    return prompt, lyrics


def run_inference(
    assistant_reply: str,
    out_dir: Path,
    *,
    audio_path: str | None = None,
    use_mock: bool = TEST_MODE,
) -> str:
    """
    Generate music using the Ace Step model via PiAPI.

    Writes ``lyrics.lrc`` (plain text) and ``audio.wav`` into ``out_dir`` and
    returns the path to the audio file.
    """
    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    (out_dir / "lyrics.lrc").write_text(lyrics, encoding="utf-8")

    if use_mock:
        mock_wav_path = Path(__file__).parent / "mock_data" / "mock_audio.wav"
        fake_wav = out_dir / "audio.wav"
        shutil.copy(mock_wav_path, fake_wav)
        return str(fake_wav)

    headers = {"X-API-Key": PIAPI_KEY}

    if audio_path:
        with open(audio_path, "rb") as f:
            b64_audio = base64.b64encode(f.read()).decode()
        mime = mimetypes.guess_type(audio_path)[0] or "audio/wav"
        data_url = f"data:{mime};base64,{b64_audio}"
        task_type = "audio2audio"
        input_payload = {
            "style_audio": data_url,
            "style_prompt": prompt,
            "lyrics": lyrics or "[inst]",
        }
    else:
        task_type = "txt2audio"
        input_payload = {
            "style_prompt": prompt,
            "lyrics": lyrics or "[inst]",
            "duration": 30,
        }

    payload = {
        "model": "Qubico/ace-step",
        "task_type": task_type,
        "input": input_payload,
        "config": {},
    }

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
        raise RuntimeError("No task_id returned from Ace Step API")

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
            audio_url = (
                stat_data.get("data", {}).get("output", {}).get("audio_url")
                or stat_data.get("output", {}).get("audio_url")
            )
            if audio_url:
                wav_res = requests.get(audio_url, timeout=120)
                wav_res.raise_for_status()
                audio_path_out = out_dir / "audio.wav"
                audio_path_out.write_bytes(wav_res.content)
                return str(audio_path_out)
            raise RuntimeError("No audio URL found in completed task")
        if status in {"failed", "error"}:
            raise RuntimeError(f"Ace Step task failed: {status}")
        time.sleep(5)
    raise TimeoutError("Ace Step API timed out")
