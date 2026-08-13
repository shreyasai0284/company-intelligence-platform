"""Impact scoring utilities for ranking company news and legal developments."""

from __future__ import annotations

from typing import Any, Iterable


NEGATIVE_SIGNAL_WEIGHTS: dict[str, int] = {
    "lawsuit": 6,
    "litigation": 6,
    "probe": 6,
    "investigation": 6,
    "recall": 5,
    "fraud": 6,
    "antitrust": 6,
    "penalty": 5,
    "fine": 5,
    "breach": 5,
    "shutdown": 5,
    "bankruptcy": 7,
    "default": 7,
    "downgrade": 4,
    "layoff": 4,
    "layoffs": 4,
    "delay": 3,
    "decline": 3,
    "drop": 3,
    "fall": 3,
    "miss": 4,
    "misses": 4,
    "warning": 3,
    "warn": 3,
    "sues": 5,
    "sued": 5,
    "charged": 6,
    "charges": 6,
    "settlement": 4,
    "injunction": 5,
    "scrutiny": 4,
    "pressure": 3,
}

IMPORTANT_SIGNAL_WEIGHTS: dict[str, int] = {
    "sec": 5,
    "doj": 5,
    "fda": 5,
    "epa": 5,
    "ftc": 5,
    "regulator": 5,
    "regulatory": 5,
    "guidance": 3,
    "restatement": 5,
    "class action": 6,
    "ceo": 3,
    "cfo": 3,
    "resignation": 4,
    "suspension": 4,
    "sanction": 5,
    "court": 4,
}

POSITIVE_SIGNAL_WEIGHTS: dict[str, int] = {
    "growth": 2,
    "expansion": 2,
    "launch": 2,
    "opens": 2,
    "opening": 2,
    "partnership": 2,
    "contract": 2,
    "approval": 3,
    "profit": 2,
    "beats": 3,
    "beat": 3,
    "upgrade": 2,
    "record": 2,
    "strong demand": 2,
    "raises": 2,
}

SEVERITY_LABELS: tuple[tuple[int, str], ...] = (
    (12, "critical"),
    (8, "high"),
    (4, "moderate"),
    (0, "low"),
)


def _collect_signal_hits(text: str, weights: dict[str, int]) -> tuple[int, list[str]]:
    lowered = text.lower()
    score = 0
    hits: list[str] = []
    for phrase, weight in weights.items():
        if phrase in lowered:
            score += weight
            hits.append(phrase)
    return score, hits


def _severity(score: int) -> str:
    for minimum, label in SEVERITY_LABELS:
        if score >= minimum:
            return label
    return "low"


def classify_text_item(text: str, *, domain: str) -> dict[str, Any]:
    negative_score, negative_hits = _collect_signal_hits(text, NEGATIVE_SIGNAL_WEIGHTS)
    important_score, important_hits = _collect_signal_hits(text, IMPORTANT_SIGNAL_WEIGHTS)
    positive_score, positive_hits = _collect_signal_hits(text, POSITIVE_SIGNAL_WEIGHTS)

    impact_score = negative_score + important_score + positive_score
    signed_score = positive_score - (negative_score + important_score)

    if domain == "litigation":
        impact_score += 4
        signed_score -= 4

    if negative_score or important_score or domain == "litigation":
        polarity = "negative"
    elif positive_score:
        polarity = "positive"
    else:
        polarity = "neutral"

    material_threshold = 5 if domain == "news" else 6
    is_material = impact_score >= material_threshold and polarity != "positive"
    sort_score = impact_score + (6 if polarity == "negative" else 0)

    return {
        "text": text,
        "domain": domain,
        "impact_score": impact_score,
        "signed_score": signed_score,
        "sort_score": sort_score,
        "polarity": polarity,
        "material": is_material,
        "severity": _severity(impact_score),
        "reasons": [*negative_hits, *important_hits, *positive_hits],
    }


def rank_text_items(items: Iterable[str], *, domain: str) -> list[dict[str, Any]]:
    ranked = [classify_text_item(item, domain=domain) for item in items if item]
    polarity_order = {"negative": 0, "neutral": 1, "positive": 2}
    ranked.sort(
        key=lambda item: (
            0 if item["material"] else 1,
            polarity_order.get(item["polarity"], 3),
            -item["sort_score"],
            item["text"],
        )
    )
    return ranked


def sentiment_from_ranked_items(items: Iterable[dict[str, Any]]) -> float:
    ranked = list(items)
    if not ranked:
        return 0.0

    total = 0.0
    for item in ranked:
        normalized = min(item.get("impact_score", 0), 12) / 12
        polarity = item.get("polarity")
        if polarity == "negative":
            total -= normalized
        elif polarity == "positive":
            total += normalized

    return round(total / len(ranked), 2)