import os
import json
import pathlib
import logging
import requests
import time
from config import settings

def chunk_text(text, max_words=500):
    words = text.split()
    for i in range(0, len(words), max_words):
        yield ' '.join(words[i:i+max_words])

def contains_devanagari(text):
    import re
    return bool(re.search(r'[\u0900-\u097F]', text))

OLLAMA_URL = settings.OLLAMA_URL
TRANSCRIPTS_DIR = pathlib.Path(settings.TRANSCRIPTS_DIR)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.TRANSLITERATION_LOG_FILE, encoding="utf-8")
    ]
)
logger = logging.getLogger("transliteration_worker")

def transliterate_file(json_path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)
    transcript = data.get("transcript")
    language = data.get("language")
    # Only transliterate if language is 'hi' (Hindi)
    if language != "hi":
        logger.info(f"Skipping (not Hindi): {json_path}")
        return False
    # Skip if already transliterated
    if "transcript_original" in data and "transcript" in data and data["transcript_original"] != data["transcript"]:
        logger.info(f"Already transliterated: {json_path}")
        return False
    if not transcript:
        logger.info(f"No transcript found in: {json_path}")
        return False
    if not contains_devanagari(transcript):
        logger.info(f"No Devanagari found in: {json_path}")
        return False
    logger.info(f"Transliterating: {json_path}")
    chunks = list(chunk_text(transcript, max_words=500))
    transliterated_chunks = []
    for idx, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {idx+1}/{len(chunks)}")
        prompt = (
            "You are a strict transliteration engine. Your ONLY job is to convert every Hindi word in the following text from Devanagari script to Latin script (Hinglish). Do NOT summarize, translate, paraphrase, or add/remove any words, punctuation, or lines. Do NOT output any Hindi/Devanagari script or explanation. Output must be the same length and structure as the input, but with all Hindi words in Latin script. Output ONLY the transliterated text, nothing else. If you see any non-Hindi text, leave it unchanged. Here is the text (UTF-8 encoded):\n\n"
            f"{chunk}"
        )
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": "gemma3:4b",
                "prompt": prompt,
                "stream": False
            },
            timeout=600
        )
        if response.status_code == 200:
            result = response.json()
            transliterated_chunk = result.get("response", "")
            logger.info(f"Chunk {idx+1} result (first 100 chars): {transliterated_chunk[:100]}")
            transliterated_chunks.append(transliterated_chunk)
        else:
            logger.error(f"Ollama transliteration error: {response.text}")
            transliterated_chunks.append(chunk)
    transliterated = ' '.join(transliterated_chunks)
    data["transcript_original"] = transcript
    data["transcript"] = transliterated
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"Transliteration complete and saved for {json_path}")
    return True

def scan_and_transliterate():
    for channel_dir in TRANSCRIPTS_DIR.iterdir():
        if not channel_dir.is_dir():
            continue
        for json_file in channel_dir.glob("*.json"):
            try:
                transliterate_file(json_file)
            except Exception as e:
                logger.error(f"Error processing {json_file}: {e}")

if __name__ == "__main__":
    # while True:
    logger.info("Scanning for Hindi transcripts to transliterate...")
    scan_and_transliterate()
    logger.info("Transliteration complete")
    # logger.info("Sleeping for 60 seconds...")
    # time.sleep(60)
