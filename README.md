# Company Intelligence Platform V5.0

Multi-agent enterprise intelligence platform.

## Architecture Overview

### Event Flow: User Request → Report Delivery

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLIENT (Frontend / API)                                                      │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. INGESTION LAYER (Lambda: cip-api-ingestion)                             │
│    ├─ Validates request: {company, country, tier}                          │
│    ├─ Generates run_id (UUID)                                             │
│    ├─ Creates DynamoDB entry (cip-run-state) with status=QUEUED            │
│    └─ Enqueues message to SQS FIFO (cip-ingestion.fifo)                    │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ASYNC QUEUE (SQS FIFO: cip-ingestion.fifo)                              │
│    └─ Triggers orchestrator Lambda via Event Source Mapping                │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. ORCHESTRATION LAYER (Lambda: cip-engine-orchestrator)                   │
│    │                                                                         │
│    ├─ Updates DynamoDB status → PROCESSING                                 │
│    │                                                                         │
│    ├─ Executes LangGraph StateGraph (agentcore/src/orchestrator/graph.py)  │
│    │  ├─ PARALLEL AGENTS (5 concurrent):                                   │
│    │  │  ├─ research_agent → company_profile                               │
│    │  │  ├─ news_agent → recent_headlines + sentiment                      │
│    │  │  ├─ leadership_agent → executives + products                       │
│    │  │  ├─ litigation_agent → active_cases                                │
│    │  │  └─ financial_agent → financial_metrics                            │
│    │  │                                                                     │
│    │  ├─ DATA RETRIEVAL (per agent):                                        │
│    │  │  ├─ Try Tavily API (optional, graceful fallback)                   │
│    │  │  ├─ Cache hit? Use DynamoDB (cip-agent-cache)                      │
│    │  │  └─ No cache? Query OpenSearch (optional vector search)            │
│    │  │                                                                     │
│    │  ├─ SYNTHESIS:                                                         │
│    │  │  ├─ Merge 5 agent outputs                                          │
│    │  │  ├─ Deduplicate & rank by materiality                              │
│    │  │  └─ Apply impact scoring (impact.py)                               │
│    │  │                                                                     │
│    │  └─ REPORT GENERATION (Bedrock):                                       │
│    │     ├─ Executive Summary (with hierarchy enforcement)                  │
│    │     ├─ Risk Analysis section                                           │
│    │     ├─ Opportunities section                                           │
│    │     ├─ Model selection: Nova Lite (Standard) / Claude 3.5 (Premium)    │
│    │     └─ Schema repair (optional, if Bedrock returns malformed JSON)     │
│    │                                                                         │
│    ├─ Persist report artifact to S3 (cip-reports-{account}-{region})      │
│    │  └─ Key: outputs/{run_id}.json (full report JSON)                     │
│    │                                                                         │
│    └─ Update DynamoDB status → COMPLETED (with metadata)                   │
│                                                                             │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. STATUS API (Lambda: cip-api-status)                                      │
│    └─ GET /status/{runId} → Returns current DynamoDB row                    │
│       (Client polls this until status !== QUEUED)                          │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. REPORT RETRIEVAL (Lambda: cip-api-reports)                              │
│    └─ GET /reports/{runId} → Returns S3 artifact (outputs/{runId}.json)    │
└────────────┬────────────────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ CLIENT receives full report JSON                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Detailed Flow: Input to Output

The diagram above is the high-level version. This is the exact control flow the project is designed around today:

1. A user submits `{ company, country, tier }` from the frontend or a direct API call.
  Why: the pipeline needs a small, fixed input contract so every downstream stage can treat requests consistently.

2. The ingestion Lambda validates the payload, normalizes the request, and generates a `run_id`.
  Why: validation prevents bad jobs from entering the queue, and `run_id` gives the client a stable handle for polling and retrieval.

3. The ingestion Lambda writes `QUEUED` to DynamoDB and publishes a message to SQS.
  Why: the async queue decouples request latency from the much slower research/report workflow.

4. The orchestrator Lambda reads the SQS message, marks the run as `PROCESSING`, and starts the LangGraph pipeline in `agentcore/src/orchestrator/graph.py`.
  Why: the status change lets the client observe progress, and the orchestrator keeps the business logic in one place.

