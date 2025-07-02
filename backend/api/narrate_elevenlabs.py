import os
import pathlib
import json
import requests
from fastapi import APIRouter, Body
from pydantic import BaseModel
from dotenv import load_dotenv
from pydub import AudioSegment
import tempfile
import logging
import re
from config import settings

router = APIRouter()

# Load ElevenLabs API key and voice ID from .env
# These are now loaded via config/settings.py
ELEVENLABS_API_KEY = settings.ELEVENLABS_API_KEY
ELEVENLABS_VOICE_ID1 = settings.ELEVENLABS_VOICE_ID1
ELEVENLABS_VOICE_ID2 = settings.ELEVENLABS_VOICE_ID2

logger = logging.getLogger("narrate_script_api")

class NarrateScriptRequest(BaseModel):
    script: str
    char1: str
    char2: str
    voice1: str = ELEVENLABS_VOICE_ID1  # default to env voice
    voice2: str = ELEVENLABS_VOICE_ID2  # can be changed per character
    output_format: str = "mp3"

@router.post("/api/narrate_script")
def narrate_script(req: NarrateScriptRequest):
    logger.info(f"Narrate request: char1={req.char1}, char2={req.char2}, voice1={req.voice1}, voice2={req.voice2}, output_format={req.output_format}")
    if not ELEVENLABS_API_KEY:
        logger.error("ElevenLabs API key not set in .env")
        return {"error": "ElevenLabs API key not set in .env"}
    # Split script into lines by speaker
    lines = [l.strip() for l in req.script.split("\n") if l.strip()]
    segments = []
    for idx, line in enumerate(lines):
        logger.info(f"Processing line {idx}: {line[:60]}")
        if line.startswith(f"{req.char1}:"):
            speaker = req.char1
            voice_id = req.voice1
            text = line[len(f"{req.char1}:"):].strip()
        elif line.startswith(f"{req.char2}:"):
            speaker = req.char2
            voice_id = req.voice2
            text = line[len(f"{req.char2}:"):].strip()
        else:
            logger.warning(f"Skipping line {idx}: does not match any speaker")
            continue
        if not text:
            logger.warning(f"Skipping line {idx}: empty text after speaker")
            continue
        logger.info(f"Synthesizing line for {speaker}: {text[:40]}...")
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": ELEVENLABS_API_KEY}
        # Remove expressions in square brackets from text
        text_clean = re.sub(r"\[[^\]]*\]", "", text).strip()
        payload = {
            "text": text_clean,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
        try:
            resp = requests.post(tts_url, headers=headers, json=payload)
            logger.info(f"TTS API status for line {idx}: {resp.status_code}")
            if resp.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{req.output_format}") as tf:
                    tf.write(resp.content)
                    tf.flush()
                    segments.append(tf.name)
            else:
                logger.error(f"Failed to synthesize line {idx}: {resp.text}")
                return {"error": f"Failed to synthesize line: {resp.text}"}
        except Exception as e:
            logger.error(f"Exception during TTS for line {idx}: {e}")
            return {"error": f"Exception during TTS: {e}"}
    # Stitch audio segments
    if not segments:
        logger.error("No audio segments generated.")
        return {"error": "No audio segments generated."}
    try:
        combined = AudioSegment.empty()
        for seg in segments:
            audio = AudioSegment.from_file(seg)
            combined += audio + AudioSegment.silent(duration=400)  # 0.4s pause
        # --- Updated audio saving structure ---
        # Save audio in narrated_podcasts/{topic}/ with filename matching saved_scripts
        def sanitize_filename(filename):
            return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in filename).strip()
        # Try to extract topic, char1, char2, length_minutes, timestamp from request or script
        topic = getattr(req, 'topic', None)
        length_minutes = getattr(req, 'length_minutes', None)
        timestamp = None
        # If topic is provided directly in the request, use it
        if not topic and hasattr(req, 'topic'):
            topic = req.topic
        # Try to parse from script if not present
        try:
            script_json = json.loads(req.script)
            topic = script_json.get('topic', topic)
            length_minutes = script_json.get('length_minutes', length_minutes)
            timestamp = script_json.get('timestamp', None)
        except Exception:
            pass
        # If not found, fallback to defaults
        if not topic:
            topic = "Unknown_Topic"
        if not length_minutes:
            length_minutes = 10
        if not timestamp:
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
        topic_dir = pathlib.Path(settings.NARRATED_PODCASTS_DIR) / sanitize_filename(str(topic))
        topic_dir.mkdir(parents=True, exist_ok=True)
        # Add topic to filename as well
        filename = f"{sanitize_filename(str(topic))}_{sanitize_filename(req.char1)}_{sanitize_filename(req.char2)}_{length_minutes}min_{timestamp}.{req.output_format}"
        output_path = topic_dir / filename
        combined.export(output_path, format=req.output_format)
        # Clean up temp files
        for seg in segments:
            os.remove(seg)
        logger.info(f"Narrated podcast saved to {output_path}")
        return {"audio_path": str(output_path)}
    except Exception as e:
        logger.error(f"Exception during audio stitching/export: {e}")
        return {"error": f"Exception during audio stitching/export: {e}"}
