from __future__ import annotations

import asyncio
from dataclasses import dataclass, field

import httpx

from config import settings
from models.response_model import Verdict
from utils.api_clients import query_fact_check, query_news, query_wikipedia


@dataclass(slots=True)
class VerificationResult:
    verdict: Verdict
    confidence: float
    sources: list[str] = field(default_factory=list)


def _normalize_query(claim: str, entities: list[str]) -> str:
    entity_fragment = " ".join(entities[:3]).strip()
    candidate = entity_fragment or claim
    return " ".join(candidate.split())[:250]


def _contains_positive_rating(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "true",
            "mostly true",
            "correct",
            "accurate",
            "supported",
            "verified",
        )
    )


def _contains_negative_rating(text: str) -> bool:
    lowered = text.lower()
    return any(
        phrase in lowered
        for phrase in (
            "false",
            "mostly false",
            "misleading",
            "pants on fire",
            "fabricated",
            "unsubstantiated",
        )
    )


def _deduplicate_sources(sources: list[str]) -> list[str]:
    seen: set[str] = set()
    unique_sources: list[str] = []
    for source in sources:
        normalized = source.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        unique_sources.append(normalized)
    return unique_sources


def _score_evidence(
    fact_check_results: list[dict[str, str]],
    wikipedia_results: list[dict[str, str]],
    news_results: list[dict[str, str]],
) -> VerificationResult:
    sources: list[str] = []
    positive_signals = 0
    negative_signals = 0

    for result in fact_check_results:
        source_name = result.get("source", "Google Fact Check")
        title = result.get("title", "")
        rating = result.get("rating", "")
        url = result.get("url", "")
        if title:
            sources.append(f"{source_name}: {title}")
        elif rating:
            sources.append(f"{source_name}: {rating}")
        if url:
            sources.append(url)
        if _contains_positive_rating(title) or _contains_positive_rating(rating):
            positive_signals += 2
        if _contains_negative_rating(title) or _contains_negative_rating(rating):
            negative_signals += 2

    for result in wikipedia_results:
        title = result.get("title", "")
        url = result.get("url", "")
        snippet = result.get("snippet", "")
        if title:
            sources.append(f"Wikipedia: {title}")
        if url:
            sources.append(url)
        if snippet:
            positive_signals += 1

    for result in news_results:
        title = result.get("title", "")
        url = result.get("url", "")
        source_name = result.get("source", "NewsAPI")
        if title:
            sources.append(f"{source_name}: {title}")
        if url:
            sources.append(url)
        if title or url:
            positive_signals += 1

    confidence = 0.45
    verdict = "UNVERIFIED"

    if positive_signals > 0 and negative_signals == 0:
        confidence = min(0.95, 0.55 + (positive_signals * 0.08))
        verdict = "LIKELY TRUE"
    elif negative_signals > 0 and positive_signals == 0:
        confidence = min(0.95, 0.65 + (negative_signals * 0.08))
        verdict = "SUSPICIOUS"
    elif positive_signals > 0 and negative_signals > 0:
        confidence = 0.55
        verdict = "SUSPICIOUS"
    elif positive_signals == 0 and negative_signals == 0:
        confidence = 0.4
        verdict = "UNVERIFIED"

    return VerificationResult(
        verdict=verdict,
        confidence=max(0.0, min(confidence, 0.99)),
        sources=_deduplicate_sources(sources),
    )


async def verify_claim(claim: str, entities: list[str]) -> VerificationResult:
    normalized_query = _normalize_query(claim, entities)

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        fact_check_task = query_fact_check(client, normalized_query)
        wikipedia_task = query_wikipedia(client, normalized_query)
        news_task = query_news(client, normalized_query)

        fact_check_results, wikipedia_results, news_results = await asyncio.gather(
            fact_check_task,
            wikipedia_task,
            news_task,
        )

    return _score_evidence(fact_check_results, wikipedia_results, news_results)
