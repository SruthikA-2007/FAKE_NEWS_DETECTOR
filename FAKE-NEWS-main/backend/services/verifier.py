from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field

import google.generativeai as genai
import httpx

from config import settings
from models.response_model import Verdict
from utils.api_clients import query_fact_check, query_news, query_wikipedia

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class VerificationResult:
    verdict: Verdict
    confidence: float
    sources: list[str] = field(default_factory=list)
    reasoning: str | None = None


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
        r"\bdebunked\b",
        r"\bdisproven\b",
        r"\bmisinformation\b",
        r"\bdisinformation\b",
        r"\bfalsehood\b",
        r"\brumor\b",
        r"\bconspiracy\b",
        r"\bunverified\b",
        r"\brefuted\b",
    ]
    return any(re.search(pattern, lowered) for pattern in negative_patterns)


def _get_source_credibility_weight(source_name: str) -> float:
    """Return confidence multiplier based on source type (higher = more trustworthy)."""
    lowered = source_name.lower()
    if "fact" in lowered or "snopes" in lowered or "politifact" in lowered:
        return 1.5  # Fact-checking sources are most reliable
    elif "wikipedia" in lowered:
        return 1.2  # Wikipedia is fairly reliable
    elif "news" in lowered or "api" in lowered:
        return 0.9  # General news sources are less reliable
    return 1.0


def _detect_misinformation_indicators(text: str) -> int:
    """Detect strong misinformation indicators in text."""
    lowered = text.lower()
    misinformation_keywords = [
        "claim", "alleged", "supposedly", "reportedly", "unconfirmed",
        "viral", "conspiracy theory", "not verified", "without evidence",
        "spreading online", "social media rumor", "debunked claim"
    ]
    return sum(1 for keyword in misinformation_keywords if keyword in lowered)


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


def _ai_score_evidence(
    claim: str,
    fact_check_results: list[dict[str, str]],
    wikipedia_results: list[dict[str, str]],
    news_results: list[dict[str, str]],
) -> VerificationResult | None:
    if not settings.gemini_api_key:
        return None

    try:
        genai.configure(api_key=settings.gemini_api_key)
        model = genai.GenerativeModel(settings.gemini_model)

        evidence_block = "EVIDENCE COLLECTED:\n"
        if fact_check_results:
            evidence_block += "\n--- Fact Check Results ---\n"
            for r in fact_check_results:
                evidence_block += f"- Source: {r.get('source')} | Title: {r.get('title')} | Rating: {r.get('rating')}\n"
        
        if wikipedia_results:
            evidence_block += "\n--- Wikipedia Snippets ---\n"
            for r in wikipedia_results:
                evidence_block += f"- Title: {r.get('title')} | Snippet: {r.get('snippet')}\n"
        
        if news_results:
            evidence_block += "\n--- News Articles ---\n"
            for r in news_results:
                evidence_block += f"- Source: {r.get('source')} | Title: {r.get('title')} | Description: {r.get('description')}\n"

        prompt = (
            "You are a professional fact-checker. Analyze the following claim against the provided evidence. "
            "Determine the truthfulness verdict (True, False, Misleading, or Unverified) and a confidence score (0.0 to 1.0). "
            "A True claim should have a high confidence score (0.7-1.0). "
            "A False claim should have a low confidence score representing its truth value (0.0-0.3). "
            "Return ONLY valid JSON as a single object with 'verdict', 'confidence', 'reasoning', and 'sources' (list of relevant URLs or names from the evidence). "
            "Do not wrap in markdown.\n\n"
            f"CLAIM: {claim}\n\n"
            f"{evidence_block}"
        )

        response = model.generate_content(
            prompt,
            generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
        )
        
        # Extract text robustly
        response_text = ""
        if hasattr(response, "text"):
            response_text = response.text
        elif hasattr(response, "candidates") and response.candidates:
            parts = response.candidates[0].content.parts
            if parts:
                response_text = parts[0].text
        
        if not response_text:
            return None

        data = json.loads(response_text)
        return VerificationResult(
            verdict=data.get("verdict", "Unverified"),
            confidence=max(0.0, min(float(data.get("confidence", 0.4)), 1.0)),
            sources=data.get("sources", []),
            reasoning=data.get("reasoning"),
        )
    except Exception as exc:
        logger.exception("AI evidence scoring failed: %s", exc)
        return None


