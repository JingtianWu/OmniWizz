import shutil
from pathlib import Path

from fastapi import FastAPI, UploadFile, Request, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from sqlmodel import Session as DBSession, SQLModel
import time
from uuid import uuid4

from log_db import (
    create_db_and_tables,
    get_session,
    log_event,
    SessionEntry,
    engine as DB_ENGINE,
)

from pipeline import (
    _make_run_dir,
    generate_music_from_image,
    generate_tags_from_image,
    generate_images_from_image,
)
from udio_module import run_inference

import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://jingtianwu.github.io"],  # or ["*"] for testing
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)


class SessionIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        sid = request.headers.get("x-omni-session")
        if not sid:
            sid = uuid4().hex
        request.state.session_id = sid

        with DBSession(DB_ENGINE) as db:
            sess = db.get(SessionEntry, sid)
            if not sess:
                sess = SessionEntry(
                    id=sid,
                    user_agent=request.headers.get("user-agent", ""),
                    locale=request.headers.get("accept-language"),
                )
                db.add(sess)
            sess.ended_at = None
            db.commit()

        response = await call_next(request)
        response.headers["x-omni-session"] = sid
        return response


app.add_middleware(SessionIDMiddleware)
create_db_and_tables()

@app.api_route("/", methods=["GET", "HEAD"], include_in_schema=False)
def root(request: Request):
    return {"status": "OmniWizz API is live"}

UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR = Path(__file__).parent.parent / "output"


@app.post("/generate")
async def generate(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    audio: UploadFile | None = File(None),
    language: str = "en",
    modes: str = "music,tags,images",  # default all three
    db: DBSession = Depends(get_session),
):
    start_t = time.monotonic()
    # 1) Write upload to disk
    img_path = UPLOAD_DIR / file.filename
    with open(img_path, "wb") as out:
        shutil.copyfileobj(file.file, out)

    audio_path = None
    if audio is not None:
        audio_path = UPLOAD_DIR / audio.filename
        with open(audio_path, "wb") as out:
            shutil.copyfileobj(audio.file, out)

    # 2) Create single run folder
    run_dir = _make_run_dir()
    results = {}

    modes_set = set(modes.lower().split(","))

    try:
        # 3a) Tags first
        if "tags" in modes_set:
            tags, _ = generate_tags_from_image(str(img_path), language, run_dir)
            folder = run_dir.name
            results["tags"] = {
                "folder": folder,
                "tags": tags,
                "tags_url": f"/output/{folder}/tags.json",
            }

        # 3b) Images next
        if "images" in modes_set:
            entities, _, image_paths = generate_images_from_image(
                str(img_path), language, run_dir=run_dir
            )
            folder = run_dir.name
            image_urls = [
                f"/output/{folder}/images/{Path(p).name}" for p in image_paths
            ]
            results["images"] = {
                "folder": folder,
                "entities": [str(e) for e in entities],
                "images": image_urls,
            }

        # 3c) Music last (async)
        if "music" in modes_set:
            folder = run_dir.name
            background_tasks.add_task(
                generate_music_from_image,
                str(img_path),
                language,
                run_dir,
                str(audio_path) if audio_path else None,
            )
            results["music"] = {
                "folder": folder,
                "audio_url": f"/output/{folder}/audio.wav",
                "lyrics_url": f"/output/{folder}/lyrics.lrc",
                "prompt_url": f"/output/{folder}/prompt.txt",
                "pending": True,
            }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    latency = time.monotonic() - start_t
    log_event(
        db,
        request.state.session_id,
        "generate",
        modes=modes,
        folder=run_dir.name,
        latency=latency,
    )

    return results


@app.post("/regenerate")
async def regenerate(
    background_tasks: BackgroundTasks,
    request: Request,
    folder: str = Form(...),
    prompt: str = Form(...),
    lyrics: str = Form(...),
    db: DBSession = Depends(get_session),
):
    out_dir = OUTPUT_DIR / folder
    if not out_dir.exists():
        raise HTTPException(404, "Folder not found")

    (out_dir / "prompt.txt").write_text(prompt, encoding="utf-8")

    # Remove old audio & lyrics so frontend polls until new files exist
    audio_fp = out_dir / "audio.wav"
    lrc_fp = out_dir / "lyrics.lrc"
    if audio_fp.exists():
        audio_fp.unlink()
    if lrc_fp.exists():
        lrc_fp.unlink()
    
    assistant_reply = f"**Music Prompt:** {prompt}\n\n**Lyrics:**\n{lyrics}"
    background_tasks.add_task(run_inference, assistant_reply, out_dir)

    log_event(
        db,
        request.state.session_id,
        "regenerate",
        folder=folder,
        prompt_len=len(prompt),
        lyrics_len=len(lyrics),
    )
    return {
        "audio_url": f"/output/{folder}/audio.wav",
        "pending": True,
    }


@app.get("/output/{folder}/{subpath:path}")
async def fetch(folder: str, subpath: str, request: Request, db: DBSession = Depends(get_session)):
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

    asset_type = "other"
    sp_lower = subpath.lower()
    if sp_lower == "tags.json":
        asset_type = "tags"
    elif sp_lower.startswith("images/"):
        asset_type = "image"
    elif sp_lower.endswith("prompt.txt"):
        asset_type = "prompt"
    elif sp_lower.endswith("lyrics.lrc"):
        asset_type = "lyrics"
    elif sp_lower.endswith(".wav"):
        asset_type = "audio"

    log_event(
        db,
        request.state.session_id,
        "fetch_output",
        path=f"{folder}/{subpath}",
        asset_type=asset_type,
    )
    return FileResponse(str(fp), media_type=media_type)


class ClientEvent(SQLModel):
    type: str
    payload: dict | None = None


@app.post("/log/batch")
async def log_batch(events: list[ClientEvent], request: Request, db: DBSession = Depends(get_session)):
    sid = request.state.session_id
    for ev in events:
        payload = ev.payload or {}
        log_event(db, sid, ev.type, **payload)
    return {"status": "ok"}
