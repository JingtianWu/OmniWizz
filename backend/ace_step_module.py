import re
import shutil
import time
import base64
import mimetypes
import requests
from pathlib import Path

from config import TEST_MODE, PIAPI_KEY
from udio_module import run_udio_inference

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


def _to_data_url(path: str) -> str:
    """Encode a local audio file as a data URL."""
    mime, _ = mimetypes.guess_type(path)
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return f"data:{mime or 'audio/wav'};base64,{b64}"


def _write_mock_audio(out_dir: Path) -> str:
    mock_wav_path = Path(__file__).parent / "mock_data" / "mock_audio.wav"
    fake_wav = out_dir / "audio.wav"
    shutil.copy(mock_wav_path, fake_wav)
    return str(fake_wav)


def _run_ace_step(prompt: str, lyrics: str, out_dir: Path, style_audio_path: str | None):
    input_payload = {
        "style_prompt": prompt,
        "lyrics": lyrics if lyrics.strip() else "[inst]",
        "duration": 30,
        "negative_style_prompt": "",
    }
    if style_audio_path:
        input_payload["style_audio"] = _to_data_url(style_audio_path)

    payload = {
        "model": "Qubico/ace-step",
        "task_type": "txt2audio",
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
                stat_data.get("data", {})
                .get("output", {})
                .get("audio_url")
            )
            if not audio_url:
                raise RuntimeError("No audio URL found in completed task")
            wav_res = requests.get(audio_url, timeout=120)
            wav_res.raise_for_status()
            audio_path = out_dir / "audio.wav"
            audio_path.write_bytes(wav_res.content)
            return str(audio_path)
        if status in {"failed", "error"}:
            raise RuntimeError(f"Ace Step task failed: {status}")
        time.sleep(5)
    raise TimeoutError("Ace Step API timed out")


def run_inference(
    assistant_reply: str,
    out_dir: Path,
    style_audio_path: str | None = None,
    *,
    use_mock: bool = TEST_MODE,
) -> str:
    """
    Generate music using the Ace Step model via PiAPI, with Udio fallback.

    Writes ``lyrics.lrc`` (plain text) and ``audio.wav`` into ``out_dir`` and
    returns the path to the audio file.
    """
    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    (out_dir / "lyrics.lrc").write_text(lyrics, encoding="utf-8")

    if use_mock:
        return _write_mock_audio(out_dir)

    try:
        return _run_ace_step(prompt, lyrics, out_dir, style_audio_path)
    except Exception as ace_err:
        print(f"Ace Step failed: {ace_err}; waiting 5s before Udio fallback")
        time.sleep(5)
        try:
            return run_udio_inference(prompt, lyrics, out_dir, style_audio_path)
        except Exception as udio_err:
            print(f"Udio fallback failed: {udio_err}; using mock audio")
            return _write_mock_audio(out_dir)
