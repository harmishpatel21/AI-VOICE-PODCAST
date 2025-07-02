import pathlib
from fastapi import APIRouter
from typing import List, Dict
from config import settings

router = APIRouter()

@router.get("/api/list_youtubers", response_model=List[str])
def list_youtubers():
    transcripts_dir = pathlib.Path(settings.TRANSCRIPTS_DIR)
    if not transcripts_dir.exists():
        return []
    return [d.name for d in transcripts_dir.iterdir() if d.is_dir()]

@router.get("/api/list_transcripts", response_model=Dict[str, List[str]])
def list_transcripts(youtuber: str):
    transcripts_dir = pathlib.Path(settings.TRANSCRIPTS_DIR) / youtuber
    if not transcripts_dir.exists():
        return {youtuber: []}
    files = [f.name for f in transcripts_dir.glob("*.json")]
    return {youtuber: files}
