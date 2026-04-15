from __future__ import annotations

import asyncio
import base64
import importlib
import io

try:
    newspaper_module = importlib.import_module("newspaper")
    Article = getattr(newspaper_module, "Article", None)
except Exception:  # pragma: no cover - optional dependency fallback
    Article = None

try:
    from PIL import Image
    import pytesseract
except Exception:  # pragma: no cover - optional OCR fallback
    Image = None
    pytesseract = None

from models.request_model import AnalyzeRequest


async def _parse_url(url: str) -> str:
    if Article is None:
        return url.strip()

    def _download_and_parse() -> str:
        article = Article(url)
        article.download()
        article.parse()
        parts = [article.title.strip(), article.text.strip()]
        return "\n".join(part for part in parts if part)

    try:
        parsed_text = await asyncio.to_thread(_download_and_parse)
        return parsed_text.strip() or url.strip()
    except Exception:
        return url.strip()


async def _parse_image(content: str) -> str:
    try:
        image_bytes = base64.b64decode(content)
    except Exception:
        return (
            "OCR placeholder: uploaded image could not be decoded. "
            "Please make sure the file is a valid image."
        )

    if Image is None or pytesseract is None:
        return (
            "OCR placeholder: the server does not have OCR support enabled. "
            "Install Pillow and pytesseract and ensure Tesseract is available."
        )

    try:
        image = Image.open(io.BytesIO(image_bytes))
        extracted_text = pytesseract.image_to_string(image, lang="eng")
        extracted_text = extracted_text.strip()
        return extracted_text or (
            "OCR placeholder: the image was processed but no text was detected. "
            "Try a clearer image or scan of the article."
        )
    except Exception:
        return (
            "OCR placeholder: failed to extract text from the uploaded image. "
            "Please verify the image format and try again."
        )


async def parse_article(request: AnalyzeRequest) -> str:
    if request.type == "text":
        return request.content.strip()
    if request.type == "url":
        return await _parse_url(request.content.strip())
    if request.type == "image":
        return await _parse_image(request.content)
    return request.content.strip()
