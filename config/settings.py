import os
from dotenv import load_dotenv

load_dotenv()

# API URLs
API_BASE = "http://localhost:8000/api"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")

# ElevenLabs API Keys
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID1 = os.getenv("ELEVENLABS_VOICE_ID1")
ELEVENLABS_VOICE_ID2 = os.getenv("ELEVENLABS_VOICE_ID2")

# Data Directories
TRANSCRIPTS_DIR = "data/transcripts"
SAVED_SCRIPTS_DIR = "data/saved_scripts"
NARRATED_PODCASTS_DIR = "data/narrated_podcasts"
NARRATED_PODCASTS_BARK_DIR = "data/narrated_podcasts_bark"

# Logging
LOGS_DIR = "logs"
BACKEND_LOG_FILE = os.path.join(LOGS_DIR, "backend_api.log")
TRANSLITERATION_LOG_FILE = os.path.join(LOGS_DIR, "transliteration_worker.log") 