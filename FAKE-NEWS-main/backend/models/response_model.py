from typing import Literal

from pydantic import BaseModel, Field


Verdict = Literal["True", "False", "Unverified", "Misleading"]


class MatchedArticle(BaseModel):
    title: str
    source: str
    url: str
    description: str | None = None
    snippet: str | None = None
    match_score: float = Field(ge=0.0, le=1.0)
    verdict_alignment: Literal["supporting", "contradicting", "neutral"] = "neutral"


class ClaimResult(BaseModel):
    text: str
    verdict: Verdict
    confidence: float = Field(ge=0.0, le=1.0)
    sources: list[str] = Field(default_factory=list)
    reasoning: str | None = None


class AnalysisResponse(BaseModel):
    claims: list[ClaimResult] = Field(default_factory=list)
    overall_score: int = Field(ge=0, le=100)
    credibility_level: Literal["very_likely_false", "possibly_false", "unverified", "partially_true", "mostly_true", "very_likely_true"] = "unverified"
    article_text: str = ""
    entities: list[dict[str, str]] = Field(default_factory=list)
    matched_articles: list[MatchedArticle] = Field(default_factory=list)
    verification_summary: str = ""
