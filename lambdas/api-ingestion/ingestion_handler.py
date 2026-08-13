"""Asynchronous API gatekeeper for the Company Intelligence Platform V5.0.

Receives a JSON payload describing an intelligence run, generates a
cryptographically secure ``run_id``, persists initial state to DynamoDB,
publishes the validated packet onto an SQS FIFO queue, and returns an
HTTP 202 Accepted response to the React frontend so it can begin polling.
"""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from typing import Any, Literal

import boto3
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

INGESTION_QUEUE_URL = os.environ["INGESTION_QUEUE_URL"]
RUN_STATE_TABLE = os.environ["RUN_STATE_TABLE"]

_sqs = boto3.client("sqs")
_ddb = boto3.resource("dynamodb")
_run_state = _ddb.Table(RUN_STATE_TABLE)


class IngestionRequest(BaseModel):
    """Inbound schema validated before any downstream dispatch."""

    company: str = Field(min_length=1, max_length=256)
    country: str = Field(min_length=2, max_length=64)
    tier: Literal["Standard", "Premium"]


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body),
    }


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    """Lambda entrypoint bound to ``POST /ingest``."""
    try:
        raw = event.get("body") or "{}"
        if event.get("isBase64Encoded"):
            import base64

            raw = base64.b64decode(raw).decode("utf-8")
        payload = IngestionRequest.model_validate_json(raw)
    except ValidationError as exc:
        logger.warning("Invalid ingestion payload: %s", exc)
        return _response(400, {"error": "invalid_payload", "details": exc.errors()})
    except Exception as exc:  # pragma: no cover
        logger.exception("Malformed request envelope")
        return _response(400, {"error": "malformed_request", "details": str(exc)})

    # --- OPTION 1: THE PERMANENT NAME FIX ---
    # Strip whitespace, replace spaces/underscores with hyphens, and lowercase.
    # This prevents SQS ValidationExceptions and keeps data partitioning consistent.
    sanitized_company = payload.company.replace(" ", "-").replace("_", "-").strip().lower()
    sanitized_country = payload.country.replace(" ", "-").replace("_", "-").strip().lower()

    run_id = uuid.uuid4().hex
    now = int(time.time())

    # Use sanitized values for downstream processing
    message_body = {
        "run_id": run_id,
        "company": sanitized_company,
        "country": sanitized_country,
        "tier": payload.tier,
        "submitted_at": now,
    }

    try:
        _run_state.put_item(
            Item={
                "run_id": run_id,
                "status": "QUEUED",
                "company": sanitized_company,
                "country": sanitized_country,
                "tier": payload.tier,
                "created_at": now,
                "updated_at": now,
                "ttl": now + 60 * 60 * 24 * 7,
            }
        )

        # MessageGroupId is now fully safe from space-based string constraints
        _sqs.send_message(
            QueueUrl=INGESTION_QUEUE_URL,
            MessageBody=json.dumps(message_body),
            MessageGroupId=f"{sanitized_company}:{sanitized_country}",
            MessageDeduplicationId=run_id,
        )
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to dispatch run %s", run_id)
        return _response(500, {"error": "dispatch_failed", "details": str(exc)})

    logger.info("Accepted run_id=%s company=%s", run_id, sanitized_company)
    return _response(
        202,
        {
            "run_id": run_id,
            "status": "QUEUED",
            "poll_url": f"/status/{run_id}",
        },
    )