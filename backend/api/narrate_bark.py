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
import numpy as np
from config import settings

router = APIRouter()

logger = logging.getLogger("narrate_script_bark_api")

class NarrateScriptBarkRequest(BaseModel):
    topic: str
    script: str
    char1: str
    char2: str
    output_format: str = "wav"

def speedup_audio(audio_segment, speed=1.2):
    # Use pydub to speed up audio without changing pitch too much
    return audio_segment._spawn(audio_segment.raw_data, overrides={
        "frame_rate": int(audio_segment.frame_rate * speed)
    }).set_frame_rate(audio_segment.frame_rate)

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
        # text_clean = re.sub(r"\[[^\]]*\]", "", text).strip()
        text_clean = text.strip()
        logger.info(f"Synthesizing line for {speaker}: {text_clean[:40]}...")
        # Use a Bark preset for better voice quality
        char_presets = {
            req.char1: "v2/en_speaker_6",  # Preset for char1
            req.char2: "v2/en_speaker_3"   # Preset for char2
        }
        bark_preset = char_presets.get(speaker, "v2/en_speaker_6")
        try:
            # Ensure Bark uses GPU if available
            if torch.cuda.is_available():
                torch_device = torch.device("cuda")
                logger.info("Using GPU for Bark TTS: %s", torch.cuda.get_device_name(0))
            else:
                torch_device = torch.device("cpu")
                logger.info("Using CPU for Bark TTS")
            # Bark uses the default device, but you can set it globally if needed
            audio_array = generate_audio(text_clean, history_prompt=bark_preset)
            audio_int16 = (audio_array * 32767).astype(np.int16)  # Convert to int16 for WAV export
            if hasattr(audio_array, 'to'):
                audio_array = audio_array.to(torch_device)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tf:
                seg = AudioSegment(
                    audio_int16.tobytes(),
                    frame_rate=SAMPLE_RATE,
                    sample_width=2,
                    channels=1
                )
                seg_fast = speedup_audio(seg, speed=1.2)
                seg_fast.export(tf.name, format="wav")
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
        def sanitize_filename(filename):
            return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in filename).strip()
        topic_safe = sanitize_filename(str(req.topic))
        topic_dir = pathlib.Path(settings.NARRATED_PODCASTS_BARK_DIR) / topic_safe
        topic_dir.mkdir(parents=True, exist_ok=True)
        import time
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f"{sanitize_filename(req.char1)}_{sanitize_filename(req.char2)}_{timestamp}.{req.output_format}"
        output_path = topic_dir / filename
        combined.export(output_path, format=req.output_format)
        for seg in segments:
            os.remove(seg)
        logger.info(f"Bark narrated podcast saved to {output_path}")
        return {"audio_path": str(output_path)}
    except Exception as e:
        logger.error(f"Exception during Bark audio stitching/export: {e}")
        return {"error": f"Exception during Bark audio stitching/export: {e}"}
