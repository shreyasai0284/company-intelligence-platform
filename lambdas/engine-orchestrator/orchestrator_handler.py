"""Background engine orchestrator for the Company Intelligence Platform V5.0.

Consumes sanitized messages from SQS, executes the Async Custom Parallel 
StateGraph orchestration pipeline, and updates execution tracking states.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
import boto3

# Add local source directories to path for imports
root_dir = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(root_dir, 'src'))

# Import the full orchestration graph
from orchestrator.graph import run_intelligence_pipeline

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUN_STATE_TABLE = os.environ["RUN_STATE_TABLE"]
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "./reports"))
_ddb = boto3.resource("dynamodb")
_run_state = _ddb.Table(RUN_STATE_TABLE)


def _persist_report_artifact(
    *,
    run_id: str,
    company: str | None,
    country: str,
    tier: str,
    graph_output: dict[str, Any],
    execution_duration: float,
) -> dict[str, str]:
    report = graph_output.get("report", {}) if isinstance(graph_output.get("report"), dict) else {}
    artifact = {
        "run_id": run_id,
        "company": company,
        "country": country,
        "tier": tier,
        "status": "COMPLETED",
        "generated_at": int(time.time()),
        "execution_time_seconds": execution_duration,
        "report": report,
        "metrics": graph_output.get("metrics", {}),
        "validated": graph_output.get("validated", {}),
        "synthesized": graph_output.get("synthesized", {}),
    }

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{run_id}.json"
    report_path.write_text(json.dumps(artifact, default=str), encoding="utf-8")
    return {
        "report_path": str(report_path),
        "report_url": f"file://{report_path}",
    }


def update_run_status(run_id: str, status: str, extra_attributes: dict[str, Any] | None = None) -> None:
    """Updates the runtime state token inside the tracking DynamoDB table."""
    now = int(time.time())
    
    update_expression = "SET #s = :status_val, updated_at = :now_val"
    expression_attribute_names = {"#s": "status"}
    expression_attribute_values = {
        ":status_val": status,
        ":now_val": now
    }
    
    if extra_attributes:
        for key, val in extra_attributes.items():
            update_expression += f", {key} = :{key}_val"
            expression_attribute_values[f":{key}_val"] = val

    try:
        _run_state.update_item(
            Key={"run_id": run_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        logger.info("State transition successful: run_id=%s -> %s", run_id, status)
    except Exception:
        logger.exception("Database state synchronization failed for run_id=%s", run_id)


def handler(event: dict[str, Any], context: Any) -> None:
    """Lambda entrypoint - SQS batch consumer for orchestration."""
    logger.info("Received background processing event from SQS Queue")
    
    # Process each SQS record
    for record in event.get("Records", []):
        try:
            body = json.loads(record["body"])
            run_id = body.get("run_id")
            company = body.get("company")
            country = body.get("country")
            tier = body.get("tier", "Standard")
            
            logger.info(f"Processing job: run_id={run_id}, company={company}, country={country}, tier={tier}")
            
            update_run_status(run_id, "PROCESSING")
            
            # Execute the full orchestration pipeline
            started_at = time.perf_counter()
            try:
                graph_output = asyncio.run(
                    run_intelligence_pipeline(
                        company=company,
                        country=country,
                        run_id=run_id,
                        tier=tier
                    )
                )
                execution_duration = time.perf_counter() - started_at
                
                # Persist report artifact to S3
                artifact_info = _persist_report_artifact(
                    run_id=run_id,
                    company=company,
                    country=country,
                    tier=tier,
                    graph_output=graph_output,
                    execution_duration=execution_duration,
                )
                
                # Update final status
                update_run_status(
                    run_id,
                    "COMPLETED",
                    extra_attributes={
                        "report_url": artifact_info.get("report_url", ""),
                        "execution_time_seconds": execution_duration,
                    }
                )
                logger.info(f"Job completed: run_id={run_id}, duration={execution_duration:.2f}s")
                
            except Exception as exec_error:
                logger.exception(f"Pipeline execution failed for run_id={run_id}")
                update_run_status(
                    run_id,
                    "FAILED",
                    extra_attributes={"error_message": str(exec_error)}
                )
                raise
                
        except Exception as record_error:
            logger.exception("Failed to process SQS record")
            raise
