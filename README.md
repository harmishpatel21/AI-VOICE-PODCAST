# AI Voice Podcast

AI Voice Podcast is an end-to-end pipeline for generating fictional podcast episodes using AI, featuring selected YouTubers as characters. The system extracts YouTube transcripts, allows users to select two characters and a topic, generates a podcast script using a local LLM (Ollama/Mistral), and narrates the script using ElevenLabs TTS, saving and playing back the audio. The UI is built with Streamlit and the backend is powered by FastAPI.

## Features

-   **YouTube Transcript Extraction:** Extract and cache transcripts from YouTube videos using `yt-dlp` and `youtube-transcript-api`.
-   **Podcast Script Generation:** Select two YouTubers and a topic, then generate a podcast script in their style using a local LLM (Ollama/Mistral).
-   **Script Expressions:** Scripts include expressive cues (e.g., [smiling], [laughs]) for more natural narration.
-   **AI Narration:** Use ElevenLabs TTS (and Bark TTS) to narrate the script, splitting by speaker and removing expressions from the spoken text.
-   **Audio Stitching:** Combine all lines into a single podcast audio file, organized by topic and metadata.
-   **Streamlit UI:** Modular dashboard for extracting transcripts, generating scripts, and listening to podcasts.
-   **Persistent Storage:** All scripts and audio are saved in structured directories by topic and metadata.

## Project Structure

```
AI-Voice-Podcast/
├── backend/
│   ├── api/
│   │   ├── llm_generate.py         # FastAPI endpoint for LLM script generation
│   │   ├── narrate_bark.py         # FastAPI endpoint for Bark narration
│   │   ├── narrate_elevenlabs.py   # FastAPI endpoint for ElevenLabs narration
│   │   ├── transcript_listing.py   # FastAPI endpoints for transcript management
│   │   └── youtube_fetch.py        # FastAPI endpoints for YouTube video/transcript fetching
│   ├── core/
│   │   └── prompt_utility.py       # Centralized prompt definitions
│   └── main.py                     # Main FastAPI app
├── config/
├── data/
├── frontend/
│   └── dashboard.py                # Streamlit UI
├── logs/
├── tests/
├── workers/
│   └── transliteration.py          # Worker for Hindi to Hinglish transliteration
├── PROJECT_PLAN.md
├── README.md
├── requirements.txt
├── .env                            # API keys (not committed)
└── ...
```

## Setup Instructions

### 1. Clone the Repository

```
git clone <your-repo-url>
cd AI-Voice-Podcast
```

### 2. Create and Activate a Virtual Environment

```
python -m venv venv
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```
pip install -r requirements.txt
```

### 4. Install ffmpeg (Required by pydub)

-   **Windows:** Download from https://ffmpeg.org/download.html and add to PATH
-   **Mac:** `brew install ffmpeg`
-   **Linux:** `sudo apt-get install ffmpeg`

### 5. Set Up Environment Variables

Create a `.env` file in the project root with your API keys:

```
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID1=your_elevenlabs_voice_id_for_char1
ELEVENLABS_VOICE_ID2=your_elevenlabs_voice_id_for_char2
```

### 6. Start the FastAPI Backend

```
uvicorn backend.main:app --reload
```

### 7. Start the Streamlit UI

```
streamlit run frontend/dashboard.py
```

## Usage

1. **Extract Transcript:** Use the UI to fetch and save YouTube transcripts for your chosen YouTubers.
2. **Create Podcast Script:** Select two YouTubers and a topic, then generate a script using the LLM.
3. **Narrate & Listen:** Narrate the script with ElevenLabs (and/or Bark) and listen to the generated podcast audio. All files are saved for future playback.

## Notes

-   Ollama/Mistral must be running locally for LLM script generation.
-   ElevenLabs API is required for ElevenLabs TTS. Free tier available.
-   All generated files are organized by topic and metadata for easy access.
-   Hindi transcripts will be automatically transliterated to Hinglish (Latin script) by a background worker.
