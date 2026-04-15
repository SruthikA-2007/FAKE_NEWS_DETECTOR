from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, status

from models.request_model import AnalyzeRequest
from models.response_model import AnalysisResponse, ClaimResult
from services.article_parser import parse_article
from services.context_verifier import find_corroborating_sources
from services.ner_processor import extract_entities
from services.scorer import calculate_overall_score

router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.post("", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    try:
        article_text = await parse_article(request)
        if not article_text.strip():
            if request.type == "url":
                detail = "Could not extract text from the provided URL. Make sure the link is valid, public, and contains readable article text."
            elif request.type == "image":
                detail = "Could not extract text from the provided image payload. Please provide OCR text or use text/url input."
            else:
                detail = "The provided text input is empty after parsing."
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=detail,
            )

        # Extract entities for context-based verification
        article_entities = await extract_entities(article_text)

        # Use context-based verification instead of claim extraction
        matched_articles, verification_summary, verdict, confidence = await find_corroborating_sources(
            article_text,
            article_entities,
        )

        # Create single claim result for the full article
        claim_result = ClaimResult(
            text=article_text[:500] + ("..." if len(article_text) > 500 else ""),
            verdict=verdict,
            confidence=confidence,
            sources=[article.url for article in matched_articles if article.url],
            reasoning=verification_summary,
        )

        # Calculate overall score based on verification result
        overall_score = calculate_overall_score([claim_result])

        # Determine credibility level
        credibility_mapping = {
            0: "very_likely_false",
            10: "very_likely_false",
            20: "possibly_false",
            35: "possibly_false",
            50: "unverified",
            65: "partially_true",
            80: "mostly_true",
            100: "very_likely_true",
        }
        credibility_level = "unverified"
        for threshold in sorted(credibility_mapping.keys()):
            if overall_score >= threshold:
                credibility_level = credibility_mapping[threshold]

        return AnalysisResponse(
            claims=[claim_result],
            overall_score=overall_score,
            credibility_level=credibility_level,
            article_text=article_text.strip(),
            entities=article_entities,
            matched_articles=matched_articles,
            verification_summary=verification_summary,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc
