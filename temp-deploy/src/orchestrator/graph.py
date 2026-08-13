"""LangGraph Orchestration Plane — Custom StateGraph Parallel Core Architecture."""
from __future__ import annotations

import sys
import os
import asyncio
import json
import time
from typing import Any, Dict
from dotenv import load_dotenv

# AWS/LangChain imports
from langgraph.graph import StateGraph, START, END
from langchain_mcp_adapters.client import MultiServerMCPClient

# Load environment variables
load_dotenv()

# This tells Python: "Treat the folder containing 'agents' and 'src' as a search root"
#sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from .state import OrchestratorState
from agentcore.agents import (
    run_financial_agent,
    run_leadership_agent,
    run_litigation_agent,
    run_research_agent,
    run_news_agent
)
from ..processing.validation import validate_payload
from ..processing.synthesis import synthesize
from ..reports.generator import generate_report


# ==========================================
# GRAPH NODES
# ==========================================

def _build_metrics(agent_name: str, started_at: float, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "agent_latencies_ms": {agent_name: round((time.perf_counter() - started_at) * 1000, 2)},
        "cache_hits": {agent_name: bool(payload.get("cache_hit"))},
    }

def research_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Research Agent...")
    started_at = time.perf_counter()
    data = run_research_agent(
        company=state.company,
        country=state.country,
        run_id=state.run_id
    )
    return {"research": data, "metrics": _build_metrics("research", started_at, data)}


def news_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing News Agent...")
    started_at = time.perf_counter()
    data = run_news_agent(
        company=state.company,
        country=state.country,
        run_id=state.run_id
    )
    return {"news": data, "metrics": _build_metrics("news", started_at, data)}


def litigation_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Litigation Agent...")
    started_at = time.perf_counter()
    data = run_litigation_agent(
        company=state.company,
        country=state.country,
        run_id=state.run_id
    )
    return {"litigation": data, "metrics": _build_metrics("litigation", started_at, data)}


def leadership_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Leadership Agent...")
    started_at = time.perf_counter()
    data = run_leadership_agent(
        company=state.company,
        country=state.country,
        run_id=state.run_id
    )
    return {"leadership": data, "metrics": _build_metrics("leadership", started_at, data)}


async def financial_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Financial Agent (with MCP)...")
    started_at = time.perf_counter()
    company = state.company
    country = state.country
    run_id = state.run_id
    
    # 1. Define paths dynamically
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.abspath(os.path.join(base_dir, "..", "mcp_servers", "corporate_tools.py"))
    
    root_dir = os.path.abspath(os.path.join(base_dir, "../../.."))
    venv_python = os.path.join(root_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = os.path.join(root_dir, ".venv", "bin", "python")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    # 2. Define the async loader and client
    mcp_client = MultiServerMCPClient({
        "corporate-intelligence": {
            "command": venv_python,
            "args": [script_path],
            "transport": "stdio"
        }
    })
    tools = await mcp_client.get_tools()
    # Await the async financial agent
    data = await run_financial_agent(company=company, country=country, run_id=run_id, tools=tools)
    return {"financial": data, "metrics": _build_metrics("financial", started_at, data)}


def validation_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Validation Layer...")
    bundle = {
        "research": state.research,
        "news": state.news,
        "litigation": state.litigation,
        "leadership": state.leadership,
        "financial": state.financial
    }
    validated = validate_payload(bundle)
    return {"validated": validated}


def synthesis_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Synthesis Layer...")
    synthesized = synthesize(state.validated)
    return {"synthesized": synthesized}


def report_node(state: OrchestratorState) -> Dict[str, Any]:
    print("[Orchestration] Executing Report Generation Layer...")
    report = generate_report(
        tier=state.tier,
        company=state.company,
        country=state.country,
        synthesized=state.synthesized
    )
    return {"report": report}


# ==========================================
# GRAPH CONVENTIONS
# ==========================================

workflow = StateGraph(OrchestratorState)

# Add nodes
workflow.add_node("research_node", research_node)
workflow.add_node("news_node", news_node)
workflow.add_node("litigation_node", litigation_node)
workflow.add_node("leadership_node", leadership_node)
workflow.add_node("financial_node", financial_node)
workflow.add_node("validation_node", validation_node)
workflow.add_node("synthesis_node", synthesis_node)
workflow.add_node("report_node", report_node)

# Add parallel flow boundaries
workflow.add_edge(START, "research_node")
workflow.add_edge(START, "news_node")
workflow.add_edge(START, "litigation_node")
workflow.add_edge(START, "leadership_node")
workflow.add_edge(START, "financial_node")

# Fan-in/Synchronization barrier transition edges
workflow.add_edge("research_node", "validation_node")
workflow.add_edge("news_node", "validation_node")
workflow.add_edge("litigation_node", "validation_node")
workflow.add_edge("leadership_node", "validation_node")
workflow.add_edge("financial_node", "validation_node")

# Serial processing edges
workflow.add_edge("validation_node", "synthesis_node")
workflow.add_edge("synthesis_node", "report_node")
workflow.add_edge("report_node", END)

# Compile
compiled_graph = workflow.compile()


# ==========================================
# PUBLIC INVOCATION API
# ==========================================

async def run_intelligence_pipeline(inputs: dict) -> dict:
    """Invokes the compiled orchestration graph with clean DTO inputs."""
    started_at = time.time()
    print(f"--- Launching Parallel Graph Execution for: {inputs.get('company')} ---")
    result = await compiled_graph.ainvoke(inputs)
    metrics = result.setdefault("metrics", {})
    metrics["started_at"] = started_at
    metrics["finished_at"] = time.time()
    return result


def _parse_embedded_payload(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, str):
        return None

    trimmed = value.strip()
    if not (trimmed.startswith("{") and trimmed.endswith("}")):
        return None

    try:
        parsed = json.loads(trimmed)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _normalize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)

    for key in ("company", "target_company", "input", "inputs", "arguments", "prompt", "query", "text"):
        parsed = _parse_embedded_payload(normalized.get(key))
        if parsed:
            normalized = {**normalized, **parsed}
            break

    messages = normalized.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue

            parsed = _parse_embedded_payload(message.get("content"))
            if parsed:
                normalized = {**normalized, **parsed}
                break

            content = message.get("content")
            if not isinstance(content, list):
                continue
            for part in content:
                if not isinstance(part, dict):
                    continue
                parsed = _parse_embedded_payload(part.get("text"))
                if parsed:
                    normalized = {**normalized, **parsed}
                    break
            else:
                continue
            break

    return normalized


