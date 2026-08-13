"""Background engine orchestrator for the Company Intelligence Platform V5.0.

Consumes sanitized messages from SQS, executes the Async Custom Parallel 
StateGraph orchestration pipeline, and updates execution tracking states.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import time
from typing import Any
import boto3

# Clean and pristine absolute import made possible by our new CDK asset root setup!
from src.orchestrator.graph import run_intelligence_pipeline

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUN_STATE_TABLE = os.environ["RUN_STATE_TABLE"]
REPORTS_BUCKET = os.environ.get("REPORTS_BUCKET", "")
_ddb = boto3.resource("dynamodb")
_run_state = _ddb.Table(RUN_STATE_TABLE)
_s3 = boto3.client("s3")


def _persist_report_artifact(
    *,
    run_id: str,
    company: str | None,
    country: str,
    tier: str,
    graph_output: dict[str, Any],
    execution_duration: float,
) -> dict[str, str]:
    if not REPORTS_BUCKET:
        return {}

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

    key = f"outputs/{run_id}.json"
    _s3.put_object(
        Bucket=REPORTS_BUCKET,
        Key=key,
        Body=json.dumps(artifact, default=str).encode("utf-8"),
        ContentType="application/json",
    )
    return {
        "report_bucket": REPORTS_BUCKET,
        "report_key": key,
        "report_url": f"s3://{REPORTS_BUCKET}/{key}",
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


def handler(event: dict[str, Any], _context: Any) -> None:
    """Lambda entrypoint triggered by SQS Event Source Mapping."""
    logger.info("Received background processing event from SQS Queue.")
    
    for record in event.get("Records", []):
        try:
            body = json.loads(record.get("body", "{}"))
            run_id = body.get("run_id")
            company = body.get("company")
            country = body.get("country", "US")
            tier = body.get("tier", "Standard")
            
            if not run_id:
                continue

            # ─── STEP 1: TRANSITION TO PROCESSING ───
            update_run_status(run_id, "PROCESSING")
            start_time = time.time()

            # ─── STEP 2: EXECUTE ASYNC LANGGRAPH STATE ENGINE ───
            logger.info("Invoking Async Custom Parallel StateGraph Engine for %s...", company)
            
            # Construct a clean DTO payload free of Lambda transport envelope details
            inputs = {
                "run_id": run_id,
                "company": company,
                "country": country,
                "tier": tier
            }

            # Executing the coroutine tree directly inside the synchronous handler wrapper
            graph_output = asyncio.run(run_intelligence_pipeline(inputs))
            
            # Natively extract our structured report data from the custom graph execution state
            report = graph_output.get("report", {})
            final_report_content = report.get("markdown", "")
            model_used = report.get("model", "")
            warnings = report.get("warnings", []) if isinstance(report.get("warnings", []), list) else []
                
            logger.info("LangGraph workflow successfully executed for run_id=%s", run_id)
            execution_duration = round(time.time() - start_time, 2)
            artifact_location = _persist_report_artifact(
                run_id=run_id,
                company=company,
                country=country,
                tier=tier,
                graph_output=graph_output,
                execution_duration=execution_duration,
            )

            # ─── STEP 3: TRANSITION TO COMPLETED WITH LIVE METADATA ───
            output_payload = {
                "execution_time_seconds": execution_duration,
                "summary_snippet": final_report_content[:200] if final_report_content else "Processing complete.",
                "report_model": model_used,
                "warning_count": len(warnings),
                "agent_metrics": graph_output.get("metrics", {}),
            }
            output_payload.update(artifact_location)
            
            update_run_status(run_id, "COMPLETED", extra_attributes=output_payload)
            
        except Exception as exc:
            if "run_id" in locals():
                update_run_status(run_id, "FAILED", extra_attributes={"error_reason": str(exc)})
            logger.exception("Pipeline terminal crash encountered during graph invocation.")
            raise exc