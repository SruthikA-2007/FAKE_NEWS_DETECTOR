from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal["True", "False", "Unverified", "Misleading"]


class ClaimResult(BaseModel):
    text: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    claims: list[ClaimResult] = Field(default_factory=list)
    overall_score: int = Field(ge=0, le=100)
    article_text: str = ""
    entities: list[dict[str, str]] = Field(default_factory=list)
