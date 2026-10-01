import time
from typing import List
from google.genai import types
from app.schemas import Provenance, Source
from app.services.gemini_client import client, MODEL, SEARCH_MODEL

COOLDOWN_SECONDS = 600
_search_blocked_until = 0.0


def _claims_block(claims: List[str]) -> str:
    return "\n- ".join(claims) if claims else "(no specific claims)"


async def _search_trace(claims: List[str], summary: str) -> Provenance:
    prompt = (
        "Use Google Search to check these claims from a piece of content.\n"
        f"Context: {summary}\n"
        "Claims:\n- " + _claims_block(claims) + "\n\n"
        "Answer in under 150 words: (1) Has this been debunked or confirmed by credible outlets/fact-checkers? "
        "(2) Where did it likely originate, and when did it start spreading? "
        "(3) Any older/original version of the same content? Be neutral and cite only what you found."
    )
    response = await client.aio.models.generate_content(
        model=SEARCH_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2,
        ),
    )

    sources, queries = [], []
    cand = response.candidates[0] if response.candidates else None
    meta = getattr(cand, "grounding_metadata", None)
    if meta:
        queries = list(meta.web_search_queries or [])
        seen = set()
        for chunk in (meta.grounding_chunks or []):
            if chunk.web and chunk.web.uri not in seen:
                seen.add(chunk.web.uri)
                sources.append(Source(title=chunk.web.title or chunk.web.uri, url=chunk.web.uri))

    return Provenance(
        summary=response.text or "No summary returned.",
        sources=sources[:6],
        search_queries=queries,
    )


async def _model_only_trace(claims: List[str], summary: str) -> Provenance:
    prompt = (
        "You cannot search the web right now. Using only your own knowledge, assess these claims.\n"
        f"Context: {summary}\n"
        "Claims:\n- " + _claims_block(claims) + "\n\n"
        "Answer in under 100 words: does this match a known scam, hoax or misinformation pattern, "
        "and what is its likely origin? Do NOT invent sources, links or dates. "
        "If you are unsure, say so."
    )
    response = await client.aio.models.generate_content(
        model=MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(temperature=0.2),
    )
    text = response.text or "No assessment returned."
    return Provenance(
        summary="AI assessment, not web-verified: " + text,
        sources=[],
        search_queries=[],
    )


async def trace_origin(claims: List[str], summary: str) -> Provenance:
    """Step 2: search-grounded origin check, with a model-only fallback if search is unavailable."""
    global _search_blocked_until

    if time.time() >= _search_blocked_until:
        try:
            return await _search_trace(claims, summary)
        except Exception as e:
            msg = str(e)
            if "429" in msg or "RESOURCE_EXHAUSTED" in msg:
                _search_blocked_until = time.time() + COOLDOWN_SECONDS
            print(f"[provenance] search failed, using fallback: {msg[:120]}")

    return await _model_only_trace(claims, summary)