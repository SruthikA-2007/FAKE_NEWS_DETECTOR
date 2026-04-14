from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)


def _deduplicate_claims(claims: list[str]) -> list[str]:
    unique_claims: list[str] = []
    seen: set[str] = set()

    for claim in claims:
        normalized = re.sub(r"\s+", " ", claim).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_claims.append(normalized)

    return unique_claims


def _fallback_claim_split(article_text: str) -> list[str]:
    fragments = re.split(r"(?<=[.!?])\s+", article_text.strip())
    claims = [fragment.strip() for fragment in fragments if len(fragment.strip()) > 15]
    return _deduplicate_claims(claims) or ([article_text.strip()] if article_text.strip() else [])


def _parse_json_claims(payload: Any) -> list[str]:
    if isinstance(payload, list):
        return [str(item).strip() for item in payload if str(item).strip()]

    if isinstance(payload, dict):
        raw_claims = payload.get("claims") or payload.get("items") or []
        if isinstance(raw_claims, list):
            return [str(item).strip() for item in raw_claims if str(item).strip()]

    return []


def _extract_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if isinstance(text, str) and text.strip():
        return text.strip()

    candidates = getattr(response, "candidates", None) or []
    for candidate in candidates:
        content = getattr(candidate, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            part_text = getattr(part, "text", None)
            if isinstance(part_text, str) and part_text.strip():
                return part_text.strip()
    return ""


async def extract_claims(article_text: str) -> list[str]:
    cleaned_article = article_text.strip()
    if not cleaned_article:
        return []

    if not settings.gemini_api_key:
        return _fallback_claim_split(cleaned_article)

    def _generate_claims() -> list[str]:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)
        prompt = (
            "You are a fact-checking assistant. Split the following article into independent factual claims only. "
            "Ignore opinions, speculation, headings, and repeated statements. "
            "Return ONLY valid JSON as a JSON array of strings. Do not wrap the answer in markdown.\n\n"
            f"Article:\n{cleaned_article}"
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        )
        response_text = _extract_text(response)
        if not response_text:
            return []

        try:
            parsed = json.loads(response_text)
        except json.JSONDecodeError:
            match = re.search(r"\[[\s\S]*\]", response_text)
            if not match:
                return []
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                return []

        return _deduplicate_claims(_parse_json_claims(parsed))

    try:
        claims = await asyncio.to_thread(_generate_claims)
        return claims or _fallback_claim_split(cleaned_article)
    except Exception as exc:
        logger.exception("Gemini claim extraction failed: %s", exc)
        return _fallback_claim_split(cleaned_article)
