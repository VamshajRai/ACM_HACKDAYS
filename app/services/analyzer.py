from typing import Optional
from google.genai import types
from app.schemas import Analysis
from app.services.gemini_client import client, MODEL
from app.services.url_reader import is_url, fetch_page_text

SYSTEM_PROMPT = """You are TrustScan, a misinformation, deepfake and scam analyst.
Examine the content (text, webpage text, image/screenshot, or audio) and judge how trustworthy it is.
Look for: AI-generation artifacts (odd hands/text/lighting, unnatural voice cadence), edited or fake screenshots,
emotional manipulation, fake urgency, requests for money/OTP/personal data, suspicious links or lookalike domains,
sensational claims with no source, and out-of-context reuse.
Be honest about uncertainty: you cannot PROVE an image is AI-made, so express it as risk.
Write red flags in simple language a grandparent could understand.
trust_score: 0 = almost certainly fake/scam, 100 = looks authentic."""


async def analyze(text: Optional[str], file_bytes: Optional[bytes], mime: Optional[str]) -> Analysis:
    parts: list = []

    if text and text.strip():
        content = await fetch_page_text(text.strip()) if is_url(text) else text.strip()
        parts.append(f"CONTENT TO CHECK:\n{content}")

    if file_bytes and mime:
        parts.append(types.Part.from_bytes(data=file_bytes, mime_type=mime))

    if not parts:
        raise ValueError("Send some text/URL or an image/audio file.")

    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=Analysis,   # forces valid JSON matching our schema
            temperature=0.2,
        ),
    )
    return response.parsed
