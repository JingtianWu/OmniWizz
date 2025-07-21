from pathlib import Path
import os
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(tags=["dev"])

DB_PATH = Path(__file__).parent / "omni_logs.db"
API_KEY = os.getenv("LOG_DOWNLOAD_KEY", "changeme")      # set this env var in Render

@router.get("/dev/download-logs", response_class=FileResponse, include_in_schema=False)
def download_logs(key: str = Query(..., description="API key set in LOG_DOWNLOAD_KEY")):
    if key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid key")
    if not DB_PATH.exists():
        raise HTTPException(status_code=404, detail="Log DB not found")
    return FileResponse(
        DB_PATH,
        filename="omni_logs.db",
        media_type="application/x-sqlite3",
    )