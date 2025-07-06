import re
import shutil
import requests
from pathlib import Path
from config import TEST_MODE, DIFFRHYTHM_API_KEY

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

    payload = {"prompt": prompt, "lyrics": lrc}
    headers = {"Authorization": f"Bearer {DIFFRHYTHM_API_KEY}"}
    res = requests.post(
        "https://api.diffrhythm.com/generate",
        json=payload,
        headers=headers,
        timeout=120,
    )
    res.raise_for_status()

    audio_path = out_dir / "audio.wav"
    audio_path.write_bytes(res.content)
    return str(audio_path)
