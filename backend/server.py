import shutil
import traceback
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pathlib import Path
from pipeline import generate_from_image

app = FastAPI()

UPLOAD_DIR = Path(__file__).parent / "uploads"
OUTPUT_DIR = Path(__file__).parent.parent / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

@app.post("/generate")
async def generate(file: UploadFile = File(...), language: str = "en"):
    img_path = UPLOAD_DIR / file.filename
    with open(img_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        audio_path = generate_from_image(str(img_path), language)
    except Exception as e:
        # Print full error details in the terminal
        traceback.print_exc()
        raise HTTPException(500, str(e))

    return {"audio_url": f"/output/{Path(audio_path).name}"}

@app.get("/output/{filename}")
async def get_output(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(404, "Not found")
    return FileResponse(str(file_path), media_type="audio/wav")
