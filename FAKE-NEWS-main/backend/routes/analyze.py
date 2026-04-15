from __future__ import annotations

import asyncio

import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status

from models.request_model import AnalyzeRequest
from models.response_model import AnalysisResponse, ClaimResult
from services.article_parser import parse_article
from services.claim_extractor import extract_claims
from services.ner_processor import extract_entities
from services.scorer import calculate_overall_score
from services.verifier import verify_claim

router = APIRouter(prefix="/analyze", tags=["analysis"])


async def _parse_analyze_request(
    request: Request,
    type: str | None = Form(None),
    content: str | None = Form(None),
    file: UploadFile | None = File(None),
) -> AnalyzeRequest:
    content_type = request.headers.get("content-type", "")
    if content_type.startswith("multipart/form-data"):
        if not type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Missing 'type' field in multipart request.",
            )
        if type == "image":
            if not file:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Image upload requires a file in the 'file' field.",
                )
            image_bytes = await file.read()
            if not image_bytes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Uploaded image is empty.",
                )
            return AnalyzeRequest(type=type, content=base64.b64encode(image_bytes).decode("utf-8"))

        if not content or not content.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Text or URL input requires non-empty 'content'.",
            )
        return AnalyzeRequest(type=type, content=content.strip())

    body = await request.json()
    return AnalyzeRequest.model_validate(body)


@router.post("", response_model=AnalysisResponse)
async def analyze(request: AnalyzeRequest = Depends(_parse_analyze_request)) -> AnalysisResponse:
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

        article_entities = await extract_entities(article_text)
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
                reasoning=result.reasoning,
            )
            for claim, result in zip(extracted_claims, verification_results)
        ]

        overall_score = calculate_overall_score(claim_results)
        return AnalysisResponse(
            claims=claim_results,
            overall_score=overall_score,
            article_text=article_text.strip(),
            entities=article_entities,
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        ) from exc
