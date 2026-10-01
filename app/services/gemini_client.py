from google import genai
from google.genai import types
from app import config

if not config.GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY missing. Copy .env.example to .env and add your free key.")

client = genai.Client(
    api_key=config.GEMINI_API_KEY,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=3,
            initial_delay=2.0,
            http_status_codes=[503],
        )
    ),
)
MODEL = config.GEMINI_MODEL
SEARCH_MODEL = config.GEMINI_SEARCH_MODEL