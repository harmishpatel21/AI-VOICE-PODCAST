import os
import pathlib
import json
from fastapi import APIRouter
from pydantic import BaseModel
from pydub import AudioSegment
import tempfile
import logging
import torch
from bark import SAMPLE_RATE, generate_audio

router = APIRouter()

logger = logging.getLogger("narrate_script_bark_api")

class NarrateScriptBarkRequest(BaseModel):
    topic: str
    script: str
    char1: str
    char2: str
    output_format: str = "wav"

@router.post("/api/narrate_script_bark")
def narrate_script_bark(req: NarrateScriptBarkRequest):
    logger.info(f"Bark Narrate request: char1={req.char1}, char2={req.char2}, output_format={req.output_format}")
    # Split script into lines by speaker
    lines = [l.strip() for l in req.script.split("\n") if l.strip()]
    segments = []
    for idx, line in enumerate(lines):
        logger.info(f"Processing line {idx}: {line[:60]}")
        if line.startswith(f"{req.char1}:"):
            speaker = req.char1
        elif line.startswith(f"{req.char2}:"):
            speaker = req.char2
        else:
            logger.warning(f"Skipping line {idx}: does not match any speaker")
            continue
        text = line.split(":", 1)[1].strip()
        if not text:
            logger.warning(f"Skipping line {idx}: empty text after speaker")
            continue
        # Remove expressions in square brackets
        import re
        text_clean = re.sub(r"\[[^\]]*\]", "", text).strip()
        logger.info(f"Synthesizing line for {speaker}: {text_clean[:40]}...")
        try:
            audio_array = generate_audio(text_clean)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
                AudioSegment(
                    audio_array.tobytes(),
                    frame_rate=SAMPLE_RATE,
                    sample_width=2,
                    channels=1
                ).export(tf.name, format="wav")
                segments.append(tf.name)
        except Exception as e:
            logger.error(f"Exception during Bark TTS for line {idx}: {e}")
            return {"error": f"Exception during Bark TTS: {e}"}
    # Stitch audio segments
    if not segments:
        logger.error("No audio segments generated.")
        return {"error": "No audio segments generated."}
    try:
        combined = AudioSegment.empty()
        for seg in segments:
            audio = AudioSegment.from_file(seg)
            combined += audio + AudioSegment.silent(duration=400)  # 0.4s pause
        # Save audio in narrated_podcasts_bark/{topic}/
        topic = getattr(req, 'topic', 'Unknown_Topic')
        topic_dir = pathlib.Path("narrated_podcasts_bark") / topic
        topic_dir.mkdir(parents=True, exist_ok=True)
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{req.char1}_{req.char2}_{timestamp}.{req.output_format}"
        output_path = topic_dir / filename
        combined.export(output_path, format=req.output_format)
        for seg in segments:
            os.remove(seg)
        logger.info(f"Bark narrated podcast saved to {output_path}")
        return {"audio_path": str(output_path)}
    except Exception as e:
        logger.error(f"Exception during Bark audio stitching/export: {e}")
        return {"error": f"Exception during Bark audio stitching/export: {e}"}
