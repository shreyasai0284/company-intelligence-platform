# API Deployment & Access Guide

## ✅ Live Deployment

**API Endpoint:** https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/

**Stack Status:** Successfully deployed (80.54s)

---

## Deployment Architecture

### What Was Deployed (PlatformInfraStack)
```
✅ API Gateway (REST)
✅ 4 Lambda Functions (ingestion, status, reports, orchestrator)
✅ SQS FIFO queue + DLQ
✅ DynamoDB tables (run-state, agent-cache)
✅ S3 reports bucket (versioned, encrypted)
✅ IAM roles + CloudWatch logs
```

### What Wasn't Deployed (AgentCoreStack)
```
⏸️  AgentCore Bedrock runtime (skipped due to Python 3.13 wheel availability)
⏸️  MCP gateway deployment (specification prepared, runtime deferred)
⏸️  Agent certification/validation (code ready, deployment pending)
Python 3.13 Wheel Incompatibility: During CDK deployment, building native C-extension Python wheel binaries for the AWS AgentCore SDK failed because Linux Lambda builder environments lacked pre-compiled .whl files for Python 3.13.
Infrastructure Fallback Strategy: To keep the platform live and fully functional, the team deployed PlatformInfraStack (API Gateway 
→
→ Ingestion Lambda 
→
→ SQS 
→
→ Orchestrator Lambda). The orchestration code and agent logic run as a standard Python application bundled inside AWS Lambda rather than inside the managed Bedrock AgentCore Runtime Container.
How Much of AgentCore is Actually Used Right Now?
AgentCore Component	Status in Codebase	Current Execution Mode
AgentCore JSON Spec (agentcore.json)	✅ Configured	Defines Gateway, MCP Runtime Tools, and MyAgent entry point (graph.py).
Agent Decorators (_decorators.py)	⚠️ Fallback Shim	Standard @agent decorator falls back to local Python wrapper functions when deployed on standard Lambda.
MCP Tool Servers (corporate_tools.py)	✅ Active	Executed as local stdio subprocesses inside Orchestrator Lambda via MultiServerMCPClient.
AgentCore Managed Gateway	⏸️ Deferred	Direct HTTP invocation bypasses AgentCore Gateway; API Gateway routes directly to Lambda.
2. Is This Architecture Heavy?
Yes, the current setup is somewhat heavy. It combines two parallel orchestration frameworks:

Infrastructure Tier: API Gateway + Ingestion Lambda + SQS FIFO Queue + DLQ + Orchestrator Lambda + Status Lambda + Report Lambda + DynamoDB Run Table + DynamoDB Cache Table + S3 Bucket.
Orchestrator Tier: LangGraph StateGraph + MultiServerMCPClient + 5 Domain Agents + Tavily Client + GDELT + CourtListener + SEC Edgar + OpenSearch (optional).
Why is it heavy?
Nested Process Spawning: Inside Orchestrator Lambda, Python launches another Python process (corporate_tools.py via stdio) for MCP.
Double Orchestration: Using both SQS/Lambda AND LangGraph fan-out, plus having placeholders for Bedrock AgentCore Gateway creates overlapping control planes.
3. What Can Be Incorporated to Replace / Consolidate Others?
You can streamline this architecture into a lean, production-grade pattern depending on whether you choose Managed AWS AgentCore or Serverless Native (LangGraph + Lambda).

Option A: Full AWS AgentCore Managed Path (Recommended if using AWS Bedrock AgentCore)


[React Frontend] ──► [API Gateway] ──► [AgentCore Managed Gateway]
                                                 │
                                                 ▼
                                   [AgentCore Runtime (graph.py)]
                                  (Managed MCP Tools + Bedrock)
What it replaces:
Eliminates Ingestion Lambda, SQS FIFO Queue, and Orchestrator Lambda.
Eliminates local MultiServerMCPClient subprocesses; AgentCore natively hosts corporate_tools.py as AWS-managed tool endpoints (mcpRuntimeTools).
Benefits: Removes 3 Lambda functions, SQS queues, and manual process management.
Option B: Direct Async Serverless Path (Recommended for standard AWS Serverless)


[React Frontend] ──► [API Gateway] ──► [Orchestrator Lambda (LangGraph)]
                                           ├──► Fast Async HTTP Requests (Tavily/SEC/GDELT)
                                           └──► S3 + DynamoDB Cache
What it replaces:
Eliminates MCP Subprocess overhead (corporate_tools.py run via stdio pipe); import functions directly as standard Python async modules.
Replaces synchronous requests calls with httpx / aiohttp inside agents.
4. How to Smoothen It Out Without Losing Functionality
Here is a step-by-step optimization plan to simplify the system while preserving all 5 agents, multi-tier fallbacks, caching, and reporting:



┌─────────────────────────────────────────────────────────────────────────────┐
│                       REDUCE ARCHITECTURAL OVERHEAD                         │
└─────────────────────────────────────────────────────────────────────────────┘
 1. Replace Subprocess MCP with Direct Module Imports
    ─────────────────────────────────────────────────
    • Current: LangGraph -> MultiServerMCPClient -> stdio -> Subprocess Python
    • Refactored: Import functions directly from corporate_tools.py into agents.
    • Savings: Eliminates process spawn time, IPC memory overhead, and subprocess crashes.
 2. Switch to Async HTTP (httpx)
    ───────────────────────────
    • Current: requests in worker threads via asyncio.to_thread().
    • Refactored: Native async HTTP calls with httpx.AsyncClient.
    • Savings: Eliminates ThreadPoolExecutor thread-switching; faster execution.
 3. Unify Python Runtime Version
    ────────────────────────────
    • Move to Python 3.12 (has native pre-built wheels for all AWS/LangChain SDKs).
    • Resolves AgentCore stack deployment blockages instantly.
 4. Consolidate Lambda Footprint
    ─────────────────────────────
    • Combine Ingestion and Orchestrator into a single Async Lambda endpoint or 
      let API Gateway directly trigger Orchestrator via SQS integration.
Architectural Comparison Summary
Metric	Current (V5.0)	Streamlined (Direct Async)	Fully Managed AgentCore
AWS Resources	12 (API, 4 Lambdas, SQS, DLQ, 2 DynamoDB, S3, CDK)	6 (API Gateway, 2 Lambdas, DynamoDB, S3)	5 (API Gateway, AgentCore Gateway, Runtime, DynamoDB, S3)
Agent IPC Mechanism	JSON-RPC over stdio subprocess	Direct Python function calls	Native AWS AgentCore Managed Tools
Latency per Run	~8 - 15 seconds	~3 - 6 seconds	~4 - 7 seconds
Complexity	High (Double orchestration)	Low (Lean serverless)	Medium (Managed cloud native)

```

