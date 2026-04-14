from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

import spacy

logger = logging.getLogger(__name__)

ENTITY_LABELS = {"PERSON", "ORG", "DATE", "MONEY", "GPE", "LOC"}


@lru_cache(maxsize=1)
def _load_model():
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        logger.warning("spaCy model en_core_web_sm is unavailable; using a blank English pipeline.")
        return spacy.blank("en")


def _extract_entities_sync(text: str) -> list[str]:
    nlp = _load_model()
    doc = nlp(text)
    entities: list[str] = []
    seen: set[str] = set()

    for entity in doc.ents:
        if entity.label_ not in ENTITY_LABELS:
            continue
        normalized = entity.text.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        entities.append(normalized)

    return entities


async def extract_entities(text: str) -> list[str]:
    if not text.strip():
        return []
    return await asyncio.to_thread(_extract_entities_sync, text)
