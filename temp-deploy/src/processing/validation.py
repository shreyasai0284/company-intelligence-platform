"""Structural validation with Amazon Nova Micro self-correction loops."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from pydantic import AliasChoices, BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

BEDROCK_REGION = os.environ.get(
    "BEDROCK_REGION",
    os.environ.get("AWS_REGION", os.environ.get("AWS_DEFAULT_REGION", "ap-south-1")),
)
NOVA_MICRO_MODEL_ID = os.environ.get(
    "NOVA_MICRO_MODEL_ID",
    os.environ.get("NOVA_MICRO_INFERENCE_PROFILE_ID", "apac.amazon.nova-micro-v1:0"),
)
MAX_CORRECTION_ROUNDS = int(os.environ.get("NOVA_VALIDATION_ROUNDS", "2"))


class AgentBundle(BaseModel):
    class ResearchProfile(BaseModel):
        summary: str = ""
        sources: list[Any] = Field(default_factory=list)

    class ResearchPayload(BaseModel):
        company: str = ""
        country: str = ""
        profile: "AgentBundle.ResearchProfile" = Field(default_factory=lambda: AgentBundle.ResearchProfile())
        cache_hit: bool = False

    class NewsPayload(BaseModel):
        company: str = ""
        articles: list[str] = Field(
            default_factory=list,
            validation_alias=AliasChoices("articles", "recent_headlines"),
        )
        sentiment_score: float = 0.0
        cache_hit: bool = False

    class LitigationPayload(BaseModel):
        company: str = ""
        active_count: int = 0
        cases: list[str] = Field(default_factory=list)
        cache_hit: bool = False

    class LeadershipPayload(BaseModel):
        company: str = ""
        executives: list[str] = Field(
            default_factory=list,
            validation_alias=AliasChoices("executives", "executives_updates"),
        )
        product_lines: list[str] = Field(
            default_factory=list,
            validation_alias=AliasChoices("product_lines", "product_lines_updates"),
        )
        cache_hit: bool = False

    class FinancialPayload(BaseModel):
        company: str = ""
        ticker: str = ""
        share_price: str = ""
        cagr_5y: float = 0.0
        corporate_brief: str = ""
        cache_hit: bool = False

    research: ResearchPayload = Field(default_factory=ResearchPayload)
    news: NewsPayload = Field(default_factory=NewsPayload)
    litigation: LitigationPayload = Field(default_factory=LitigationPayload)
    leadership: LeadershipPayload = Field(default_factory=LeadershipPayload)
    financial: FinancialPayload = Field(default_factory=FinancialPayload)


def _invoke_nova_micro(prompt: str) -> str:
    """Best-effort Nova Micro invocation. Falls back to identity in local dev."""
    try:  # pragma: no cover — requires Bedrock runtime credentials
        import boto3

        client = boto3.client("bedrock-runtime", region_name=BEDROCK_REGION)
        resp = client.invoke_model(
            modelId=NOVA_MICRO_MODEL_ID,
            body=json.dumps(
                {
                    "messages": [{"role": "user", "content": [{"text": prompt}]}],
                    "inferenceConfig": {"maxTokens": 1024, "temperature": 0.0},
                }
            ),
        )
        body = json.loads(resp["body"].read())
        return body["output"]["message"]["content"][0]["text"]
    except Exception as exc:
        logger.debug("Nova Micro unavailable, skipping correction: %s", exc)
        return prompt


def validate_payload(bundle: dict[str, Any]) -> dict[str, Any]:
    """Run structural validation with up to N Nova Micro correction rounds."""
    candidate = bundle
    last_error: str | None = None

    for round_idx in range(MAX_CORRECTION_ROUNDS + 1):
        try:
            validated = AgentBundle.model_validate(candidate)
            return validated.model_dump()
        except ValidationError as exc:
            last_error = str(exc)
            logger.info("Validation round %d failed: %s", round_idx, last_error)
            if round_idx == MAX_CORRECTION_ROUNDS:
                break
            corrected = _invoke_nova_micro(
                "You are a JSON repair assistant. Fix the following object so it conforms to the schema. "
                f"Schema errors:\n{last_error}\n\nObject:\n{json.dumps(candidate, default=str)}"
            )
            try:
                candidate = json.loads(corrected)
            except Exception:
                break

    return {"_validation_error": last_error or "unknown", "raw": bundle}
