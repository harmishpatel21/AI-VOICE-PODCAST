from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import random
import re
import logging
import os
import json
import pathlib
from api_transcript_listing import router as transcript_listing_router
from api_llm_generate import router as llm_generate_router

app = FastAPI()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("backend_api.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("backend_api")

# Allow CORS for local Streamlit frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcript_listing_router)
app.include_router(llm_generate_router)

class TranscriptResponse(BaseModel):
    video_id: str
    video_url: str
    transcript: Optional[str]
    language: Optional[str]
    is_generated: Optional[bool] = None
    error: Optional[str] = None

def sanitize_filename(name):
    # Remove or replace characters not allowed in filenames
    return re.sub(r'[^\w\-_\. ]', '_', name)

@app.get("/api/channel_videos", response_model=List[str])
def get_channel_video_ids(youtuber: str = Query(...), num_videos: int = Query(3)):
    logger.info(f"Fetching channel videos for: {youtuber}, num_videos={num_videos}")
    ydl_opts = {'extract_flat': True, 'quiet': True, 'skip_download': True}
    channel_url = youtuber if youtuber.startswith('http') else f"https://www.youtube.com/{youtuber}/videos"
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(channel_url, download=False)
        entries = info.get('entries', [])
        # Only keep valid video IDs (length 11) and not shorts
        video_ids = [
            e['id'] for e in entries
            if 'id' in e and isinstance(e['id'], str) and len(e['id']) == 11
            and (
                ('url' in e and '/shorts/' not in str(e['url']))
                or ('url' not in e and '_type' in e and e['_type'] == 'url')  # fallback for some playlist entries
            )
        ]
    if not video_ids:
        logger.warning(f"No valid videos found for channel: {youtuber}")
        return []
    # Return the latest N videos (first N in the list)
    return video_ids[:num_videos]

@app.get("/api/transcript", response_model=TranscriptResponse)
def get_transcript(video_id: str = Query(...)):
    video_url = f"https://youtu.be/{video_id}"
    logger.info(f"Fetching transcript for video_id: {video_id}")
    # Try to load from local cache first
    transcript_dir = pathlib.Path("transcripts")
    transcript_dir.mkdir(exist_ok=True)
    meta_info = None
    # Try to get channel name and video title using yt-dlp
    try:
        with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
            info = ydl.extract_info(video_url, download=False)
            channel_name = sanitize_filename(info.get('channel', 'unknown_channel'))
            video_title = sanitize_filename(info.get('title', 'unknown_title'))
            meta_info = {
                "channel_name": channel_name,
                "video_title": video_title,
                "video_url": video_url,
                "video_id": video_id
            }
    except Exception as e:
        logger.warning(f"Could not fetch video/channel info for {video_id}: {e}")
        channel_name = 'unknown_channel'
        video_title = 'unknown_title'
        meta_info = {
            "channel_name": channel_name,
            "video_title": video_title,
            "video_url": video_url,
            "video_id": video_id
        }
    channel_dir = transcript_dir / meta_info["channel_name"]
    channel_dir.mkdir(exist_ok=True)
    transcript_path = channel_dir / f"{meta_info['video_title']}_{video_id}.json"
    if transcript_path.exists():
        logger.info(f"Transcript already exists locally: {transcript_path}")
        with open(transcript_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return TranscriptResponse(**data)
    try:
        # Try English first
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
            transcript_text = " ".join([t['text'] for t in transcript])
            logger.info(f"Fetched English transcript for {video_id}")
            data = {
                **meta_info,
                "transcript": transcript_text,
                "language": 'en',
                "is_generated": False,
                "error": None
            }
            with open(transcript_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            return TranscriptResponse(**data)
        except Exception as e_en:
            logger.warning(f"English transcript not found for {video_id}: {e_en}")
            # Try any available language
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                for t in transcript_list:
                    try:
                        transcript = t.fetch()
                        # FetchedTranscriptSnippet is a list of objects, not dicts, so use .text
                        if hasattr(transcript[0], 'text'):
                            transcript_text = " ".join([seg.text for seg in transcript])
                        else:
                            transcript_text = " ".join([seg['text'] for seg in transcript])
                        logger.info(f"Fetched transcript in language {t.language_code} for {video_id}")
                        data = {
                            **meta_info,
                            "transcript": transcript_text,
                            "language": t.language_code,
                            "is_generated": getattr(t, 'is_generated', False),
                            "error": None
                        }
                        with open(transcript_path, 'w', encoding='utf-8') as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        return TranscriptResponse(**data)
                    except Exception as e_any:
                        logger.warning(f"Failed to fetch transcript in {t.language_code} for {video_id}: {e_any}")
                logger.error(f"No transcript available for {video_id} in any language.")
                data = {
                    **meta_info,
                    "transcript": None,
                    "language": None,
                    "is_generated": None,
                    "error": "No transcript available in any language."
                }
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return TranscriptResponse(**data)
            except Exception as e_list:
                logger.error(f"Transcript not available for {video_id}: {e_list}")
                data = {
                    **meta_info,
                    "transcript": None,
                    "language": None,
                    "is_generated": None,
                    "error": str(e_list)
                }
                with open(transcript_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                return TranscriptResponse(**data)
    except Exception as e:
        logger.error(f"Transcript not available for {video_id}: {e}")
        data = {
            **meta_info,
            "transcript": None,
            "language": None,
            "is_generated": None,
            "error": str(e)
        }
        with open(transcript_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return TranscriptResponse(**data)

@app.get("/api/transcript_from_url", response_model=TranscriptResponse)
def get_transcript_from_url(video_url: str = Query(...)):
    logger.info(f"Fetching transcript from URL: {video_url}")
    match = re.search(r"(?:v=|youtu.be/)([\w-]{11})", video_url)
    if not match:
        logger.error(f"Invalid YouTube video URL: {video_url}")
        return TranscriptResponse(video_id="", video_url=video_url, transcript=None, language=None, error="Invalid YouTube video URL.")
    video_id = match.group(1)
    return get_transcript(video_id)
