import pathlib
import json
import random
from fastapi import APIRouter, Body
from pydantic import BaseModel
import requests
import logging
import time
import re
from config import settings
from backend.core.prompt_utility import get_podcast_script_prompt

router = APIRouter()

OLLAMA_URL = settings.OLLAMA_URL

class PodcastScriptRequest(BaseModel):
    char1: str
    char2: str
    topic: str
    length_minutes: int = 10
    model: str = "gemma3:4b"
    sample_lines: int = 3

logger = logging.getLogger("llm_generate_api")

def sanitize_filename(filename):
    # Remove or replace invalid characters for a file name
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in filename).strip()

@router.post("/api/generate_podcast_script")
def generate_podcast_script(req: PodcastScriptRequest):
    # Force model to gemma3:4b regardless of what client sends
    req.model = "gemma3:4b"
    logger.info(f"Received request: char1={req.char1}, char2={req.char2}, topic={req.topic}, model={req.model}, length={req.length_minutes}")
    # Load transcript samples for each character
    def get_samples(youtuber, n):
        transcript_dir = pathlib.Path(settings.TRANSCRIPTS_DIR) / youtuber
        all_files = list(transcript_dir.glob("*.json"))
        if not all_files:
            logger.warning(f"No transcripts found for youtuber: {youtuber}")
            return []
        random.shuffle(all_files)
        lines = []
        for f in all_files:
            with open(f, encoding="utf-8") as jf:
                data = json.load(jf)
                if data.get("transcript"):
                    # Split transcript into lines (simple split by period)
                    split_lines = [l.strip() for l in data["transcript"].split(".") if l.strip()]
                    lines.extend(split_lines)
            if len(lines) >= n:
                break
        logger.info(f"Sampled {min(n, len(lines))} lines for {youtuber}")
        return random.sample(lines, min(n, len(lines)))

    char1_samples = get_samples(req.char1, req.sample_lines)
    char2_samples = get_samples(req.char2, req.sample_lines)

    # Detect if either speaker's sample lines are in Hindi (Devanagari script)
    def contains_devanagari(text):
        return bool(re.search(r'[\u0900-\u097F]', text))

    char1_is_hindi = any(contains_devanagari(line) for line in char1_samples)
    char2_is_hindi = any(contains_devanagari(line) for line in char2_samples)
    script_language = "Hinglish" if char1_is_hindi or char2_is_hindi else "English"

    # Build prompt
    prompt = get_podcast_script_prompt(req.char1, req.char2, char1_samples, char2_samples, req.topic, req.length_minutes, script_language)

    logger.info(f"Prompt constructed for LLM call. Model: {req.model}")
    try:
        # Call Ollama
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": req.model,
                "prompt": prompt,
                "stream": False
            },
            timeout=600  # Allow up to 10 minutes for LLM response
        )
        logger.info(f"Ollama API response status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            script = result.get("response", "")
            logger.info(f"LLM script generation successful for topic '{req.topic}'")
            # Save the script
            save_dir = pathlib.Path(settings.SAVED_SCRIPTS_DIR) / sanitize_filename(req.topic)
            save_dir.mkdir(parents=True, exist_ok=True)
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"{sanitize_filename(req.char1)}_{sanitize_filename(req.char2)}_{req.length_minutes}min_{timestamp}.json"
            save_path = save_dir / filename
            save_data = {
                "char1": req.char1,
                "char2": req.char2,
                "topic": req.topic,
                "length_minutes": req.length_minutes,
                "timestamp": timestamp,
                "script": script,
                "prompt": prompt
            }
            with open(save_path, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved generated script to {save_path}")
            return {"script": script, "prompt": prompt, "save_path": str(save_path)}
        else:
            logger.error(f"Ollama API error: {response.text}")
            return {"error": f"Ollama API error: {response.text}"}
    except Exception as e:
        logger.error(f"Exception during LLM call: {e}")
        return {"error": str(e)}
