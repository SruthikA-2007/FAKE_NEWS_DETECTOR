
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
    
    # Test 3: Known Misinformation with high likelihood of being in Fact Check API
    fake_news = "Drinking bleach cures Covid-19"
    print(f"Checking FAKE claim: '{fake_news}'")
    result = await verify_claim(fake_news, [])
    print(f"  Verdict: {result.verdict}")
    print(f"  Confidence: {result.confidence:.2f} ({int(result.confidence*100)}%)")
    print(f"  Sources found: {len(result.sources)}")
    for s in result.sources[:3]:
        print(f"    - {s}")
    print("-" * 30)

if __name__ == "__main__":
    asyncio.run(test_live_apis())
