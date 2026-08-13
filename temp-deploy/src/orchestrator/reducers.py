"""Custom dictionary reducers powering the synchronization barrier.

LangGraph applies reducers to merge parallel branch outputs into the
shared :class:`OrchestratorState`. The agent-result reducer guarantees
that all five branches resolve before the synthesis node fires.
"""

from __future__ import annotations
from typing import Any

REQUIRED_AGENTS: tuple[str, ...] = (
    "research",
    "news",
    "litigation",
    "leadership",
    "financial",
)

def merge_agent_dict(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge an individual agent's dictionary output without mutating values."""
    if not existing:
        return dict(incoming or {})

    merged = dict(existing)
    for key, value in (incoming or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_agent_dict(merged[key], value)
        else:
            merged[key] = value
    return merged


def merge_metrics(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    """Combine telemetry maps additively without dropping prior values."""
    out = dict(existing or {})
    for key, value in (incoming or {}).items():
        if isinstance(value, dict):
            out[key] = {**(out.get(key) or {}), **value}
        else:
            out[key] = value
    return out


def append_errors(existing: list[dict[str, Any]], incoming: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [*(existing or []), *(incoming or [])]


def all_agents_resolved(state: dict[str, Any]) -> bool:
    """Synchronization barrier predicate — all five branches must publish data."""
    return all(bool(state.get(agent)) for agent in REQUIRED_AGENTS)