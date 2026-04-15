from __future__ import annotations

import asyncio
import logging
import re
from functools import lru_cache

import spacy

logger = logging.getLogger(__name__)

ENTITY_LABELS = {"PERSON", "ORG", "DATE", "MONEY", "GPE", "LOC"}

LABEL_MAP = {
    "PERSON": "person",
    "ORG": "org",
    "DATE": "date",
    "MONEY": "money",
    "GPE": "org",
    "LOC": "org"
}


@lru_cache(maxsize=1)
def _load_model():
    try:
        return spacy.load("en_core_web_sm")
    except Exception:
        logger.info("spaCy model en_core_web_sm is unavailable; using rule-based fallback extraction.")
        return spacy.blank("en")


def _extract_entities_rule_based(text: str) -> list[dict[str, str]]:
    entities: list[dict[str, str]] = []
    seen: set[str] = set()

    # Simple date patterns (e.g., 12/05/2026, 2026-04-15, April 15, 2026)
    date_patterns = [
        r"\b\d{1,2}/\d{1,2}/\d{2,4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{2,4}\b",
    ]

    # Currency patterns (e.g., $10M, USD 5000)
    money_patterns = [
        r"\$\s?\d+(?:,\d{3})*(?:\.\d+)?(?:\s?[KMB])?\b",
        r"\b(?:USD|EUR|INR|GBP)\s?\d+(?:,\d{3})*(?:\.\d+)?\b",
    ]

    def _append_entity(value: str, entity_type: str) -> None:
        normalized = value.strip()
        if not normalized:
            return
        key = normalized.lower()
        if key in seen:
            return
        seen.add(key)
        entities.append({"text": normalized, "type": entity_type})

    for pattern in date_patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            _append_entity(match, "date")

    for pattern in money_patterns:
        for match in re.findall(pattern, text, flags=re.IGNORECASE):
            _append_entity(match, "money")

    # Approximate proper noun phrases as organization/person signals.
    for match in re.findall(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}\b", text):
        tokens = match.split()
        if len(tokens) >= 2:
            entity_type = "person"
        else:
            entity_type = "org"
        _append_entity(match, entity_type)

    return entities


def _extract_entities_sync(text: str) -> list[dict[str, str]]:
    nlp = _load_model()
    doc = nlp(text)
    entities: list[dict[str, str]] = []
    seen: set[str] = set()

    if not getattr(doc, "ents", None):
        return _extract_entities_rule_based(text)

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
        entities.append({
            "text": normalized,
            "type": LABEL_MAP.get(entity.label_, "org")
        })

    return entities


async def extract_entities(text: str) -> list[dict[str, str]]:
    if not text.strip():
        return []
    return await asyncio.to_thread(_extract_entities_sync, text)
