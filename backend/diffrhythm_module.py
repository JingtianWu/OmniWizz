import re, time, platform, subprocess, sys, os
from pathlib import Path

def extract_prompt_and_lyrics(output, lang='en'):
    if lang == 'en':
        p_pat = r"\*\*Music Prompt:\*\*\s*(.*?)(?:\n{2,}|\*\*Lyrics:\*\*)"
        l_pat = r"\*\*Lyrics:\*\*\s*([\s\S]+)"
    else:
        p_pat = r"\*\*音乐风格：\*\*\s*(.*?)(?:\n{2,}|\*\*歌词：\*\*)"
        l_pat = r"\*\*歌词：\*\*\s*([\s\S]+)"
    p_matches = list(re.finditer(p_pat, output))
    l_matches = list(re.finditer(l_pat, output))
    prompt = p_matches[-1].group(1).strip() if p_matches else ""
    lyrics = l_matches[-1].group(1).strip() if l_matches else ""
    return prompt, lyrics

def normalize_lrc(raw_lyrics):
    pattern = re.compile(r"(\[\d{2}:\d{2}\.\d{2}\])")
    parts = pattern.split(raw_lyrics)
    lines = []
    for i in range(1, len(parts), 2):
        timestamp = parts[i]
        text = parts[i+1].strip() if (i+1) < len(parts) else ""
        if text:
            lines.append(f"{timestamp}{text}")
    return "\n".join(lines)

def run_inference(assistant_reply):
    script_dir = Path(__file__).parent.resolve()
    project_root = script_dir.parent
    repo_root  = project_root / 'DiffRhythm'
    out_dir    = project_root / 'output'
    out_dir.mkdir(exist_ok=True)

    prompt, lyrics = extract_prompt_and_lyrics(assistant_reply)
    lyrics = normalize_lrc(lyrics)
    ts = time.strftime("%Y%m%d_%H%M%S")
    lrc_path = out_dir / f"{ts}.lrc"
    lrc_path.write_text(lyrics, encoding='utf-8')

    os.environ['CUDA_VISIBLE_DEVICES'] = '0'
    if platform.system() == 'Darwin':
        os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = (
            '/opt/homebrew/Cellar/espeak-ng/1.52.0/lib/libespeak-ng.dylib'
        )

    cmd = [
        sys.executable, 'infer/infer.py',
        '--lrc-path', str(lrc_path),
        '--ref-prompt', prompt,
        '--audio-length', '95',
        '--repo-id', 'ASLP-lab/DiffRhythm-1_2',
        '--output-dir', str(out_dir),
        '--chunked',
        '--batch-infer-num', '5'
    ]
    subprocess.run(cmd, check=True, cwd=repo_root)

    # find the most recent .wav
    wavs = sorted(out_dir.glob("*.wav"))
    if not wavs:
        raise FileNotFoundError("No .wav generated")
    return str(wavs[-1])