---

## Why You Get "Missing Authentication Token" Error

### Problem
When you click the API endpoint URL in a browser, you get:
```
{"message":"Missing Authentication Token"}
```

### Why This Happens
1. **Browser makes GET requests by default**
2. **POST /ingest endpoint rejects GET requests** → API Gateway returns "Missing Authentication Token" (generic error for unauthorized HTTP method)
3. **GET endpoints (`/status`, `/reports`) work fine**

### Actual API Status
```
✅ GET /reports/{runId}     → Works (404 if report not found)
✅ GET /status/{runId}      → Works (returns run state or 404)
❌ GET /ingest              → Returns 401 (endpoint is POST-only)
✅ POST /ingest             → Works (with JSON body)
```

---

## How to Test the API Properly

### Option 1: Use Postman/REST Client
```
POST https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/ingest
Content-Type: application/json

{
  "company": "Tesla",
  "country": "USA",
  "tier": "standard"
}
```

Response (200 OK):
```json
{
  "run_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "status": "QUEUED"
}
```

### Option 2: Use cURL from Terminal
```bash
# Submit a job
curl -X POST https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/ingest \
  -H "Content-Type: application/json" \
  -d '{"company":"Tesla","country":"USA","tier":"standard"}'

# Check status (replace {runId} with actual)
curl https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/status/{runId}

# Get report (replace {runId} with actual)
curl https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/reports/{runId}
```

### Option 3: Use Python requests
```python
import requests

# Submit job
resp = requests.post(
  "https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/ingest",
  json={"company": "Tesla", "country": "USA", "tier": "standard"}
)
run_id = resp.json()["run_id"]
print(f"Job queued: {run_id}")

# Poll status
status_resp = requests.get(
  f"https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/status/{run_id}"
)
print(f"Status: {status_resp.json()}")

# Fetch report (when complete)
report_resp = requests.get(
  f"https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/reports/{run_id}"
)
print(f"Report: {report_resp.json()}")
```

