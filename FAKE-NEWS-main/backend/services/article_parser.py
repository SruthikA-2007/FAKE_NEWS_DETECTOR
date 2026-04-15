from __future__ import annotations

import asyncio
import importlib
import re
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

try:
    newspaper_module = importlib.import_module("newspaper")
    Article = getattr(newspaper_module, "Article", None)
except Exception:  # pragma: no cover - optional dependency fallback
    Article = None

from models.request_model import AnalyzeRequest


def _normalize_url(url: str) -> str:
    candidate = url.strip()
    if not candidate:
        return ""
    if not re.match(r"^https?://", candidate, flags=re.IGNORECASE):
        candidate = f"https://{candidate}"

    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return candidate


def _extract_text_from_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe", "footer", "nav"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    # Prefer article-specific blocks before falling back to broader text nodes.
    candidates = [
        *soup.select("article p"),
        *soup.select("main p"),
        *soup.select("[role='main'] p"),
    ]

    if not candidates:
        candidates = [*soup.find_all("p"), *soup.find_all("li"), *soup.find_all("h2")]

    paragraphs: list[str] = []
    for node in candidates:
        text = node.get_text(" ", strip=True)
        if len(text) < 20:
            continue
        paragraphs.append(text)

    body = "\n".join(paragraphs)

    # Last-resort fallback for pages that do not use paragraph tags heavily.
    if len(body) < 80:
        page_text = soup.get_text(" ", strip=True)
        page_text = re.sub(r"\s+", " ", page_text).strip()
        # Keep a bounded amount of text for downstream claim extraction.
        body = page_text[:12000]

    if title and body:
        return f"{title}\n{body}".strip()
    return (body or title).strip()


async def _parse_url_with_http(url: str) -> str:
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36"
                )
            },
        ) as client:
            response = await client.get(url)
            response.raise_for_status()
    except Exception:
        return ""

    content_type = (response.headers.get("content-type") or "").lower()
    if "text/html" not in content_type and "application/xhtml+xml" not in content_type:
        raw_text = response.text.strip()
        return raw_text[:12000]

    return _extract_text_from_html(response.text)


async def _parse_url(url: str) -> str:
    normalized_url = _normalize_url(url)
    if not normalized_url:
        return ""

    if Article is None:
        return await _parse_url_with_http(normalized_url)

    def _download_and_parse() -> str:
        article = Article(normalized_url)
        article.download()
        article.parse()
        parts = [article.title.strip(), article.text.strip()]
        return "\n".join(part for part in parts if part)

    try:
        parsed_text = await asyncio.to_thread(_download_and_parse)
        cleaned = parsed_text.strip()
        # Some sites fail in newspaper3k but still work with raw HTML parsing.
        if len(cleaned) >= 120:
            return cleaned
    except Exception:
        pass

    fallback_text = await _parse_url_with_http(normalized_url)
    return fallback_text.strip()


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
