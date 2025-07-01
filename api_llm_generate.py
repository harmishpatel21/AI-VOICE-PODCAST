import pathlib
import json
import random
from fastapi import APIRouter, Body
from pydantic import BaseModel
import requests
import logging
import time
import re

router = APIRouter()

OLLAMA_URL = "http://localhost:11434/api/generate"

class PodcastScriptRequest(BaseModel):
    char1: str
    char2: str
    topic: str
    length_minutes: int = 10
    model: str = "mistral"
    sample_lines: int = 3

logger = logging.getLogger("llm_generate_api")

def sanitize_filename(filename):
    # Remove or replace invalid characters for a file name
    return "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in filename).strip()

@router.post("/api/generate_podcast_script")
def generate_podcast_script(req: PodcastScriptRequest):
    logger.info(f"Received request: char1={req.char1}, char2={req.char2}, topic={req.topic}, model={req.model}, length={req.length_minutes}")
    # Load transcript samples for each character
    def get_samples(youtuber, n):
        transcript_dir = pathlib.Path("transcripts") / youtuber
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
    prompt = f"""
You are an expert podcast scriptwriter. Write a realistic, engaging, and natural-sounding podcast conversation between two hosts:

- {req.char1}: Here are some example lines in their style: {char1_samples}
- {req.char2}: Here are some example lines in their style: {char2_samples}

The topic of the podcast is: \"{req.topic}\".

Alternate their dialogue naturally, making sure each host's personality and style comes through. The conversation should be about {req.length_minutes} minutes long (roughly 1500-2000 words). Use humor, depth, and storytelling as appropriate. Start with a brief introduction, then dive into the topic, and end with a natural outro.

**Important:** For each line of dialogue, add a short expression or action in square brackets that describes how the host is speaking, reacting, or gesturing (e.g., [laughs], [smiling], [thoughtful pause], [raises eyebrow], [enthusiastic], [shrugs], etc.). These expressions should help bring the conversation to life and can be placed before or after the spoken line.

Format:
{req.char1}: [expression] ...
{req.char2}: [expression] ...
(repeat)

Write the entire script in {script_language}. If {script_language} is Hinglish, use Latin script for all Hindi words and mix with English naturally, as in real Hinglish conversations. Do not use Devanagari script."
"""

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
            save_dir = pathlib.Path("saved_scripts") / sanitize_filename(req.topic)
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
