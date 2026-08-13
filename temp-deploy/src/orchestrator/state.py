from __future__ import annotations

from typing import Any, Literal, Annotated
from pydantic import BaseModel, Field
from .reducers import merge_agent_dict, merge_metrics, append_errors


class ExecutionMetrics(BaseModel):
    """Lightweight per-run telemetry."""

    started_at: float = 0.0
    finished_at: float = 0.0
    agent_latencies_ms: dict[str, float] = Field(default_factory=dict)
    cache_hits: dict[str, bool] = Field(default_factory=dict)
    retries: dict[str, int] = Field(default_factory=dict)


class OrchestratorState(BaseModel):
    """Master state object reduced across the LangGraph fan-out/fan-in."""

    # Inbound Configuration Elements
    run_id: str
    company: str
    country: str
    tier: Literal["Standard", "Premium"]

    # Per-agent dictionary outputs (populated by state nodes)
    research: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)
    news: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)
    litigation: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)
    leadership: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)
    financial: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)

    # Downstream Synthesis Products
    validated: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)
    synthesized: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)
    report: Annotated[dict[str, Any], merge_agent_dict] = Field(default_factory=dict)

    # Telemetry Control Plane
    metrics: Annotated[ExecutionMetrics, merge_metrics] = Field(default_factory=ExecutionMetrics)
    errors: Annotated[list[dict[str, Any]], append_errors] = Field(default_factory=list)