---

## AgentCore Deployment Difference

### PlatformInfraStack (✅ Deployed)
- **Purpose:** REST API layer + async orchestration infrastructure
- **Components:** API Gateway, Lambdas, DynamoDB, SQS, S3
- **Responsible for:** Ingest, status tracking, report retrieval, job queuing
- **No dependency on:** Bedrock AgentCore SDK

### AgentCoreStack (⏸️ Skipped)
- **Purpose:** Bedrock AgentCore agent runtime + gateway
- **Components:** Bedrock agents, MCP gateway, agent lifecycle management
- **Responsible for:** Running the 5 domain agents, LLM orchestration, agent monitoring
- **Dependency on:** Bedrock AgentCore SDK + Python 3.13 wheels

### Why AgentCore Deployment Was Skipped
The CDK tried to compile Python dependencies for AWS Lambda but failed:
```
PackagingError: Building source distributions is disabled
```

This happens when pip can't find pre-built wheels (.whl files) for Python 3.13 packages and isn't configured to build from source. The solution is one of:
1. **Use Python 3.12** (more wheel availability)
2. **Pre-build a Lambda layer** with all packages
3. **Configure pip to build from source** (slower deployment)

### Important: Does This Mean the System Won't Work?

**No—it will still work!** Here's why:
- The **orchestrator Lambda** is deployed as part of `PlatformInfraStack`
- The orchestrator Lambda **includes the agent code** (via bundling)
- When a job arrives in SQS, the Lambda will execute the agent code
- The agents will run and generate reports normally
- The only thing missing is Bedrock AgentCore **certification** (which is optional)

The agents will run as a **standard Python application** inside the orchestrator Lambda, not as a certified Bedrock AgentCore deployment.

---

## Next Steps to Complete AgentCore

To deploy the AgentCore stack later:

1. **Use Python 3.12 instead of 3.13:**
   ```bash
   python -m venv .venv --python=python3.12
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Or pre-build a layer:**
   ```bash
   # Create wheel cache for Python 3.12
   pip wheel -r requirements.txt -w ./wheels/
   # Then reference this in CDK
   ```

3. **Or update main.ts to re-enable AgentCoreStack** (after fixing Python version)

---

## Cost & Free Tier (Deployed Resources)

| Service | Usage | Free Tier? | Cost |
|---------|-------|-----------|------|
| API Gateway | Requests | 1M/month | ✅ FREE |
| Lambda | Invocations | 1M/month | ✅ FREE |
| DynamoDB | Read/write | On-demand | ✅ FREE (first month) |
| S3 | Storage + API | 5GB + 20k ops | ✅ FREE |
| SQS | Requests | 1M/month | ✅ FREE |
| CloudWatch | Logs | 5GB/month | ✅ FREE |
| **Total** | | | **$0/month** |

All deployed resources are within AWS free tier for typical usage.

---

## Troubleshooting

### "Missing Authentication Token" on `/ingest`
- **Cause:** Visiting endpoint in browser (uses GET)
- **Solution:** Use POST method with JSON body in Postman/cURL

### "not_found" on `/reports/{runId}`
- **Cause:** Report not yet persisted (job still processing)
- **Solution:** Check `/status/{runId}` first, wait for COMPLETED status

### "500 reports_bucket_not_configured"
- **Cause:** Lambda missing `REPORTS_BUCKET` env var
- **Solution:** Check CloudWatch logs, re-deploy stack

### No output from `/status/{runId}`
- **Cause:** Job not found in DynamoDB
- **Solution:** Verify `run_id` is correct, check if SQS processed the message

---

## Summary

| Component | Status | Notes |
|-----------|--------|-------|
| REST API | ✅ LIVE | 3 endpoints ready |
| Infrastructure | ✅ LIVE | All AWS services deployed |
| Agent Runtime | ⏸️ READY | Code present, AgentCore certification deferred |
| Persistence | ✅ LIVE | S3 + DynamoDB working |
| Authentication | ❌ NONE | API is open (add auth if needed) |
| Cost | ✅ FREE | Stays within free tier |
