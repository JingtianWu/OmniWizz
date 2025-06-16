import uuid
import json
from datetime import datetime
from pathlib import Path
import shutil
from config import TEST_MODE

from llm_processors import (
    ImageToLyricsProcessor,
    ImageToTagsProcessor,
    ImageToVisualEntitiesProcessor,
)
from diffrhythm_module import run_inference
from serpapi_module import fetch_images_for_entity

OUTPUT_ROOT = Path(__file__).parent.parent / "output"


def _make_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    d = OUTPUT_ROOT / f"{stamp}_{uid}"
    d.mkdir(parents=True, exist_ok=False)
    return d


def generate_music_from_image(
    image_path: str, language: str = "en", run_dir: Path = None
) -> str:
    # 1) Prepare run_dir
    out_dir = run_dir or _make_run_dir()
    shutil.copy2(image_path, out_dir / Path(image_path).name)

    # 2) LLM → prompt + lyrics
    uri = f"file://{image_path}"
    proc = ImageToLyricsProcessor(uri, language)
    raw = proc.generate()
    print("\n=== LLM RAW OUTPUT ===\n", raw, "\n=== END ===")

    prompt, lyrics = proc._postprocess(raw)
    if not prompt.strip():
        raise RuntimeError("LLM did not emit a music prompt")

    # 3) Store prompt for later reference
    with open(out_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    # 4) Assemble assistant reply for DiffRhythm
    assistant_reply = f"**Music Prompt:** {prompt}\n\n**Lyrics:**\n{lyrics}"

    # 5) Inference (or mock)
    audio_path = run_inference(assistant_reply, out_dir)
    return audio_path


def generate_tags_from_image(
    image_path: str, language: str = "en", run_dir: Path = None
):
    out_dir = run_dir or _make_run_dir()
    shutil.copy2(image_path, out_dir / Path(image_path).name)

    uri = f"file://{image_path}"
    proc = ImageToTagsProcessor(uri, language)
    tags = proc.process()

    # save tags.json
    with open(out_dir / "tags.json", "w", encoding="utf-8") as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

    return tags, out_dir


def generate_images_from_image(
    image_path: str, language: str = "en", per_entity: int = 1, run_dir: Path = None
):
    out_dir = run_dir or _make_run_dir()
    shutil.copy2(image_path, out_dir / Path(image_path).name)

    # subfolder for images
    image_dir = out_dir / "images"
    image_dir.mkdir(exist_ok=True)

    # 1) LLM → entities
    uri = f"file://{image_path}"
    proc = ImageToVisualEntitiesProcessor(uri, language)
    entities = proc.process()

    # 2) MOCK: copy pre-made images
    if TEST_MODE:
        mock_dir = Path(__file__).parent / "mock_data" / "images"
        for img_path in mock_dir.glob("*.*"):
            shutil.copy(img_path, image_dir)
        all_paths = [str(p) for p in image_dir.glob("*.*")]
        return entities, out_dir, all_paths

    # 3) REAL: fetch per entity
    all_paths = []
    for ent in entities:
        imgs = fetch_images_for_entity(ent, num=per_entity, out_dir=image_dir)
        all_paths.extend(imgs)

    return entities, out_dir, all_paths