import uuid
import json
from datetime import datetime
from pathlib import Path
import shutil
from llm_processors import _to_data_url
from config import TEST_MODE
from musicai_module import transcribe_chords

from llm_processors import (
    ImageToLyricsProcessor,
    ImageToTagsProcessor,
    ImageToVisualEntitiesProcessor,
)
from ace_step_module import run_inference
from nano_banana_module import generate_images_for_entity

OUTPUT_ROOT = Path(__file__).parent.parent / "output"


def _make_run_dir() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:6]
    d = OUTPUT_ROOT / f"{stamp}_{uid}"
    d.mkdir(parents=True, exist_ok=False)
    return d


def prepare_music_from_image(
    image_path: str,
    language: str = "en",
    run_dir: Path | None = None,
    audio_path: str | None = None,
) -> tuple[str, Path, str | None]:
    """Return (assistant_reply, out_dir, style_audio_path).

    This performs all preprocessing steps (chord transcription, LLM prompt
    creation, etc.) but does not invoke the music inference API.  It ensures a
    valid assistant reply is produced even if intermediate steps fail."""

    out_dir = run_dir or _make_run_dir()
    shutil.copy2(image_path, out_dir / Path(image_path).name)

    chords = None
    if audio_path:
        try:
            chords = transcribe_chords(audio_path)
            with open(out_dir / "chords.json", "w", encoding="utf-8") as f:
                json.dump(chords, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Chord transcription failed: {e}")

    uri = _to_data_url(image_path)
    try:
        proc = ImageToLyricsProcessor(uri, language, chords)
    except Exception as e:
        print(f"Processor init failed: {e}; using mock processor")
        proc = ImageToLyricsProcessor(uri, language, chords=None)

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

    with open(out_dir / "prompt.txt", "w", encoding="utf-8") as f:
        f.write(prompt)

    assistant_reply = f"**Music Prompt:** {prompt}\n\n**Lyrics:**\n{lyrics}"
    return assistant_reply, out_dir, audio_path


def generate_music_from_image(
    image_path: str,
    language: str = "en",
    run_dir: Path | None = None,
    audio_path: str | None = None,
) -> str:
    assistant_reply, out_dir, style_audio = prepare_music_from_image(
        image_path, language, run_dir, audio_path
    )
    try:
        audio_path = run_inference(
            assistant_reply,
            out_dir,
            style_audio_path=str(style_audio) if style_audio else None,
        )
    except Exception as e:
        print(f"Ace Step failed: {e}; using mock audio")
        audio_path = run_inference(
            assistant_reply,
            out_dir,
            style_audio_path=str(style_audio) if style_audio else None,
            use_mock=True,
        )
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

    # 3) REAL: generate images for all entities concurrently
    from concurrent.futures import ThreadPoolExecutor, as_completed

    all_paths: list[str] = []
    if entities:
        max_workers = min(len(entities), 6)  # cap concurrency
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {
                ex.submit(generate_images_for_entity, ent, per_entity, image_dir): ent
                for ent in entities
            }
            for fut in as_completed(futures):
                ent = futures[fut]
                try:
                    imgs = fut.result() or []
                    all_paths.extend(imgs)
                    if not imgs:
                        print(f"Image generation returned no images for {ent}")
                except Exception as e:
                    print(f"Image generation failed for {ent}: {e}")

    if not all_paths:
        print("No images generated; using mock images")
        mock_dir = Path(__file__).parent / "mock_data" / "images"
        for img_path in mock_dir.glob("*.*"):
            shutil.copy(img_path, image_dir)
        all_paths = [str(p) for p in image_dir.glob("*.*")]

    return entities, out_dir, all_paths
