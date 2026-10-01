import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
# Separate model for the search step so it has its own quota counter
GEMINI_SEARCH_MODEL = os.getenv("GEMINI_SEARCH_MODEL", GEMINI_MODEL)
MAX_UPLOAD_MB = 10
MAX_UPLOAD_FILES = 5
ALLOWED_MIME = {
    "image/png", "image/jpeg", "image/webp",
    "audio/mpeg", "audio/wav", "audio/mp3", "audio/ogg", "audio/mp4",
}