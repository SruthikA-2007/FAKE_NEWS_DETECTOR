from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, status

from models.request_model import AnalyzeRequest
from models.response_model import AnalysisResponse, ClaimResult
from services.article_parser import parse_article
from services.claim_extractor import extract_claims
from services.ner_processor import extract_entities
from services.scorer import calculate_overall_score
from services.verifier import verify_claim

router = APIRouter(prefix="/analyze", tags=["analysis"])


@router.post("", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest) -> AnalysisResponse:
    try:
        article_text = await parse_article(request)
        if not article_text.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The provided content could not be parsed into text.",
            )

        extracted_claims = await extract_claims(article_text)
        if not extracted_claims:
            extracted_claims = [article_text.strip()]

        entities_per_claim = await asyncio.gather(*(extract_entities(claim) for claim in extracted_claims))
        verification_results = await asyncio.gather(
            *(verify_claim(claim, entities) for claim, entities in zip(extracted_claims, entities_per_claim))
        )

        claim_results = [
            ClaimResult(
                text=claim,
                verdict=result.verdict,
                confidence=result.confidence,
                sources=result.sources,
            )
            for claim, result in zip(extracted_claims, verification_results)
        ]

        overall_score = calculate_overall_score(claim_results)
        return AnalysisResponse(claims=claim_results, overall_score=overall_score)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc
