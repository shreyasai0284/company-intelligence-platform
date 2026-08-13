import asyncio
import json
import logging
import os
import re
import uuid
from html import escape
from datetime import datetime, timezone
from typing import Any

from collections import OrderedDict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from agentcore.agents._env import load_agentcore_env
from agentcore.src.orchestrator.graph import compiled_graph

load_agentcore_env()

logger = logging.getLogger(__name__)


def _get_allowed_origins() -> list[str]:
    frontend_url = os.getenv("FRONTEND_URL", "").strip()
    if frontend_url:
        return [origin.strip() for origin in frontend_url.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://localhost:5173"]

app = FastAPI(title="Company Intelligence Local Backend")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

runs: dict[str, dict[str, Any]] = {}


def _clean_evidence_text(value: str, *, company: str, require_company: bool = True) -> str:
    text = str(value or "").strip()
    if not text:
        return ""

    text = text.replace("•", "").replace("-", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^(?:bullet|item|note)\s*[:\-]\s*", "", text, flags=re.IGNORECASE)
    text = text.replace("|", " ")
    text = re.sub(r"\s+\|\s+", " ", text)
    text = re.sub(r"\s+", " ", text)
    text = text.strip(" .")

    if not text:
        return ""
    if require_company and company.lower() not in text.lower():
        return ""

    # Remove common truncation artifacts and awkward fragments.
    text = text.replace("...", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text.rstrip(" .")
    if not text:
        return ""
    if text[-1] not in ".!?":
        text += "."
    return text


def build_status_result_payload(result: dict[str, Any], *, run_id: str, company: str, country: str, tier: str, created_at: str, completed_at: str) -> dict[str, Any]:
    report = result.get("report", {}) if isinstance(result.get("report"), dict) else {}
    markdown = report.get("markdown", "") if isinstance(report, dict) else ""

    agent_results: dict[str, Any] = {}

    def add_agent_result(agent_key: str, title: str, insight: str, evidence: list[str], confidence: float = 0.78, metadata: dict[str, Any] | None = None) -> None:
        agent_results[agent_key] = {
            "title": title,
            "confidence_score": round(confidence * 100),
            "detailed_insight": insight,
            "system_evidence": evidence,
            "metadata": metadata or {},
        }

    research = result.get("research") if isinstance(result.get("research"), dict) else {}
    research_profile = research.get("profile", {}) if isinstance(research.get("profile"), dict) else {}
    research_summary = research_profile.get("summary") or ""
    research_sources = [item.get("title") for item in research_profile.get("sources", []) if isinstance(item, dict) and item.get("title")]
    add_agent_result(
        "research",
        "Research Profile",
        research_summary or f"{company} has a broad public footprint and market relevance in {country}.",
        research_sources or [f"Research sources for {company}"],
        confidence=0.82,
        metadata={"sources": research_sources[:3], "data_points": len(research_sources)},
    )

    news = result.get("news") if isinstance(result.get("news"), dict) else {}
    headline_items = news.get("recent_headlines") or []
    if isinstance(headline_items, list):
        evidence = []
        other_company_pattern = re.compile(
            r"\b(?:apple|google|alphabet|microsoft|amazon|meta|tesla|nvidia|facebook|netflix|uber|airbnb|paypal|oracle|adobe|intel|amd|sony|nike|ford|toyota|honda|acura)\b",
            re.IGNORECASE,
        )
        for item in headline_items[:3]:
            cleaned = _clean_evidence_text(item, company=company, require_company=False)
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if company.lower() in lowered:
                evidence.append(cleaned)
                continue
            if not other_company_pattern.search(lowered):
                evidence.append(cleaned)
        evidence = evidence[:3]
    else:
        evidence = []
    sentiment = news.get("sentiment_score")
    add_agent_result(
        "news",
        "News Signals",
        f"Current news sentiment is {'positive' if isinstance(sentiment, (int, float)) and sentiment >= 0.5 else 'mixed'} for {company}.",
        evidence or [],
        confidence=0.74,
        metadata={"sources": evidence[:3], "data_points": len(evidence)},
    )

    litigation = result.get("litigation") if isinstance(result.get("litigation"), dict) else {}
    cases = litigation.get("cases") or []
    if isinstance(cases, list):
        evidence = [
            _clean_evidence_text(item, company=company)
            for item in cases[:3]
            if _clean_evidence_text(item, company=company)
        ]
    else:
        evidence = []
    add_agent_result(
        "litigation",
        "Litigation Watch",
        f"Litigation activity includes {litigation.get('active_count', 0)} tracked matters for {company}.",
        evidence or [],
        confidence=0.79,
        metadata={"sources": evidence[:3], "data_points": len(evidence)},
    )

    leadership = result.get("leadership") if isinstance(result.get("leadership"), dict) else {}
    exec_updates = leadership.get("executives_updates") or []
    product_updates = leadership.get("product_lines_updates") or []
    if isinstance(exec_updates, list):
        exec_evidence = [
            _clean_evidence_text(item, company=company)
            for item in exec_updates[:2]
            if _clean_evidence_text(item, company=company)
        ]
    else:
        exec_evidence = []
    if isinstance(product_updates, list):
        product_evidence = [
            _clean_evidence_text(item, company=company)
            for item in product_updates[:2]
            if _clean_evidence_text(item, company=company)
        ]
    else:
        product_evidence = []
    leadership_evidence = exec_evidence + product_evidence
    add_agent_result(
        "leadership",
        "Leadership Signals",
        f"Leadership and product signals indicate an evolving operating posture for {company}.",
        leadership_evidence or [f"No leadership updates surfaced for {company}."],
        confidence=0.72,
        metadata={"sources": leadership_evidence[:3], "data_points": len(leadership_evidence)},
    )

    financial = result.get("financial") if isinstance(result.get("financial"), dict) else {}
    financial_brief = financial.get("corporate_brief") or ""
    cleaned_financial_brief = _clean_evidence_text(financial_brief, company=company, require_company=False)
    financial_evidence = [cleaned_financial_brief] if cleaned_financial_brief else []
    add_agent_result(
        "financial",
        "Financial Snapshot",
        financial_brief or f"Financial profile for {company} is available and being monitored.",
        financial_evidence or [f"No financial snapshot available for {company}."],
        confidence=0.8,
        metadata={"sources": [financial.get("ticker", "N/A")], "data_points": 1},
    )

    return {
        "run_id": run_id,
        "company": company,
        "country": country,
        "tier": tier,
        "status": "COMPLETED",
        "executive_summary": markdown or f"{company} has been analyzed across multiple intelligence domains in {country}.",
        "agent_results": agent_results,
        "created_at": created_at,
        "completed_at": completed_at,
        "result": result,
    }


class IngestRequest(BaseModel):
    company: str
    country: str = "US"
    tier: str = "Standard"


@app.get("/ping")
async def ping():
    return {"status": "ok"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/invocations")
async def invocations(payload: IngestRequest):
    run_id = str(uuid.uuid4())
    runs[run_id] = {
        "run_id": run_id,
        "company": payload.company,
        "country": payload.country,
        "tier": payload.tier,
        "status": "QUEUED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }

    async def run_pipeline():
        runs[run_id]["status"] = "PROCESSING"
        try:
            result = await compiled_graph.ainvoke({
                "run_id": run_id,
                "company": payload.company,
                "country": payload.country,
                "tier": payload.tier,
            })
            runs[run_id]["result"] = build_status_result_payload(
                result,
                run_id=run_id,
                company=payload.company,
                country=payload.country,
                tier=payload.tier,
                created_at=runs[run_id]["created_at"],
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
            runs[run_id]["status"] = "COMPLETED"
        except Exception as exc:
            logger.exception("Invocation pipeline failed for run_id=%s", run_id)
            runs[run_id]["status"] = "FAILED"
            runs[run_id]["error"] = str(exc)

    asyncio.create_task(run_pipeline())
    return {"run_id": run_id}


@app.post("/ingest")
async def ingest(payload: IngestRequest):
    run_id = str(uuid.uuid4())
    runs[run_id] = {
        "run_id": run_id,
        "company": payload.company,
        "country": payload.country,
        "tier": payload.tier,
        "status": "QUEUED",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "result": None,
    }

    async def run_pipeline():
        runs[run_id]["status"] = "PROCESSING"
        try:
            result = await compiled_graph.ainvoke({
                "run_id": run_id,
                "company": payload.company,
                "country": payload.country,
                "tier": payload.tier,
            })
            runs[run_id]["result"] = result
            runs[run_id]["status"] = "COMPLETED"
        except Exception as exc:
            logger.exception("Ingest pipeline failed for run_id=%s", run_id)
            runs[run_id]["status"] = "FAILED"
            runs[run_id]["error"] = str(exc)

    asyncio.create_task(run_pipeline())
    return {"run_id": run_id}


@app.get("/status/{run_id}")
def get_status(run_id: str):
    run = runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")

    result = run.get("result") or {}
    if isinstance(result, dict):
        executive_summary = result.get("executive_summary") or result.get("result", {}).get("report", {}).get("markdown", "")
    else:
        executive_summary = ""

    return {
        "run_id": run_id,
        "company": run["company"],
        "country": run["country"],
        "tier": run["tier"],
        "status": run["status"],
        "executive_summary": executive_summary,
        "agent_results": result.get("agent_results", {}) if isinstance(result, dict) else {},
        "created_at": run["created_at"],
        "completed_at": result.get("completed_at") if isinstance(result, dict) else None,
        "result": run.get("result"),
        "error_message": run.get("error"),
        "error": run.get("error"),
    }


@app.get("/reports/{run_id}")
def get_report(run_id: str):
    run = runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if run.get("status") != "COMPLETED":
        raise HTTPException(status_code=409, detail="report not ready")
    return run.get("result", {})


@app.get("/report-view/{run_id}")
def get_report_view(run_id: str):
    run = runs.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="run not found")
    if run.get("status") != "COMPLETED":
        raise HTTPException(status_code=409, detail="report not ready")

    result = run.get("result") or {}
    report = result.get("report", {}) if isinstance(result, dict) else {}
    markdown = report.get("markdown", "") if isinstance(report, dict) else ""

    header = (
        f"Report View - {run.get('company', 'Report')}\n"
        f"Run ID: {run_id} | Country: {run.get('country', '')} | Tier: {run.get('tier', '')}\n\n"
    )
    return PlainTextResponse(header + markdown)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