5. The graph fans out into five parallel agents: research, news, leadership, litigation, and financial.
  Why: each domain is independent, so running them concurrently reduces total runtime and keeps the report balanced.

6. Each agent tries the best live source first, then falls back if needed.
  Why: the project prefers fresh data, but it is designed to keep working if one source is missing or returns too little.
  - Research: Tavily first, then MCP, then GDELT, then knowledge base, then related cache context.
  - News: Tavily first, then MCP, then GDELT, then knowledge base, then related cache context.
  - Leadership: Tavily for executive and product signals, then MCP, then related cache context.
  - Litigation: Tavily first, then MCP, then CourtListener, then knowledge base, then related cache context.
  - Financial: Yahoo Finance and yfinance first, then MCP, then SEC filings, then knowledge base.

7. Validation and synthesis merge the five outputs, deduplicate repeated facts, and rank what is material.
  Why: raw source data is noisy; this stage decides which facts matter enough to reach the final report.

8. The report generator routes to Bedrock Nova Lite for Standard tier or Nova Pro for Premium tier, with a local template fallback if Bedrock is unavailable.
  Why: tiering lets the project balance cost and quality, while the fallback keeps the system usable during model or network failures.

9. The orchestrator stores the final artifact in S3 and updates DynamoDB to `COMPLETED` or `FAILED`.
  Why: S3 holds the immutable report, while DynamoDB remains the fast source of truth for status polling.

10. The client polls `/status/{runId}` until the run is finished, then fetches `/reports/{runId}`.
   Why: this keeps the user experience simple and avoids holding the original request open for the entire analysis run.

The same LangGraph pipeline is what `agentcore dev` exercises locally; the launch surface changes, but the agent logic, fallbacks, synthesis, and report generation are the same.

### How the Agents Work in Detail

All five agents follow the same general operating pattern, but each one is tuned to a different business question. The shared design is intentional: it keeps the system resilient when one provider is missing, slow, or sparse, while still preferring fresh live data when it is available.

#### Shared agent pattern

Every agent follows the same shape, but each one uses a different primary source and a different source file.

1. Check cache first in [agentcore/agents/_cache.py](agentcore/agents/_cache.py).
  Why: repeated company queries should return fast without redoing the same lookup.
2. Try the live source for that agent.
  Why: the report should prefer current evidence over stale summaries.
3. Fall back to MCP, external APIs, or knowledge-base retrieval when the live source is thin.
  Why: the system should still produce a useful section even when one provider fails.
4. Return the extracted facts plus `primary_source` and `sources_used`.
  Why: the orchestrator can explain where each section came from.

#### Research agent

The research agent builds the company profile and operating context that the rest of the report depends on. Its implementation lives in [agentcore/agents/research_agent.py](agentcore/agents/research_agent.py).

- How it works: it first checks the cache, then queries Tavily for a company overview, business model, market position, and geography-specific context.
- How it fills gaps: if Tavily does not return enough, it calls the MCP corporate-insight tool through [agentcore/agents/_mcp.py](agentcore/agents/_mcp.py), then falls back to GDELT and finally the knowledge base through [agentcore/agents/_external_apis.py](agentcore/agents/_external_apis.py).
- What it stores: the agent builds a `profile.summary` and a `profile.sources` list, then writes the result back through the cache helpers in [agentcore/agents/_cache.py](agentcore/agents/_cache.py).
- Why it matters: this section becomes the base company narrative before the other agents add risk, legal, leadership, and financial detail.

#### News agent

The news agent focuses on recent developments that materially affect the company. Its implementation lives in [agentcore/agents/news_agent.py](agentcore/agents/news_agent.py).

- How it works: it first checks the cache, then uses Tavily news searches for headlines about recalls, investigations, earnings misses, regulatory warnings, or other material events.
- How it fills gaps: if Tavily is sparse, it falls back to MCP corporate-insight text, then GDELT, then the knowledge base, then related cached context from [agentcore/agents/_cache.py](agentcore/agents/_cache.py).
- What it stores: it ranks the returned headlines with the impact helpers used by the orchestrator and stores `recent_headlines`, `sentiment_score`, `headline_sources`, and `headline_impact`.
- Why it matters: the report should show the most relevant public events, not just every headline the web returns.

#### Leadership agent

The leadership agent captures executive and product-direction changes. Its implementation lives in [agentcore/agents/leadership_agent.py](agentcore/agents/leadership_agent.py).

- How it works: it first checks the cache, then runs two Tavily searches, one for executive changes and one for product updates.
- How it fills gaps: if either search is weak, it uses the MCP corporate-insight fallback via [agentcore/agents/_mcp.py](agentcore/agents/_mcp.py) and related cache context.
- What it stores: it writes `executives_updates` and `product_lines_updates` so the report can separate leadership moves from product changes.
- Why it matters: leadership and product updates often explain strategy shifts, execution changes, or new risk.

#### Litigation agent

The litigation agent surfaces legal and regulatory exposure. Its implementation lives in [agentcore/agents/litigation_agent.py](agentcore/agents/litigation_agent.py).

- How it works: it first checks the cache. If there is no usable cached result, it searches Tavily for lawsuits, active cases, and legal risk signals.
- How it fills gaps: if Tavily is weak or returns too little, it falls back to the MCP corporate-insight tool, then CourtListener, then the knowledge base, then related cache context.
- What it stores: it writes a list of case titles or legal-risk summaries in `cases`, along with `active_count` and provenance metadata.
- Why it matters: this section should clearly tell the user what the legal issue is instead of just saying the company has litigation.

#### Financial agent

The financial agent provides market context and a usable financial snapshot. Its implementation lives in [agentcore/agents/financial_agent.py](agentcore/agents/financial_agent.py).

- How it works: it first checks the cache, then resolves a ticker with Yahoo Finance search, then opens `yfinance` for live price and statement data.
- How it builds the financial answer: if the company is public, it pulls live share price and computes revenue growth from the financial statements. If the company is private or unlisted, it skips the market lookup path and uses fallback sources instead.
- How it fills gaps: when there is no ticker or no usable public market data, it falls back to the MCP corporate tool, then SEC filings, then the knowledge base through [agentcore/agents/_external_apis.py](agentcore/agents/_external_apis.py).
- What it stores: it writes `ticker`, `share_price`, `cagr_5y`, and `corporate_brief`, then caches the payload for repeat queries.
- Why it matters: public companies need market context, but private or unlisted companies still need a financial narrative that the report can use.


┌─────────────────────────────────────────────────────────────────────────────┐
│                           FULL ENTERPRISE SYSTEM                            │
├─────────────────────────────────────────────┬───────────────────────────────┤
│    AWS Platform Infrastructure (CDK)        │    AWS Bedrock AgentCore      │
│  (API Gateway, SQS, DynamoDB, S3 Buckets)   │    (LLM Reasoning & Runtime)  │
├─────────────────────────────────────────────┼───────────────────────────────┤
│ • Decoupled REST APIs                       │ • LangGraph State Management  │
│ • Async Job Queuing (SQS FIFO + DLQ)         │ • Bedrock Model Prompting     │
│ • Long-term Report Persistence (S3)         │ • MCP Tool Execution          │
│ • Run State & Cache Database (DynamoDB)     │ • Agent Reasoning Loops       │
└─────────────────────────────────────────────┴───────────────────────────────┘
Specific Reasons Why AgentCore Doesn't Include Infrastructure Inbuilt
Reason A: SQS Queues & Async Processing
AgentCore executes agent reasoning loops (which can take 10 to 60 seconds per company query).
API Gateway & SQS allow users to submit requests instantly without waiting for a 60-second HTTP timeout. If AgentCore forced direct synchronous HTTP, high traffic would cause HTTP 504 timeouts.
Reason B: Database & Persistence Choices (DynamoDB / S3)
AWS doesn't force a specific database inside AgentCore because different enterprises use PostgreSQL, MongoDB, DynamoDB, or S3.
By leaving storage separate, your platform can save reports permanently in S3 (cip-reports) and cache results in DynamoDB (cip-agent-cache) according to your own custom security, encryption, and TTL rules.
Reason C: Flexibility & Security (API Gateway)
Enterprise apps need custom authentication (Cognito, OAuth2, API Keys), rate limiting, and CORS headers.
API Gateway provides enterprise-grade API management in front of AgentCore.
3. Summary
AgentCore provides the brain (LLM orchestrator, LangGraph, agent tools).
AWS Infrastructure (CDK) provides the body (REST endpoints, message queues, databases, file storage).
By using CDK (cdk deploy), you tie the brain and the body together into a single production application

#### Validation, synthesis, and report generation

- Validation checks that all five agent branches returned usable data.
  Why: if one branch is empty or malformed, the report should not blindly trust it.
- Synthesis deduplicates and ranks the raw facts.
  Why: multiple agents can surface the same event, and the user should not read repeated bullets.
- Report generation uses tiered Bedrock routing.
  Why: Standard favors lower-cost output, Premium favors higher-quality output, and the local template fallback keeps the system working when Bedrock is unavailable.
- The final output is formatted for readability rather than raw JSON.
  Why: the user wants a report, not an internal data dump.

### AgentCore Gateway and MCP Integration Status

Current status in this repository:

- AgentCore gateway is configured in agentcore/agentcore.json as company-intelligence-gateway with an httpRuntime target pointing to runtime MyAgent.
- MCP tooling is active in runtime execution: the orchestrator bootstraps a local MCP server and loads tools through MultiServerMCPClient.
- Parallel agents (research/news/litigation/leadership/financial) accept MCP tool handles and use MCP as a live fallback path when primary providers are unavailable or sparse.
- mcpRuntimeTools are declared in agentcore/agentcore.json and bound to runtime MyAgent.

### Architecture Match to Target Diagram (Excluding Frontend)

Estimated match: approximately 86% for backend architecture, with strongest alignment in orchestration, queueing, persistence, reporting, and MCP-assisted tool execution.

| Diagram Zone | Current Project Status | Match |
|---|---|---|
| Zone 2 - Edge/API Layer | Implemented via API Gateway + ingestion/status/reports Lambdas | High |
| Zone 3 - Async Buffer | Implemented via SQS FIFO + worker/orchestrator trigger | High |
| Zone 4 - LangGraph Orchestration | Implemented with fan-out/fan-in graph and synchronization barrier | High |
| Zone 5 - AgentCore Deployment Layer | Partially implemented. Runtime and gateway config exist, but full AgentCore-managed deployment path is not the default active path | Medium |
| Zone 6 - Cache and Memory Layer | Implemented via DynamoDB cache and optional OpenSearch retrieval | High |
| Zone 7 - Parallel Agent Execution | Implemented with five parallel agents in orchestrator graph | High |
| Zone 8 - Validation Layer | Implemented (validation pipeline present) | High |
| Zone 9 - Synthesis Layer | Implemented (merge, deduplicate, rank/compose) | High |
| Zone 10 - Report Generation | Implemented (tiered model routing and report assembly) | High |
| Zone 11 - Persistence Layer | Implemented via DynamoDB + S3 artifacts | High |
| Zone 12 - Monitoring and Observability | Partially implemented (CloudWatch logs; full AgentCore-native observability is not yet the default path) | Medium |

Main gaps against the diagram:

- AgentCore-native observability and full managed runtime lifecycle are only partially represented in the currently deployed path.
- Some documentation sections still describe deferred AgentCore stack behavior; treat this section as the current source of truth.

### Deployment Model

The repository now uses one merged deployment entrypoint:

- `cdk deploy CompanyIntelligencePlatformV5` provisions the platform infra stack and the AgentCore runtime stacks together.
- The root CDK app in [bin/main.ts](bin/main.ts) synthesizes both the API/queue/storage infrastructure and the AgentCore runtime declared in `agentcore/agentcore.json`.
- The standalone `agentcore/cdk` project still exists as the generated AgentCore CDK scaffold, but the default production path is the merged root deployment.

### Canonical Entry Points

`graph.py` is the central orchestration implementation, but it is not the only external entry point.

- HTTP runtime entry path
  - Route handlers in `agentcore/src/orchestrator/graph.py` accept runtime calls (`/invocations`, `/invoke`, `/`).
- Async pipeline entry path
  - `lambdas/engine-orchestrator/orchestrator_handler.py` is the SQS-triggered Lambda handler that invokes the orchestration pipeline.

So: one core orchestrator graph, multiple ingress paths.

Configuration and deployment model:

