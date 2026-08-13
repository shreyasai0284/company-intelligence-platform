"""Minimal orchestrator - bypasses graph.py to test SQS->DynamoDB pipeline."""
import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any
import boto3

logger = logging.getLogger()
logger.setLevel(logging.INFO)

RUN_STATE_TABLE = os.environ["RUN_STATE_TABLE"]
REPORTS_DIR = Path(os.environ.get("REPORTS_DIR", "./reports"))
_ddb = boto3.resource("dynamodb")
_run_state = _ddb.Table(RUN_STATE_TABLE)


def handler(event, context):
    """Minimal handler - just proves SQS triggering and DynamoDB updates work."""
    
    logger.info(f"Received {len(event.get('Records', []))} message(s)")
    
    for record in event.get("Records", []):
        try:
            # Parse SQS message
            body = json.loads(record["body"])
            run_id = body.get("run_id")
            company = body.get("company")
            
            logger.info(f"Processing: {run_id} for {company}")
            
            # Update status to PROCESSING
            _run_state.update_item(
                Key={"run_id": run_id},
                UpdateExpression="SET #status = :status, updated_at = :updated_at",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "PROCESSING",
                    ":updated_at": int(time.time()),
                },
            )
            logger.info(f"Status updated to PROCESSING for {run_id}")
            
            # Create minimal report (bypass agent execution)
            report = {
                "run_id": run_id,
                "company": company,
                "status": "success",
                "report": {
                    "executive_summary": "Minimal orchestrator - infrastructure test",
                    "sections": []
                },
                "generated_at": int(time.time())
            }
            
            REPORTS_DIR.mkdir(parents=True, exist_ok=True)
            report_path = REPORTS_DIR / f"{run_id}.json"
            report_path.write_text(json.dumps(report), encoding="utf-8")
            logger.info(f"Report stored: {report_path}")
            
            # Update status to COMPLETED
            _run_state.update_item(
                Key={"run_id": run_id},
                UpdateExpression="SET #status = :status, updated_at = :updated_at",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "COMPLETED",
                    ":updated_at": int(time.time()),
                },
            )
            logger.info(f"Status updated to COMPLETED for {run_id}")
            
        except Exception as e:
            logger.error(f"Error processing record: {e}", exc_info=True)
            # Update to FAILED
            if 'run_id' in locals():
                _run_state.update_item(
                    Key={"run_id": run_id},
                    UpdateExpression="SET #status = :status, error_message = :error_message, updated_at = :updated_at",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "FAILED",
                        ":error_message": str(e),
                        ":updated_at": int(time.time()),
                    },
                )
    
    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Pipeline executed"})
    }
