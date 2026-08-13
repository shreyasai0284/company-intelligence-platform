"""Report retrieval API for the Company Intelligence Platform V5.0.

Fetches persisted report artifacts from the local reports directory and returns them to the caller.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def _reports_dir() -> Path:
    return Path(os.environ.get("REPORTS_DIR", "./reports"))


def _json_default(value: Any) -> Any:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    raise TypeError(f"Unserializable type: {type(value)}")


def _response(status: int, body: dict[str, Any] | str) -> dict[str, Any]:
    if isinstance(body, str):
        body = {"message": body}
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

    report_path = _reports_dir() / f"{run_id}.json"

    try:
        artifact_body = report_path.read_text(encoding="utf-8")
        artifact = json.loads(artifact_body)
        return _response(200, artifact)
    except FileNotFoundError:
        return _response(404, {"error": "not_found", "run_id": run_id})
    except json.JSONDecodeError as exc:  # pragma: no cover
        logger.exception("Report artifact decode failed for %s", run_id)
        return _response(500, {"error": "artifact_corrupted", "details": str(exc)})
    except Exception as exc:  # pragma: no cover
        logger.exception("Report retrieval failed for %s", run_id)
        return _response(500, {"error": "retrieval_failed", "details": str(exc)})
