
import asyncio
import sys
import os

# Add parent directory to sys.path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.verifier import _score_evidence

def test_scoring():
    cases = [
        {
            "name": "Verified True claim",
            "fc": [{"rating": "True"}],
            "wiki": [],
            "news": []
        },
        {
            "name": "Claim with 'untrue' rating (should be False, not True)",
            "fc": [{"rating": "This is untrue"}],
            "wiki": [],
            "news": []
        },
        {
            "name": "Claim with 'false' rating",
            "fc": [{"rating": "False"}],
            "wiki": [],
            "news": []
        },
        {
            "name": "Wikipedia neutral results (Unverified)",
            "fc": [],
            "wiki": [{"snippet": "Some info about the topic"}],
            "news": []
        },
        {
            "name": "Mixed signals (Misleading)",
            "fc": [{"rating": "True"}, {"rating": "False"}],
            "wiki": [],
            "news": []
        }
    ]
    
    for case in cases:
        result = _score_evidence(case["fc"], case["wiki"], case["news"])
        print(f"Case: {case['name']}")
        print(f"  Verdict: {result.verdict}")
        print(f"  Confidence Score: {result.confidence:.2f} ({int(result.confidence*100)}%)")
        print("-" * 20)

if __name__ == "__main__":
    test_scoring()
