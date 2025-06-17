import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse

from pipeline import (
    _make_run_dir,
    generate_music_from_image,
    generate_tags_from_image,
    generate_images_from_image,
)

app = FastAPI()

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path(__file__).parent.parent / "output"


@app.post("/generate")
async def generate(
    file: UploadFile = File(...),
    language: str = "en",
    modes: str = "music,tags,images",  # default all three
):
    # 1) Write upload to disk
    img_path = UPLOAD_DIR / file.filename
    with open(img_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    # 2) Create single run folder
    run_dir = _make_run_dir()
    results = {}

    try:
        # 3a) Music
        if "music" in modes.lower().split(","):
            audio_path = generate_music_from_image(str(img_path), language, run_dir)
            folder = run_dir.name
            results["music"] = {
                "folder": folder,
                "audio_url": f"/output/{folder}/audio.wav",
                "lyrics_url": f"/output/{folder}/lyrics.lrc",
                "prompt_url": f"/output/{folder}/prompt.txt",
            }

        # 3b) Tags
        if "tags" in modes.lower().split(","):
            tags, _ = generate_tags_from_image(str(img_path), language, run_dir)
            folder = run_dir.name
            results["tags"] = {
                "folder": folder,
                "tags": tags,
                "tags_url": f"/output/{folder}/tags.json",
            }

        # 3c) Images
        if "images" in modes.lower().split(","):
            entities, _, image_paths = generate_images_from_image(
                str(img_path), language, run_dir=run_dir
            )
            folder = run_dir.name
            # convert local image paths to frontend-accessible URLs
            image_urls = [
                f"/output/{folder}/images/{Path(p).name}" for p in image_paths
            ]
            results["images"] = {
                "folder": folder,
                "entities": [str(e) for e in entities],
                "images": image_urls,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return results


@app.get("/output/{folder}/{subpath:path}")
async def fetch(folder: str, subpath: str):
    fp = OUTPUT_DIR / folder / subpath
    if not fp.exists():
        raise HTTPException(404, "Not found")

    ext = subpath.lower().rsplit(".", 1)[-1]
    if ext == "wav":
        media_type = "audio/wav"
    elif ext in {"png", "jpg", "jpeg", "gif"}:
        media_type = f"image/{ext if ext != 'jpg' else 'jpeg'}"
    elif ext == "txt":
        media_type = "text/plain"
    else:
        media_type = "application/octet-stream"

    return FileResponse(str(fp), media_type=media_type)