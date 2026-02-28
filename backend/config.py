"""Configuration with placeholder API keys."""
import os
from pathlib import Path

# Load .env file if it exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)

# Mistral AI API
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "your-mistral-api-key-here")

# ElevenLabs API for TTS
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "your-elevenlabs-api-key-here")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")  # Rachel voice

# WHO ICD API (register at https://icd.who.int/icdapi)
WHO_CLIENT_ID = os.getenv("WHO_CLIENT_ID", "your-who-client-id-here")
WHO_CLIENT_SECRET = os.getenv("WHO_CLIENT_SECRET", "your-who-client-secret-here")

# Server config
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", 8000))
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