def _score_evidence(
    claim: str,
    fact_check_results: list[dict[str, str]],
    wikipedia_results: list[dict[str, str]],
    news_results: list[dict[str, str]],
) -> VerificationResult:
    # 1. Try AI Scoring first
    ai_res = _ai_score_evidence(claim, fact_check_results, wikipedia_results, news_results)
    if ai_res:
        # Deduplicate sources gathered by AI and ensure they are clean
        ai_res.sources = _deduplicate_sources(ai_res.sources + [r.get("url") for r in fact_check_results + wikipedia_results + news_results if r.get("url")])
        return ai_res

    # 2. Fallback to Keyword-Based Scoring
    sources: list[str] = []
    positive_signals = 0
    negative_signals = 0
    neutral_signals = 0
    total_sources = 0

    # Process fact-check results (highest credibility)
    for result in fact_check_results:
        source_name = result.get("source", "Google Fact Check")
        title = result.get("title", "")
        rating = result.get("rating", "")
        url = result.get("url", "")
        credibility_weight = _get_source_credibility_weight(source_name)

        if title:
            sources.append(f"{source_name}: {title}")
        elif rating:
            sources.append(f"{source_name}: {rating}")
        if url:
            sources.append(url)

        total_sources += 1

        if _contains_positive_rating(title) or _contains_positive_rating(rating):
            positive_signals += int(2 * credibility_weight)
        if _contains_negative_rating(title) or _contains_negative_rating(rating):
            negative_signals += int(2 * credibility_weight)

    # Process Wikipedia results
    for result in wikipedia_results:
        title = result.get("title", "")
        url = result.get("url", "")
        snippet = result.get("snippet", "")
        credibility_weight = _get_source_credibility_weight("Wikipedia")

        if title:
            sources.append(f"Wikipedia: {title}")
        if url:
            sources.append(url)

        total_sources += 1

        if snippet:
            lowered = snippet.lower()
            misinformation_indicators = _detect_misinformation_indicators(snippet)

            if any(w in lowered for w in ["hoax", "fake", "false", "misinformation", "disputed", "conspiracy", "rumor", "debunked", "unverified"]):
                negative_signals += int((1 + misinformation_indicators * 0.5) * credibility_weight)
            else:
                neutral_signals += int(1 * credibility_weight)

    # Process news results (lower credibility)
    for result in news_results:
        title = result.get("title", "")
        url = result.get("url", "")
        source_name = result.get("source", "NewsAPI")
        description = result.get("description", "")
        credibility_weight = _get_source_credibility_weight(source_name)

        if title:
            sources.append(f"{source_name}: {title}")
        if url:
            sources.append(url)

        total_sources += 1

        if title or url:
            lowered = f"{title} {description}".lower()
            misinformation_indicators = _detect_misinformation_indicators(lowered)

            if any(w in lowered for w in ["hoax", "fake", "false", "misinformation", "disputed", "conspiracy", "rumor", "debunked", "unverified"]):
                negative_signals += int((1 + misinformation_indicators * 0.5) * credibility_weight)
            else:
                neutral_signals += int(1 * credibility_weight)

    # New optimized scoring logic
    evidence_strength = 0.25  # Default: pessimistic for unverified claims
    verdict: Verdict = "Unverified"
    
    # Apply source count multiplier (more sources = higher confidence)
    source_multiplier = min(1.2, 0.8 + (total_sources * 0.1))

    if positive_signals > 0 and negative_signals == 0:
        # All positive evidence: mark as True
        evidence_strength = min(0.95, (0.70 + (positive_signals * 0.08) + (neutral_signals * 0.02)) * source_multiplier)
        verdict = "True"
    elif negative_signals > 0:
        if positive_signals > 0:
            # Mixed signals: mark as Misleading with low confidence
            evidence_strength = 0.35
            verdict = "Misleading"
        else:
            # Strong negative evidence: mark as False with high confidence
            neg_strength = min(0.95, 0.70 + (negative_signals * 0.08))
            evidence_strength = max(0.05, 1.0 - neg_strength)
            verdict = "False"
    elif neutral_signals > 0:
        # Only neutral signals: slightly above default unverified
        evidence_strength = min(0.45, 0.25 + (neutral_signals * 0.04))
        verdict = "Unverified"
    else:
        # No evidence found: very low confidence for unverified
        evidence_strength = 0.20  # Reduced from 0.4 to be more pessimistic
        verdict = "Unverified"

    return VerificationResult(
        verdict=verdict,
        confidence=max(0.0, min(evidence_strength, 0.99)),
        sources=_deduplicate_sources(sources),
        reasoning="Based on keyword presence in search results. (AI scoring unavailable)"
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

    return _score_evidence(claim, fact_check_results, wikipedia_results, news_results)
