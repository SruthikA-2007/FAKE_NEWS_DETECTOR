
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env explicitly
load_dotenv()

from services.verifier import verify_claim

async def test_live_apis():
    print("Testing Live APIs with Truthfulness Scoring...\n")
    
    # Test 1: Known True Fact
    true_claim = "The Great Wall of China is in China"
    print(f"Checking TRUE claim: '{true_claim}'")
    result_true = await verify_claim(true_claim, [])
    print(f"  Verdict: {result_true.verdict}")
    print(f"  Confidence: {result_true.confidence:.2f} ({int(result_true.confidence*100)}%)")
    print(f"  Sources found: {len(result_true.sources)}")
    print("-" * 30)

    # Test 2: Known Misinformation
    false_claim = "The Great Wall of China is in Brazil"
    print(f"Checking FALSE claim: '{false_claim}'")
    result_false = await verify_claim(false_claim, [])
    print(f"  Verdict: {result_false.verdict}")
    print(f"  Confidence: {result_false.confidence:.2f} ({int(result_false.confidence*100)}%)")
    print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_live_apis())
