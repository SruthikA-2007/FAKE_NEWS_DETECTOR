from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import httpx

from config import settings

logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
FALLBACK_MODELS = [
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash-8b-latest",
    "gemini-1.5-pro-latest",
]


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
    """
    Fallback claim extraction using sentence splitting.
    Filters out very short sentences and prioritizes meaningful claims.
    """
    # Split on sentence boundaries
    fragments = re.split(r"(?<=[.!?])\s+", article_text.strip())
    claims = []
    
    for fragment in fragments:
        normalized = fragment.strip()
        # Increased minimum length from 15 to 20 characters for better quality
        # Skip sentences that are mostly conjunctions or common phrases
        if (len(normalized) > 20 and 
            not normalized.lower().startswith(('and ', 'but ', 'or ', 'the ', 'a ')) and
            normalized.count(' ') >= 2):  # At least 3 words
            claims.append(normalized)
    
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


def _extract_text_from_api_response(payload: dict[str, Any]) -> str:
    candidates = payload.get("candidates") or []
    for candidate in candidates:
        content = candidate.get("content") or {}
        parts = content.get("parts") or []
        for part in parts:
            part_text = part.get("text")
            if isinstance(part_text, str) and part_text.strip():
                return part_text.strip()
    return ""


def _fetch_available_models(api_key: str, timeout_seconds: float) -> list[str]:
    try:
        response = httpx.get(
            f"{GEMINI_API_BASE}/models",
            params={"key": api_key},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Unable to list Gemini models: %s", exc)
        return []

    data = response.json()
    result: list[str] = []
    for model in data.get("models", []):
        model_name = str(model.get("name", ""))
        methods = model.get("supportedGenerationMethods") or []
        if "generateContent" not in methods:
            continue
        if not model_name.startswith("models/"):
            continue
        cleaned = model_name.split("models/", 1)[1].strip()
        if cleaned:
            result.append(cleaned)
    return result


def _build_candidate_models(configured_model: str, available_models: list[str]) -> list[str]:
    preferred_available = [
        model
        for model in available_models
        if "gemini" in model.lower() and ("flash" in model.lower() or "pro" in model.lower())
    ]
    model_candidates = [configured_model.strip(), *FALLBACK_MODELS, *preferred_available]

    deduped: list[str] = []
    seen: set[str] = set()
    for model_name in model_candidates:
        normalized = model_name.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped


def _request_claim_extraction(
    *,
    api_key: str,
    model_name: str,
    prompt: str,
    timeout_seconds: float,
) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
        },
    }

    response = httpx.post(
        f"{GEMINI_API_BASE}/models/{model_name}:generateContent",
        params={"key": api_key},
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return _extract_text_from_api_response(response.json())


async def extract_claims(article_text: str) -> list[str]:
    cleaned_article = article_text.strip()
    if not cleaned_article:
        return []

    if not settings.gemini_api_key:
        return _fallback_claim_split(cleaned_article)

    def _generate_claims() -> list[str]:
        prompt = (
            "You are a fact-checking assistant. Split the following article into independent factual claims only. "
            "Ignore opinions, speculation, headings, and repeated statements. "
            "Return ONLY valid JSON as a JSON array of strings. Do not wrap the answer in markdown.\n\n"
            f"Article:\n{cleaned_article}"
        )

        available_models = _fetch_available_models(settings.gemini_api_key, settings.request_timeout_seconds)
        candidate_models = _build_candidate_models(settings.gemini_model, available_models)

        for model_name in candidate_models:
            try:
                response_text = _request_claim_extraction(
                    api_key=settings.gemini_api_key,
                    model_name=model_name,
                    prompt=prompt,
                    timeout_seconds=settings.request_timeout_seconds,
                )
                if not response_text:
                    continue
                try:
                    parsed = json.loads(response_text)
                except json.JSONDecodeError:
                    match = re.search(r"\[[\s\S]*\]", response_text)
                    if not match:
                        continue
                    try:
                        parsed = json.loads(match.group(0))
                    except json.JSONDecodeError:
                        continue

                claims = _deduplicate_claims(_parse_json_claims(parsed))
                if claims:
                    return claims
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in {400, 404}:
                    logger.debug("Gemini model %s unavailable, trying next model.", model_name)
                    continue
                logger.info("Gemini request failed for model %s: %s", model_name, exc)
            except Exception as exc:
                logger.info("Gemini claim extraction failed for model %s: %s", model_name, exc)

        logger.warning("Gemini claim extraction unavailable for all candidate models, using fallback splitter.")
        return []

    try:
        claims = await asyncio.to_thread(_generate_claims)
        return claims or _fallback_claim_split(cleaned_article)
    except Exception as exc:
        logger.exception("Gemini claim extraction failed: %s", exc)
        return _fallback_claim_split(cleaned_article)
