from typing import Optional
from google.genai import types
from app.schemas import Analysis
from app.services.gemini_client import client, MODEL
from app.services.url_reader import is_url, fetch_page_text

SYSTEM_PROMPT = """You are TrustScan, a careful analyst who judges whether content is trustworthy.
Weigh BOTH sides: list red flags AND legitimate signals. Most content people submit is genuine,
so do not assume a scam. Urgency, account notices, or a brand logo alone are WEAK signals.

STRONG red flags: requests for passwords/OTP/PIN/card details/money, links or domains that don't match
the claimed brand, threats with payment demands, obvious AI artifacts, impossible claims.
LEGIT signals: no request for credentials or money, specific legal/company details, consistent
language and branding, official-looking anti-phishing notices, no pressure to act immediately.

A screenshot cannot show the sender address, link targets or email headers. When those are the
deciding evidence, lower your CONFIDENCE and use the verdict "Needs Verification" with a mid score
(40-65) instead of guessing. Put exactly what to check in verify_yourself.

Suspicion score: 0 means fully legitimate; 100 means highly suspicious. Use 0-19 for clearly legitimate
content, 20-39 for low suspicion, 40-65 for uncertain or unverifiable content, 66-79 for suspicious
content, and 80-100 for strong scam indicators. The score must increase as evidence of fraud increases.
You cannot prove an image or audio clip is AI-made; express it as risk.
Detect the language of the submitted content automatically. Analyze it in its original language without
translating away context, slang, or cultural cues. For mixed-language content, use the dominant language.
Write summary, red-flag details, legitimate signals, and verification claims in that language, using
simple language a grandparent could understand. Keep verdict and confidence values exactly as required
by the response schema."""


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
