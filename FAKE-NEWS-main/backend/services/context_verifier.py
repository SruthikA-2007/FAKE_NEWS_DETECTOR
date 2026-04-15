"""
Context-based verification: Extract key entities and article summary, then search for
corroborating sources and score based on coverage and source trust.
"""
from __future__ import annotations

import asyncio
import logging
import re
from collections import Counter

import httpx

from config import settings
from models.response_model import MatchedArticle, Verdict
from utils.api_clients import query_fact_check, query_news, query_wikipedia

logger = logging.getLogger(__name__)


TRUSTED_SOURCES = {
    "bbc": 1.0,
    "reuters": 1.0,
    "associated press": 1.0,
    "ap news": 1.0,
    "bloomberg": 0.95,
    "the guardian": 0.95,
    "the new york times": 0.95,
    "washington post": 0.95,
    "economist": 0.9,
    "financial times": 0.9,
    "wikipedia": 0.85,
    "npr": 0.9,
    "bbc news": 1.0,
    "cnn": 0.8,
    "foxnews": 0.75,
    "msnbc": 0.75,
}


def _get_source_trust_score(source_name: str) -> float:
    """Score between 0.0 (low trust) and 1.0 (high trust)."""
    lowered = source_name.lower()
    for trusted_source, score in TRUSTED_SOURCES.items():
        if trusted_source in lowered:
            return score
    return 0.5  # Default for unknown sources


def _tokenize_and_normalize(text: str) -> set[str]:
    """Convert text to lowercase tokens, filter noise."""
    text_lower = text.lower()
    tokens = re.findall(r"\b\w+\b", text_lower)
    stopwords = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
        "of", "with", "is", "are", "was", "were", "be", "been", "by", "from",
        "as", "that", "this", "it", "will", "would", "could", "should"
    }
    return {t for t in tokens if len(t) > 2 and t not in stopwords}


def _compute_keyword_overlap(article_text: str, matched_text: str) -> float:
    """Compute Jaccard similarity between article and matched text keywords."""
    article_tokens = _tokenize_and_normalize(article_text)
    matched_tokens = _tokenize_and_normalize(matched_text)

    if not article_tokens or not matched_tokens:
        return 0.0

    intersection = len(article_tokens & matched_tokens)
    union = len(article_tokens | matched_tokens)

    return intersection / union if union > 0 else 0.0


def _extract_article_summary(article_text: str, max_length: int = 500) -> str:
    """Extract key sentences from article for summary."""
    sentences = re.split(r"(?<=[.!?])\s+", article_text.strip())
    summary_sentences = []
    current_length = 0

    for sentence in sentences:
        if len(sentence) < 15:
            continue
        if current_length + len(sentence) > max_length:
            break
        summary_sentences.append(sentence)
        current_length += len(sentence)

    return " ".join(summary_sentences)


def _contains_misinformation_signal(text: str) -> bool:
    """Check if text contains strong misinformation indicators."""
    lowered = text.lower()
    bad_keywords = [
        "hoax", "fake", "fabricated", "debunked", "false",
        "misinformation", "disinformation", "unverified claim",
        "conspiracy theory", "not verified"
    ]
    return any(keyword in lowered for keyword in bad_keywords)


def _contains_truth_signal(text: str) -> bool:
    """Check if text contains truth/verification signals."""
    lowered = text.lower()
    good_keywords = [
        "confirmed", "verified", "official", "reported",
        "according to", "sources say", "fact-check", "true"
    ]
    return any(keyword in lowered for keyword in good_keywords)


