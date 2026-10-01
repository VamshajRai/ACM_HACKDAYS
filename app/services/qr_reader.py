from io import BytesIO

import zxingcpp
from PIL import Image, ImageOps, UnidentifiedImageError


def decode_qr_codes(image_bytes: bytes) -> list[str]:
    try:
        with Image.open(BytesIO(image_bytes)) as image:
            decoded = zxingcpp.read_barcodes(
                ImageOps.exif_transpose(image).convert("RGB"),
                formats=zxingcpp.BarcodeFormat.QRCode,
                try_rotate=True,
            )
    except (Image.DecompressionBombError, OSError, UnidentifiedImageError, ValueError):
        return []

    return list(dict.fromkeys(code.text for code in decoded if code.text))