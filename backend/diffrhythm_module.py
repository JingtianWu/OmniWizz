import re
import time
import platform
import sys
import os
import runpy
import shutil
from pathlib import Path
from config import TEST_MODE

def extract_prompt_and_lyrics(output, lang='en'):
    if lang == 'en':
        p_pat = r"\*\*Music(?:al)? Prompt:\*\*\s*(.*?)(?:\n{2,}|\*\*Lyrics:\*\*)"
        l_pat = r"\*\*Lyrics:\*\*\s*([\s\S]+)"
    else:
        p_pat = r"\*\*音乐风格：\*\*\s*(.*?)(?:\n{2,}|\*\*歌词：\*\*)"
        l_pat = r"\*\*歌词：\*\*\s*([\s\S]+)"
    prompt = re.search(p_pat, output, re.IGNORECASE)
    lyrics = re.search(l_pat, output, re.IGNORECASE)
    return (prompt.group(1).strip() if prompt else "",
            lyrics.group(1).strip() if lyrics else "")

def normalize_lrc(raw_lyrics):
    pattern = re.compile(r"(\[\d{2}:\d{2}\.\d{2}\])")
    parts = pattern.split(raw_lyrics)
    lines = []
    for i in range(1, len(parts), 2):
        ts, txt = parts[i], parts[i+1].strip() if (i+1)<len(parts) else ""
        if txt:
            lines.append(f"{ts}{txt}")
    return "\n".join(lines)

def run_inference(assistant_reply: str, out_dir: Path) -> str:
    """
    Run DiffRhythm’s infer.py in-process, writing
    - out_dir/lyrics.lrc
    - out_dir/audio.wav
    Returns path to audio.wav
    """
    if TEST_MODE:
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
    project_root = Path(__file__).parent.parent
    repo_root    = project_root / "DiffRhythm"

    # 1) write normalized .lrc
    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    lrc = normalize_lrc(lyrics)
    (out_dir / "lyrics.lrc").write_text(lrc, encoding="utf-8")

    # 2) set up environment
    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    if platform.system() == 'Darwin':
        os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = (
          '/opt/homebrew/Cellar/espeak-ng/1.52.0/lib/libespeak-ng.dylib'
        )

    # 3) build args for infer.py
    args = [
      "--lrc-path",   str(out_dir/"lyrics.lrc"),
      "--ref-prompt", prompt,
      "--audio-length","95",
      "--repo-id",    "ASLP-lab/DiffRhythm-1_2",
      "--output-dir", str(out_dir),
      "--chunked",
      "--batch-infer-num","5"
    ]

    infer_dir   = repo_root / "infer"
    infer_script= infer_dir  / "infer.py"

    # 4) hack cwd, sys.argv & sys.path so infer.py just works
    old_cwd  = os.getcwd()
    old_argv = sys.argv[:]
    sys.argv = [str(infer_script)] + args
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(infer_dir))
    try:
        os.chdir(repo_root)
        runpy.run_path(str(infer_script), run_name="__main__")
    finally:
        os.chdir(old_cwd)
        sys.argv = old_argv
        sys.path.pop(0)
        sys.path.pop(0)

    # 5) find the generated .wav and rename
    wavs = sorted(out_dir.glob("*.wav"))
    if not wavs:
        raise FileNotFoundError("No .wav generated")
    final = out_dir/"audio.wav"
    wavs[-1].rename(final)
    return str(final)