def _extract_company(payload: dict[str, Any]) -> str | None:
    direct_company = payload.get("company") or payload.get("target_company")
    if isinstance(direct_company, str) and direct_company.strip():
        return direct_company.strip()

    for container_key in ("input", "inputs", "arguments"):
        nested = payload.get(container_key)
        if isinstance(nested, dict):
            nested_company = nested.get("company") or nested.get("target_company")
            if isinstance(nested_company, str) and nested_company.strip():
                return nested_company.strip()
        elif isinstance(nested, str) and nested.strip():
            return nested.strip()

    for text_key in ("prompt", "query", "text"):
        value = payload.get(text_key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    messages = payload.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if isinstance(content, str) and content.strip():
                return content.strip()
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict):
                        text = part.get("text")
                        if isinstance(text, str) and text.strip():
                            return text.strip()

    return None


def _build_invoke_response(
    result: dict[str, Any],
    *,
    response_mode: str,
    include_debug: bool,
) -> dict[str, Any]:
    report = result.get("report", {}) if isinstance(result.get("report"), dict) else {}

    if response_mode == "full_state":
        return result
    if response_mode == "report":
        response: dict[str, Any] = {"report": report.get("markdown", "")}
        if include_debug:
            response["debug"] = {
                "run_id": result.get("run_id"),
                "company": result.get("company"),
                "country": result.get("country"),
                "tier": result.get("tier"),
                "model": report.get("model"),
                "metrics": result.get("metrics", {}),
                "validated": result.get("validated", {}),
                "synthesized": result.get("synthesized", {}),
                "warnings": report.get("warnings", []),
            }
        return response
    if response_mode == "report_with_meta":
        response = {
            "run_id": result.get("run_id"),
            "company": result.get("company"),
            "country": result.get("country"),
            "tier": result.get("tier"),
            "model": report.get("model"),
            "markdown": report.get("markdown", ""),
        }
        if include_debug:
            response["debug"] = {
                "metrics": result.get("metrics", {}),
                "validated": result.get("validated", {}),
                "synthesized": result.get("synthesized", {}),
                "warnings": report.get("warnings", []),
            }
        return response

    return {"report": report.get("markdown", "")}


@app.entrypoint
async def invoke(payload: dict[str, Any]) -> dict[str, Any]:
    """AgentCore HTTP entrypoint."""
    normalized_payload = _normalize_payload(payload)
    company = _extract_company(normalized_payload)
    if not company:
        raise ValueError(
            "Payload must include a company value in one of: "
            "'company', 'target_company', 'input', 'inputs.company', "
            "'prompt', 'query', or 'messages'"
        )

    inputs = {
        "run_id": normalized_payload.get("run_id", "agentcore_dev_run"),
        "company": company,
        "country": normalized_payload.get("country", "US"),
        "tier": normalized_payload.get("tier", "Premium"),
    }
    result = await run_intelligence_pipeline(inputs)
    response_mode = str(normalized_payload.get("response_mode", "report")).lower()
    include_debug = bool(normalized_payload.get("include_debug", False))
    return _build_invoke_response(
        result,
        response_mode=response_mode,
        include_debug=include_debug,
    )


def orchestrator_graph(target_company: str):
    """Sync wrapper for graph execution."""
    inputs = {
        "run_id": "local_sync_run",
        "company": target_company,
        "country": "US",
        "tier": "Premium"
    }
    return asyncio.run(run_intelligence_pipeline(inputs))