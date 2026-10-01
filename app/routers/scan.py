import hashlib
from typing import Optional, Union
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile
from app import config
from app.schemas import QRCode, ScanResponse
from app.services import analyzer, provenance, qr_reader

router = APIRouter(prefix="/api", tags=["scan"])

# In-memory cache: same input -> same saved result, zero quota used.
# It is cleared whenever the server restarts.
_CACHE: dict = {}
_CACHE_MAX = 100


def _cache_key(text: Optional[str], file_parts: list[tuple[bytes, str]], file_names: list[str]) -> str:
    h = hashlib.sha256()
    h.update((text or "").strip().encode("utf-8"))
    for (file_bytes, mime), file_name in zip(file_parts, file_names):
        h.update(b"|")
        h.update(mime.encode("utf-8"))
        encoded_name = file_name.encode("utf-8")
        h.update(len(encoded_name).to_bytes(4, "big"))
        h.update(encoded_name)
        h.update(len(file_bytes).to_bytes(8, "big"))
        h.update(file_bytes)
    return h.hexdigest()


@router.post("/scan", response_model=ScanResponse)
async def scan(
    text: Optional[str] = Form(None),
    # Accepting str too means a junk value from Swagger is ignored instead of causing a 422
    file: Union[UploadFile, str, None] = File(None),
    files: Optional[list[UploadFile]] = File(None),
):
    uploads = [upload for upload in (files or []) if isinstance(upload, StarletteUploadFile) and upload.filename]
    if isinstance(file, StarletteUploadFile) and file.filename:
        uploads.insert(0, file)
    if len(uploads) > config.MAX_UPLOAD_FILES:
        raise HTTPException(413, f"Upload no more than {config.MAX_UPLOAD_FILES} files at once")

    file_parts = []
    for upload in uploads:
        if upload.content_type not in config.ALLOWED_MIME:
            raise HTTPException(415, f"Unsupported file type: {upload.content_type}")
        file_bytes = await upload.read()
        if len(file_bytes) > config.MAX_UPLOAD_MB * 1024 * 1024:
            raise HTTPException(413, f"{upload.filename} is larger than {config.MAX_UPLOAD_MB} MB")
        file_parts.append((file_bytes, upload.content_type))

    key = _cache_key(text, file_parts, [upload.filename or "" for upload in uploads])
    if key in _CACHE:
        return _CACHE[key]

    qr_codes = []
    for upload, (file_bytes, mime) in zip(uploads, file_parts):
        if mime.startswith("image/"):
            qr_codes.extend(
                QRCode(file_name=upload.filename or "uploaded image", content=content)
                for content in qr_reader.decode_qr_codes(file_bytes)
            )

    try:
        analysis = await analyzer.analyze(text, file_parts, [qr.content for qr in qr_codes])
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

    result = ScanResponse(analysis=analysis, provenance=prov, qr_codes=qr_codes)

    # Only successful scans are cached, so errors are never saved
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.pop(next(iter(_CACHE)))
    _CACHE[key] = result
    return result