- `agentcore/agentcore.json`
  - AgentCore declarative model: runtime, gateway, and `mcpRuntimeTools` definitions.
- `agentcore/project.yaml`
  - High-level project intent and runtime defaults used during project initialization.
- `bin/main.ts`, `lib/platform-infra-stack.ts`
  - CDK infrastructure definition for API + queue + persistence architecture.

### Core Components

| Component | Technology | Purpose |
|---|---|---|
| **graph.py** | LangGraph | StateGraph orchestrator, fan-out/fan-in with 5 parallel agents |
| **Five Agents** | Python + Bedrock | research, news, leadership, litigation, financial |
| **impact.py** | Weighted Scoring | Materiality classifier for negative/positive news ranking |
| **synthesis.py** | Merge + Deduplicate | Combines 5 agent outputs, ranks by impact |
| **generator.py** | Bedrock API | Report generation, tiered model selection |
| **API Layer** | API Gateway + 3 Lambdas | Ingestion, Status, Report Retrieval |
| **Async Queue** | SQS FIFO | Decouples ingestion from orchestration |
| **State Storage** | DynamoDB | run_id index, execution metadata, TTL cleanup |
| **Report Archive** | S3 | Immutable JSON artifacts, versioned |
| **Cache Layer** | DynamoDB + OpenSearch | Agent output caching, optional vector search |

### Data State Machine

```
User Request
    │
    ▼
QUEUED ──────────────────────────────────────────────┐
(request stored in DynamoDB)                        │
    │                                               │
    ├─ [SQS trigger]                                │
    │                                               │
    ▼                                               │
PROCESSING ─────────────────────┐                   │
(LangGraph executing)           │                   │
    │                           │                   │
    ├─ Agents running          │                   │
    ├─ Synthesis happening     │                   │
    ├─ Bedrock generating      │                   │
    ├─ S3 storing artifact     │                   │
    │                           │                   │
    ▼                           │                   │
COMPLETED ◄─────────────────────┘                   │
(Success, report available)                        │
    │                                               │
    └──────────────────────────────────────────────┘
                    ▼
           FAILED (on error)
```

### Deployment Shape

The merged deploy now includes:

- REST API, Lambda functions, SQS, DynamoDB, and S3 from `PlatformInfraStack`.
- AgentCore runtime and gateway resources from `AgentCoreStack`.
- Shared orchestration code path based on the same `agentcore/src/orchestrator/graph.py` implementation.

### Persistence Layer

| Storage | Data | TTL | Access Pattern |
|---|---|---|---|
| **DynamoDB (cip-run-state)** | run_id, company, status, metadata | 7 days | Primary key: run_id |
| **DynamoDB (cip-agent-cache)** | API responses, cached news, litigation, etc. | 24 hours | Primary key: cache_key |
| **S3 (cip-reports-*) | Full report JSON artifacts | Forever (RETAIN) | Key: outputs/{run_id}.json |
| **OpenSearch (optional)** | Vector embeddings + metadata | 24 hours | Query: semantic search by domain |

---

## Quick Start

### 1. Prerequisites

- **Macro-orchestrator:** LangGraph fan-out / fan-in StateGraph with a custom synchronization barrier and 5 parallel agents
- **Report processing:** Materiality-ranked synthesis, Bedrock-based generation with tiered model selection
- **Frontend:** React (`platform-frontend`)
- **Report lifecycle:** Ingest → Async orchestration → Status polling → Full artifact retrieval
- **Persistence:** S3 (immutable artifacts) + DynamoDB (state + cache) + Optional OpenSearch (vector retrieval)


## 1. Local dependencies

### Python (backend)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-worker.txt
pip install -r lambdas/api-ingestion/requirements.txt
pip install -r lambdas/api-status/requirements.txt
pip install agentcore   # AWS Bedrock AgentCore SDK
```

### Node (CDK + frontend)
```bash
npm install -g aws-cdk
npm install            # installs CDK + frontend deps (root package.json)
```

## 2. Initialize the AgentCore project

```bash
agentcore create --config agentcore/project.yaml
agentcore deploy --env dev
```

This registers the five agents declared in `agentcore/agents/` and
wires their gateway credentials from `agentcore/tools/registry.json`
(secrets live in AWS Secrets Manager, not in the agent runtime).

The orchestration runtime source lives under `agentcore/src/`, including
`agentcore/src/orchestrator/graph.py`; this checkout does not use a separate
top-level runtime `src/` directory.

## 3. Run the SQS worker locally with Docker

```bash
docker build -t cip-worker .

