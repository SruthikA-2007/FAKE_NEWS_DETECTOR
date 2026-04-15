from __future__ import annotations

from collections.abc import Sequence

from models.response_model import ClaimResult


def calculate_overall_score(claims: Sequence[ClaimResult]) -> int:
    """
    Calculate overall credibility score with penalties for strong negative verdicts.
    
    Scoring logic:
    - False claims: heavily weighted (0.05 confidence)
    - Misleading claims: moderate weight (0.35 confidence)
    - Unverified claims: default weight (0.25 confidence)
    - True claims: full confidence weight (0.95 confidence)
    
    Then average with multiplier for false claims found.
    """
    if not claims:
        return 0

    # Weight verdicts to penalize false claims more heavily
    total_confidence = 0.0
    false_claim_count = 0
    
    for claim in claims:
        if claim.verdict == "False":
            # Heavily penalize false claims
            total_confidence += max(0.05, claim.confidence * 0.1)
            false_claim_count += 1
        elif claim.verdict == "Misleading":
            # Moderate penalty for misleading
            total_confidence += claim.confidence * 0.5
        else:
            # Normal weight for True and Unverified
            total_confidence += claim.confidence

    average_confidence = total_confidence / len(claims)
    
    # Apply penalty multiplier based on false claims found
    if false_claim_count > 0:
        # Each false claim reduces overall score by 15%
        penalty = 1.0 - (false_claim_count * 0.15)
        average_confidence *= max(0.0, penalty)
    
    return max(0, min(100, int(round(average_confidence * 100))))