async def find_corroborating_sources(
    article_text: str,
    entities: list[dict[str, str]],
) -> tuple[list[MatchedArticle], str, Verdict, float]:
    """
    Find articles corroborating the claim across trusted news sources and fact-checkers.
    
    Returns:
        - List of matched articles with alignment scores
        - Summary of verification findings
        - Verdict (True/False/Misleading/Unverified)
        - Overall confidence score
    """
    if not article_text.strip():
        return [], "No article content provided.", "Unverified", 0.0

    article_summary = _extract_article_summary(article_text)
    entity_names = [e.get("text", "") for e in entities if e.get("type") == "person"]
    entity_orgs = [e.get("text", "") for e in entities if e.get("type") in {"org", "loc"}]

    # Build search queries from entities
    search_queries = []
    if entity_names:
        search_queries.append(" AND ".join(entity_names[:2]))
    if entity_orgs:
        search_queries.append(" AND ".join(entity_orgs[:2]))
    search_queries.append(article_summary[:100])

    if not search_queries:
        search_queries = [article_summary[:100]]

    matched_articles: list[MatchedArticle] = []
    supporting_count = 0
    contradicting_count = 0
    neutral_count = 0
    total_trust_score = 0.0

    timeout = httpx.Timeout(settings.request_timeout_seconds)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        for query in search_queries:
            if not query.strip():
                continue

            try:
                # Fetch from multiple sources
                fact_check_results, wikipedia_results, news_results = await asyncio.gather(
                    query_fact_check(client, query),
                    query_wikipedia(client, query),
                    query_news(client, query),
                    return_exceptions=True,
                )

                # Process results
                for result in fact_check_results or []:
                    rating = (result.get("rating") or "").lower()
                    title = result.get("title") or result.get("source", "Fact Check")
                    url = result.get("url", "")

                    if not url:
                        continue

                    # Determine alignment
                    if _contains_misinformation_signal(rating):
                        alignment = "contradicting"
                        contradicting_count += 1
                    elif _contains_truth_signal(rating):
                        alignment = "supporting"
                        supporting_count += 1
                    else:
                        alignment = "neutral"
                        neutral_count += 1

                    trust = _get_source_trust_score(result.get("source", ""))
                    keyword_overlap = _compute_keyword_overlap(article_text, title)
                    match_score = (keyword_overlap * 0.6 + trust * 0.4)

                    matched_articles.append(
                        MatchedArticle(
                            title=title,
                            source=result.get("source", "Fact Check"),
                            url=url,
                            description=rating,
                            match_score=match_score,
                            verdict_alignment=alignment,
                        )
                    )
                    total_trust_score += trust

                for result in news_results or []:
                    title = result.get("title", "")
                    url = result.get("url", "")
                    source = result.get("source", "")
                    description = result.get("description", "")

                    if not url or not title:
                        continue

                    # Determine alignment from text
                    combined_text = f"{title} {description}".lower()
                    if _contains_misinformation_signal(combined_text):
                        alignment = "contradicting"
                        contradicting_count += 1
                    elif _contains_truth_signal(combined_text) or "report" in combined_text:
                        alignment = "supporting"
                        supporting_count += 1
                    else:
                        alignment = "neutral"
                        neutral_count += 1

                    trust = _get_source_trust_score(source)
                    keyword_overlap = _compute_keyword_overlap(article_text, f"{title} {description}")
                    match_score = (keyword_overlap * 0.6 + trust * 0.4)

                    if match_score > 0.3:  # Only include if reasonable overlap
                        matched_articles.append(
                            MatchedArticle(
                                title=title,
                                source=source,
                                url=url,
                                description=description,
                                match_score=match_score,
                                verdict_alignment=alignment,
                            )
                        )
                        total_trust_score += trust

            except Exception as exc:
                logger.warning("Error querying sources for '%s': %s", query[:50], exc)
                continue

    # Sort by match score
    matched_articles.sort(key=lambda x: x.match_score, reverse=True)
    matched_articles = matched_articles[:10]  # Keep top 10

    # Determine verdict and confidence based on coverage
    if not matched_articles:
        return (
            matched_articles,
            "No corroborating sources found. Cannot verify claim.",
            "Unverified",
            0.20,
        )

    total_matches = len(matched_articles)
    avg_trust = total_trust_score / total_matches if total_matches > 0 else 0.5

    # Score: if mostly supporting and high trust, mark as True
    if supporting_count > contradicting_count and supporting_count >= total_matches * 0.5:
        verdict = "True"
        confidence = min(0.95, 0.70 + (supporting_count / total_matches) * 0.2 + (avg_trust - 0.5))
        summary = f"Found {supporting_count} corroborating sources from trusted outlets. Article appears credible."
    elif contradicting_count > supporting_count and contradicting_count >= total_matches * 0.4:
        verdict = "False"
        confidence = max(0.05, 1.0 - (0.70 + (contradicting_count / total_matches) * 0.2 + (avg_trust - 0.5)))
        summary = f"Found {contradicting_count} sources contradicting this claim. Evidence suggests misinformation."
    elif supporting_count > 0 and contradicting_count > 0:
        verdict = "Misleading"
        confidence = 0.35
        summary = f"Found mixed evidence: {supporting_count} supporting vs {contradicting_count} contradicting sources."
    else:
        verdict = "Unverified"
        confidence = min(0.50, 0.25 + (neutral_count / total_matches) * 0.15)
        summary = f"Found {total_matches} sources but no strong indicators. Claim remains unverified."

    return matched_articles, summary, verdict, confidence
