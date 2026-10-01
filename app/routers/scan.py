import hashlib
from typing import Optional, Union
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from app import config
from app.schemas import ScanResponse
from app.services import analyzer, provenance

router = APIRouter(prefix="/api", tags=["scan"])

# In-memory cache: same input -> same saved result, zero quota used.
# It is cleared whenever the server restarts.
_CACHE: dict = {}
_CACHE_MAX = 100


def _cache_key(text: Optional[str], file_bytes: Optional[bytes], mime: Optional[str]) -> str:
    h = hashlib.sha256()
    h.update((text or "").strip().encode("utf-8"))
    h.update(b"|")
    h.update(mime.encode() if mime else b"")
    h.update(b"|")
    if file_bytes:
        h.update(file_bytes)
    return h.hexdigest()


@router.post("/scan", response_model=ScanResponse)
async def scan(
    text: Optional[str] = Form(None),
    # Accepting str too means a junk value from Swagger is ignored instead of causing a 422
    file: Union[UploadFile, str, None] = File(None),
):
    file_bytes, mime = None, None

    # Real uploads are Starlette's UploadFile (FastAPI's UploadFile is a subclass of it),
    # so check against the Starlette class or genuine uploads get ignored.
    if isinstance(file, StarletteUploadFile) and file.filename:
        mime = file.content_type
        if mime not in config.ALLOWED_MIME:
            raise HTTPException(415, f"Unsupported file type: {mime}")
        file_bytes = await file.read()
        if len(file_bytes) > config.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"File larger than {config.MAX_UPLOAD_MB} MB")

    key = _cache_key(text, file_bytes, mime)
    if key in _CACHE:
        return _CACHE[key]

    try:
        analysis = await analyzer.analyze(text, file_bytes, mime)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Gemini analysis failed: {e}")

    prov = None
    if analysis.claims_to_verify:
        try:
            prov = await provenance.trace_origin(analysis.claims_to_verify, analysis.summary)
        except Exception:
            prov = None  # never fail the whole scan because of provenance

    result = ScanResponse(analysis=analysis, provenance=prov)

    # Only successful scans are cached, so errors are never saved
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = result
    return result