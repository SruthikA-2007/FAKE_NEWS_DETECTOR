
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load .env explicitly
load_dotenv()

from services.verifier import verify_claim

async def check_news(claim):
    print(f"Checking claim: '{claim}'")
    result = await verify_claim(claim, [])
    print(f"  Verdict: {result.verdict}")
    print(f"  Confidence: {result.confidence:.2f} ({int(result.confidence*100)}%)")
    print(f"  Positive Signals logic check: {result.verdict == 'True'}")
    print("-" * 30)

async def main():
    # Known True
    await check_news("The capital of France is Paris")
    # Known False
    await check_news("The moon is made of green cheese")
    # Known Misleading/Common Fake
    await check_news("Drinking bleach cures Covid-19")

if __name__ == "__main__":
    asyncio.run(main())
