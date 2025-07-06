import uuid
import json
from datetime import datetime
from pathlib import Path
import shutil
from llm_processors import _to_data_url
from config import TEST_MODE

from llm_processors import (
    ImageToLyricsProcessor,
    ImageToTagsProcessor,
    ImageToVisualEntitiesProcessor,
)
from diffrhythm_module import run_inference
from midjourney_module import generate_images

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
    uri = _to_data_url(image_path)
    proc = ImageToLyricsProcessor(uri, language)
    try:
        raw = proc.generate()
    except Exception as e:
        print(f"LLM generation failed: {e}; falling back to mock")
        raw = proc._mock_generate()

    print("\n=== LLM RAW OUTPUT ===\n", raw, "\n=== END ===")

    try:
        prompt, lyrics = proc._postprocess(raw)
        if not prompt.strip():
            raise ValueError("empty prompt")
    except Exception as e:
        print(f"Postprocessing failed: {e}; using mock output")
        raw = proc._mock_generate()
        prompt, lyrics = proc._postprocess(raw)

    # 3) Store prompt for later reference
    with open(out_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    # 4) Assemble assistant reply for DiffRhythm
    assistant_reply = f"**Music Prompt:** {prompt}\n\n**Lyrics:**\n{lyrics}"

    # 5) Inference (or mock)
    try:
        audio_path = run_inference(assistant_reply, out_dir)
    except Exception as e:
        print(f"DiffRhythm failed: {e}; using mock audio")
        audio_path = run_inference(assistant_reply, out_dir, use_mock=True)
    return audio_path


def generate_tags_from_image(
    image_path: str, language: str = "en", run_dir: Path = None
):
    out_dir = run_dir or _make_run_dir()
    shutil.copy2(image_path, out_dir / Path(image_path).name)

    uri = _to_data_url(image_path)
    proc = ImageToTagsProcessor(uri, language)
    try:
        tags = proc.process()
        if not tags:
            raise ValueError("no tags")
    except Exception as e:
        print(f"Tag generation failed: {e}; using mock tags")
        tags = proc._postprocess(proc._mock_generate())

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
    uri = _to_data_url(image_path)
    proc = ImageToVisualEntitiesProcessor(uri, language)
    try:
        entities = proc.process()
    except Exception as e:
        print(f"Entity extraction failed: {e}; continuing with empty list")
        entities = []

    # 2) MOCK: copy pre-made images
    if TEST_MODE:
        mock_dir = Path(__file__).parent / "mock_data" / "images"
        for img_path in mock_dir.glob("*.*"):
            shutil.copy(img_path, image_dir)
        all_paths = [str(p) for p in image_dir.glob("*.*")]
        return entities, out_dir, all_paths

    # 3) REAL: generate images via Midjourney per entity
    all_paths = []
    for ent in entities:
        try:
            imgs = generate_images(ent, out_dir=image_dir)
            if imgs:
                if per_entity and len(imgs) > per_entity:
                    imgs = imgs[:per_entity]
                all_paths.extend(imgs)
        except Exception as e:
            print(f"Image generation failed for {ent}: {e}")

    if not all_paths:
        print("No images fetched; using mock images")
        mock_dir = Path(__file__).parent / "mock_data" / "images"
        for img_path in mock_dir.glob("*.*"):
            shutil.copy(img_path, image_dir)
        all_paths = [str(p) for p in image_dir.glob("*.*")]

    return entities, out_dir, all_paths