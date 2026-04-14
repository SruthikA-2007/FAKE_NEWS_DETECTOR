from __future__ import annotations

from collections.abc import Sequence

from models.response_model import ClaimResult


def calculate_overall_score(claims: Sequence[ClaimResult]) -> int:
    if not claims:
        return 0

    average_confidence = sum(claim.confidence for claim in claims) / len(claims)
    return max(0, min(100, int(round(average_confidence * 100))))
