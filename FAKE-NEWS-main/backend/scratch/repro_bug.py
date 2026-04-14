
import asyncio
import sys
import os

# Add parent directory to sys.path to import services
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.verifier import _score_evidence

def test_scoring():
    # Scenario: User says everything is 79% TRUE
    # Let's try to find inputs that produce 0.79 confidence and LIKELY TRUE verdict
    
    cases = [
        {
            "name": "Single positive (2 sigs) and no neutral",
            "fc": [{"rating": "True"}],
            "wiki": [],
            "news": []
        },
        {
            "name": "One positive match in FactCheck",
            "fc": [{"title": "Verified: Some claim is True"}],
            "wiki": [],
            "news": []
        },
        {
            "name": "Wikipedia neutral results",
            "fc": [],
            "wiki": [{"snippet": "Some info"}],
            "news": []
        }
    ]
    
    for case in cases:
        result = _score_evidence(case["fc"], case["wiki"], case["news"])
        print(f"Case: {case['name']}")
        print(f"  Verdict: {result.verdict}")
        print(f"  Confidence: {result.confidence}")
        print("-" * 20)

if __name__ == "__main__":
    test_scoring()
