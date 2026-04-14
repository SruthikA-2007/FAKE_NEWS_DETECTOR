from __future__ import annotations

from typing import Any

import httpx

from config import settings


FACT_CHECK_ENDPOINT = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
WIKIPEDIA_SEARCH_ENDPOINT = "https://en.wikipedia.org/w/api.php"
NEWS_API_ENDPOINT = "https://newsapi.org/v2/everything"


async def fetch_json(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> dict[str, Any]:
    try:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}
    except (httpx.HTTPError, ValueError):
        return {}


async def query_fact_check(client: httpx.AsyncClient, query: str) -> list[dict[str, str]]:
    if not settings.factcheck_api_key:
        return []

    payload = await fetch_json(
        client,
        FACT_CHECK_ENDPOINT,
        params={
            "query": query,
            "pageSize": 5,
            "key": settings.factcheck_api_key,
        },
    )

    results: list[dict[str, str]] = []
    for item in payload.get("claims", [])[:5]:
        reviews = item.get("claimReview") or []
        if not reviews:
            continue
        review = reviews[0]
        results.append(
            {
                "source": review.get("publisher", {}).get("name", "Google Fact Check"),
                "rating": str(review.get("textualRating", "")),
                "url": str(review.get("url", "")),
                "title": str(review.get("title", "")),
            }
        )
    return results


async def query_wikipedia(client: httpx.AsyncClient, query: str) -> list[dict[str, str]]:
    payload = await fetch_json(
        client,
        WIKIPEDIA_SEARCH_ENDPOINT,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "origin": "*",
            "srlimit": 3,
        },
    )

    results: list[dict[str, str]] = []
    for item in payload.get("query", {}).get("search", [])[:3]:
        title = str(item.get("title", ""))
        if not title:
            continue
        results.append(
            {
                "source": "Wikipedia",
                "title": title,
                "snippet": str(item.get("snippet", "")),
                "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}",
            }
        )
    return results


async def query_news(client: httpx.AsyncClient, query: str) -> list[dict[str, str]]:
    if not settings.news_api_key:
        return []

    payload = await fetch_json(
        client,
        NEWS_API_ENDPOINT,
        params={
            "q": query,
            "language": "en",
            "pageSize": 5,
            "apiKey": settings.news_api_key,
        },
    )

    results: list[dict[str, str]] = []
    for item in payload.get("articles", [])[:5]:
        title = str(item.get("title", ""))
        if not title:
            continue
        results.append(
            {
                "source": str((item.get("source") or {}).get("name", "NewsAPI")),
                "title": title,
                "description": str(item.get("description", "")),
                "url": str(item.get("url", "")),
            }
        )
    return results