docker run --rm \
  -e AWS_REGION=us-east-1 \
  -e INGESTION_QUEUE_URL="https://sqs.us-east-1.amazonaws.com/<account>/cip-ingestion.fifo" \
  -e RUN_STATE_TABLE="cip-run-state" \
  -e CACHE_TABLE="cip-agent-cache" \
  -v ~/.aws:/root/.aws:ro \
  cip-worker
```

## 4. Deploy AWS infrastructure (CDK)

```bash
cdk bootstrap        # one-time per account/region
cdk deploy CompanyIntelligencePlatformV5
```

**CDK provisions:**
- **API Gateway** with three endpoints:
  - `POST /ingest` — Submit company for intelligence gathering
  - `GET /status/{runId}` — Poll execution status (QUEUED → PROCESSING → COMPLETED/FAILED)
  - `GET /reports/{runId}` — Retrieve full report artifact (NEW)
- **Lambdas:** Ingestion, Status, Reports handlers
- **SQS FIFO:** `cip-ingestion.fifo` (DLQ: `cip-ingestion-dlq.fifo`)
- **DynamoDB:** 
  - `cip-run-state` (run_id PK, execution metadata + S3 report location)
  - `cip-agent-cache` (cache_key PK, automatic OpenSearch indexing)
- **S3:** `cip-reports-{account}-{region}` (versioned, encrypted, immutable report artifacts)
- **IAM:** Role granting Bedrock AgentCore, Parameter Store, Secrets Manager, X-Ray, DynamoDB, and S3 access

**After deployment, CDK outputs:**
```
ApiEndpoint: https://<api-id>.execute-api.us-east-1.amazonaws.com/
QueueUrl: https://sqs.us-east-1.amazonaws.com/<account>/cip-ingestion.fifo
ReportsBucketName: cip-reports-<account>-<region>
```

Use the `ApiEndpoint` value as `VITE_API_BASE_URL` in your frontend.

## 5. Frontend API usage

Create a `.env` in the project root (or `platform-frontend/.env`) pointing the React client at the deployed API:

```bash
VITE_API_BASE_URL=https://<api-id>.execute-api.us-east-1.amazonaws.com
```

**Workflow:**
1. **Submit:** `POST {VITE_API_BASE_URL}/ingest` with `{company, country, tier}` → returns `{run_id}`
2. **Poll:** `GET {VITE_API_BASE_URL}/status/{run_id}` until `status === "COMPLETED"`
3. **Fetch:** `GET {VITE_API_BASE_URL}/reports/{run_id}` → full report artifact JSON

**Report artifact structure:**
```json
{
  "run_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "company": "Tesla",
  "country": "USA",
  "tier": "premium",
  "status": "COMPLETED",
  "generated_at": "2026-07-20T12:34:56Z",
  "execution_time_seconds": 45.3,
  "report": {
    "markdown": "# Tesla Executive Summary\n...",
    "sections": {...}
  },
  "metrics": {
    "agent_runtimes": {...},
    "cache_hits": {...}
  },
  "validated": {...},
  "synthesized": {...}
}
```

**Error responses:**
- `404` — Report not found (still processing, check `/status/{run_id}`)
- `500` — S3 or configuration error (check CloudWatch logs)

---

## Troubleshooting

### Issue: Orchestrator Lambda fails with `Runtime.ImportModuleError: cannot import name 'DocumentModifiedShape' from 'botocore.docs.utils'`

**Root cause:** The `bedrock-agentcore` package (v1.18.0) was built against an older version of botocore that exported `DocumentModifiedShape`. Lambda's Python 3.12 runtime has a newer botocore that no longer exports this symbol.

**Status:** This was blocking full AgentCoreStack deployment. Fixed by:
1.  Removing `bedrock_agentcore` from `layers/python/` 
2.  Removing `BedrockAgentCoreApp` import from `graph.py`
3.  Redeploying with `cdk deploy CompanyIntelligencePlatformV5`

**If you still see this error:**

**Fix Option A: Force Lambda layer update (Recommended)**
```bash
# 1. Verify bedrock_agentcore is removed from layers
ls layers/python/ | grep bedrock
# Should output nothing

