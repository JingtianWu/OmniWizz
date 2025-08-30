from pathlib import Path
from musicgpt_module import run_inference as run_musicgpt
from udio_module import run_inference as run_udio


def generate_audio(assistant_reply: str, out_dir: Path) -> str:
    """Generate audio using MusicGPT with fallbacks to Udio and mock output."""
    try:
        return run_musicgpt(assistant_reply, out_dir)
    except Exception as e:
        print(f"MusicGPT failed: {e}; falling back to Udio")
        try:
            return run_udio(assistant_reply, out_dir)
        except Exception as e2:
            print(f"Udio failed: {e2}; using mock audio")
            return run_udio(assistant_reply, out_dir, use_mock=True)
