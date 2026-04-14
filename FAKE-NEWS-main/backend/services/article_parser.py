from __future__ import annotations

import asyncio
import importlib

try:
    newspaper_module = importlib.import_module("newspaper")
    Article = getattr(newspaper_module, "Article", None)
except Exception:  # pragma: no cover - optional dependency fallback
    Article = None

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
    return (
        "OCR placeholder: image text extraction is not implemented yet. "
        "Pass the image content through an OCR service before verification. "
        f"Source: {content.strip()}"
    )


async def parse_article(request: AnalyzeRequest) -> str:
    if request.type == "text":
        return request.content.strip()
    if request.type == "url":
        return await _parse_url(request.content.strip())
    if request.type == "image":
        return await _parse_image(request.content)
    return request.content.strip()