# 2. Force CDK to rebuild the layer
rm -rf cdk.out/
cdk deploy CompanyIntelligencePlatformV5 --require-approval never

# 3. Test with a new job
curl -X POST https://<api-endpoint>/ingest \
  -d '{"company":"Tesla","country":"USA","tier":"Standard"}' \
  -H "Content-Type: application/json"
```

**Fix Option B: Pin botocore version**
```bash
# In layers/python/requirements.txt:
botocore==1.43.31  # Tested compatible with bedrock-agentcore
bedrock-agentcore==1.18.0

# Rebuild layer
cdk deploy CompanyIntelligencePlatformV5 --require-approval never
```

**Fix Option C: Upgrade bedrock-agentcore**
```bash
# Check for newer version compatible with current botocore
pip index versions bedrock-agentcore

# Update to latest compatible version in layers/python/requirements.txt
bedrock-agentcore==1.20.0  # or later
```

### Verify the fix

```bash
# Check CloudWatch logs for the orchestrator Lambda
aws logs tail /aws/lambda/cip-engine-orchestrator --region ap-south-1 --follow

# You should see:
# - "Received background processing event from SQS Queue"
# - "Invoking Async Custom Parallel StateGraph Engine"
# - No "Runtime.ImportModuleError" messages

# If still failing, check the full error:
aws logs describe-log-streams \
  --log-group-name /aws/lambda/cip-engine-orchestrator \
  --region ap-south-1 --order-by LastEventTime --descending \
  | jq '.logStreams[0].logStreamName'

# Then retrieve that stream:
aws logs get-log-events \
  --log-group-name /aws/lambda/cip-engine-orchestrator \
  --log-stream-name '<stream-name-from-above>' \
  --region ap-south-1
```

**How it works:**
1. Request arrives in Lambda with `{company, country, tier}`
2. All 5 agents start simultaneously (parallel execution)
3. Each agent retrieves data (Tavily → cache fallback → OpenSearch)
4. Results are validated and synthesized
5. Bedrock generates report with tiered model selection
6. S3 stores artifact, DynamoDB records COMPLETED status
7. Frontend polls `/status` until COMPLETED, then `/reports` to fetch

---

## Development

### Local testing of graph.py

```bash
# Install dependencies
pip install -r requirements.txt

# Run a single orchestration cycle
python -c "
import asyncio
from agentcore.src.orchestrator.graph import run_intelligence_pipeline

result = asyncio.run(run_intelligence_pipeline({
    'run_id': 'test-123',
    'company': 'Tesla',
    'country': 'USA',
    'tier': 'Standard'
}))

print(result['report']['markdown'])
"
```

### Running tests

```bash
# Unit tests for components
pytest tests/test_report_focus.py       # Impact scoring
pytest tests/test_retrieval_layer.py    # Cache layer
pytest tests/test_report_reader.py      # Report API

# Integration test (requires AWS creds)
pytest tests/test_api_lifecycle.py      # Full workflow
```

### Modifying agents

Each agent lives in `agentcore/agents/`:
- `research_agent.py` — Company profile
- `news_agent.py` — Headlines + sentiment
- `leadership_agent.py` — Executives + products
- `litigation_agent.py` — Active lawsuits
- `financial_agent.py` — Financial metrics

To add a new data source:
1. Update agent's query string
2. Add Tavily fallback logic (optional)
3. Store results in DynamoDB cache
4. Results automatically flow through synthesis → report

---

## Deployment Summary

| Step | Command | Output | Next |
|---|---|---|---|
| Bootstrap | `cdk bootstrap` | CloudFormation bucket created | Deploy |
| Deploy | `cdk deploy CompanyIntelligencePlatformV5` | API endpoint + queue URL | Test |
| Test | `curl -X POST <api>/ingest ...` | run_id returned | Poll |
| Poll | `curl <api>/status/{runId}` | status: COMPLETED | Retrieve |
| Retrieve | `curl <api>/reports/{runId}` | Full report JSON | Done |

---
#   c o m p a n y - i n t e l l i g e n c e - p l a t f o r m  
 