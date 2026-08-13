"""Polled state tracking API for the Company Intelligence Platform V5.0.

Returns the latest persisted state for a given ``run_id`` from DynamoDB
so the React frontend can render progress and final report references.
"""

from __future__ import annotations

import json
import logging
import os
from decimal import Decimal
from typing import Any

import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUN_STATE_TABLE = os.environ["RUN_STATE_TABLE"]

_ddb = boto3.resource("dynamodb")
_run_state = _ddb.Table(RUN_STATE_TABLE)


def _json_default(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value % 1 == 0 else float(value)
    raise TypeError(f"Unserializable type: {type(value)}")


def _response(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(body, default=_json_default),
    }


def handler(event: dict[str, Any], _context: Any) -> dict[str, Any]:
    path_params = event.get("pathParameters") or {}
    run_id = path_params.get("runId")
    if not run_id:
        return _response(400, {"error": "missing_run_id"})

    try:
        item = _run_state.get_item(Key={"run_id": run_id}).get("Item")
    except Exception as exc:  # pragma: no cover
        logger.exception("DynamoDB lookup failed for run %s", run_id)
        return _response(500, {"error": "lookup_failed", "details": str(exc)})

    if not item:
        return _response(404, {"error": "not_found", "run_id": run_id})

    return _response(200, item)
