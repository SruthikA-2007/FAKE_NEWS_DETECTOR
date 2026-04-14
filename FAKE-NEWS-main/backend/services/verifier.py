from __future__ import annotations

import asyncio
import re
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


def _normalize_query(claim: str, entities: list[dict[str, str]]) -> str:
    entity_fragment = " ".join(e["text"] for e in entities[:3]).strip()
    candidate = entity_fragment or claim
    return " ".join(candidate.split())[:250]


def _contains_positive_rating(text: str) -> bool:
    lowered = text.lower()
    # Use word boundaries to avoid matching "true" in "untrue"
    positive_patterns = [
        r"\btrue\b",
        r"\bmostly true\b",
        r"\bcorrect\b",
        r"\baccurate\b",
        r"\bsupported\b",
        r"\bverified\b",
    ]
    return any(re.search(pattern, lowered) for pattern in positive_patterns)


def _contains_negative_rating(text: str) -> bool:
    lowered = text.lower()
    negative_patterns = [
        r"\bfalse\b",
        r"\bmostly false\b",
        r"\bmisleading\b",
        r"\bpants on fire\b",
        r"\bfabricated\b",
        r"\bunsubstantiated\b",
        r"\buntrue\b",
        r"\binaccurate\b",
        r"\bwrong\b",
        r"\bhoax\b",
        r"\bfake\b",
    ]
    return any(re.search(pattern, lowered) for pattern in negative_patterns)


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
    neutral_signals = 0

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
            lowered = snippet.lower()
            if any(w in lowered for w in ["hoax", "fake", "false", "misinformation", "disputed", "conspiracy", "rumor", "debunked", "unverified"]):
                negative_signals += 1
            else:
                neutral_signals += 1

    for result in news_results:
        title = result.get("title", "")
        url = result.get("url", "")
        source_name = result.get("source", "NewsAPI")
        description = result.get("description", "")
        if title:
            sources.append(f"{source_name}: {title}")
        if url:
            sources.append(url)
        if title or url:
            lowered = f"{title} {description}".lower()
            if any(w in lowered for w in ["hoax", "fake", "false", "misinformation", "disputed", "conspiracy", "rumor", "debunked", "unverified"]):
                negative_signals += 1
            else:
                neutral_signals += 1

    evidence_strength = 0.45
    verdict: Verdict = "Unverified"

    if positive_signals > 0 and negative_signals == 0:
        # High signals mean high truthfulness
        evidence_strength = min(0.95, 0.65 + (positive_signals * 0.1) + (neutral_signals * 0.02))
        verdict = "True"
    elif negative_signals > 0:
        if positive_signals > 0:
            # Mixed signals
            evidence_strength = 0.45
            verdict = "Misleading"
        else:
            # Negative signals mean low truthfulness
            # Convert strength of negative evidence to a low truth score
            neg_strength = min(0.95, 0.65 + (negative_signals * 0.1))
            evidence_strength = 1.0 - neg_strength
            verdict = "False"
    elif neutral_signals > 0:
        evidence_strength = min(0.55, 0.40 + (neutral_signals * 0.05))
        verdict = "Unverified"
    else:
        evidence_strength = 0.4
        verdict = "Unverified"

    return VerificationResult(
        verdict=verdict,
        confidence=max(0.0, min(evidence_strength, 0.99)),
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
