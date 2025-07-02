from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from backend.api.transcript_listing import router as transcript_listing_router
from backend.api.llm_generate import router as llm_generate_router
from backend.api.narrate_elevenlabs import router as narrate_script_router
from backend.api.narrate_bark import router as narrate_script_bark_router
from backend.api.youtube_fetch import router as youtube_fetch_router
from config import settings

app = FastAPI()

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(settings.BACKEND_LOG_FILE, encoding="utf-8")
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
app.include_router(narrate_script_router)
app.include_router(narrate_script_bark_router)
app.include_router(youtube_fetch_router)
