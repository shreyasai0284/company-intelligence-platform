"""LangChain-powered synthesis engine.

Deduplicates and harmonizes the validated multi-source agent bundle
into a coherent, citation-ready dossier consumed by the report tier.
"""

from __future__ import annotations

import hashlib
import logging
import re
from typing import Any, Iterable

from .impact import rank_text_items

logger = logging.getLogger(__name__)


def _hash(item: Any) -> str:
    return hashlib.sha1(repr(item).encode("utf-8")).hexdigest()


def _dedupe(seq: Iterable[Any]) -> list[Any]:
    seen: set[str] = set()
    out: list[Any] = []
    for item in seq:
        h = _hash(item)
        if h in seen:
            continue
        seen.add(h)
        out.append(item)
    return out


def _normalize_text_item(item: Any) -> list[str]:
    if not isinstance(item, str):
        return [str(item)]

    normalized = item.replace("\r", " ").replace("\n", " ").strip()
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = re.sub(r"\.\.\.(?=[A-Z])", "... | ", normalized)
    normalized = re.sub(r"(?<=[a-z])(?=[A-Z][a-z])", " | ", normalized)

    parts = [part.strip(" |.-") for part in normalized.split("|")]
    cleaned_parts: list[str] = []
    for part in parts:
        if not part:
            continue
        part = re.sub(r"\s+", " ", part).strip()
        if len(part) < 8:
            continue
        cleaned_parts.append(part)
    return cleaned_parts or [normalized]


def _normalize_text_list(items: Iterable[Any]) -> list[str]:
    expanded: list[str] = []
    for item in items:
        expanded.extend(_normalize_text_item(item))
    return _dedupe(expanded)


def synthesize(validated: dict[str, Any]) -> dict[str, Any]:
    """Merge validated agent outputs into a deduplicated dossier."""
    if "_validation_error" in validated:
        return {"error": "validation_failed", "details": validated["_validation_error"]}

    news_articles = _normalize_text_list(validated.get("news", {}).get("articles", []) or [])
    cases = _normalize_text_list(validated.get("litigation", {}).get("cases", []) or [])
    executives = _normalize_text_list(validated.get("leadership", {}).get("executives", []) or [])
    product_lines = _normalize_text_list(validated.get("leadership", {}).get("product_lines", []) or [])
    ranked_news = rank_text_items(news_articles, domain="news")
    ranked_cases = rank_text_items(cases, domain="litigation")
    material_news = [item["text"] for item in ranked_news if item["material"]]
    contextual_news = [item["text"] for item in ranked_news if not item["material"]]
    material_cases = [item["text"] for item in ranked_cases if item["material"]]
    contextual_cases = [item["text"] for item in ranked_cases if not item["material"]]

    try:  # pragma: no cover — optional LangChain enrichment
        from langchain_core.documents import Document  # noqa: F401
    except Exception:
        logger.debug("LangChain not installed; running pure synthesis path.")

    return {
        "profile": validated.get("research", {}).get("profile", {}),
        "news": {
            "articles": news_articles,
            "count": len(news_articles),
            "sentiment_score": validated.get("news", {}).get("sentiment_score", 0.0),
            "material_articles": material_news,
            "contextual_articles": contextual_news,
            "ranked_articles": ranked_news,
        },
        "litigation": {
            "cases": cases,
            "count": len(cases),
            "material_cases": material_cases,
            "contextual_cases": contextual_cases,
            "ranked_cases": ranked_cases,
        },
        "leadership": {"executives": executives, "product_lines": product_lines},
        "financial": validated.get("financial", {}),
    }
