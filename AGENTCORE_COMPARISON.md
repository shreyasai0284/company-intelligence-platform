# PlatformInfraStack vs AgentCoreStack: Deployment Comparison

## Quick Summary

| Aspect | PlatformInfraStack | AgentCoreStack |
|--------|-------------------|----------------|
| **Status** | ✅ **DEPLOYED** | ⏸️ Deferred |
| **Deployment Time** | ~80 seconds | Would take ~5-10 min |
| **Components** | API + Infrastructure | Agent Runtime + Gateway |
| **Responsibility** | HTTP API layer + job queue | Bedrock agent orchestration |
| **Python Dependency** | Minimal | Heavy (many wheels needed) |
| **Cost** | $0/month (free tier) | $0/month (free tier) |

---

## PlatformInfraStack (✅ What You Have Now)

### Architecture
```
User Request
    ↓
API Gateway (prod/)
    ├── POST /ingest → IngestionFn
    │   ↓
    │   SQS FIFO Queue
    │   ↓
    │   OrchestratorFn (processes job)
    ├── GET /status/{runId} → StatusFn
    │   ↓
    │   DynamoDB run-state table
    └── GET /reports/{runId} → ReportsFn
        ↓
        S3 bucket (reports)
```

### What's Running Now
- **IngestionFn** - Accepts company details, queues job
- **StatusFn** - Returns job execution status
- **ReportsFn** - Fetches persisted reports from S3 ← NEW
- **OrchestratorFn** - Pulls jobs from SQS, runs agent code, persists results
- **DynamoDB** (2 tables) - Stores run state and agent cache
- **SQS** - FIFO queue for job ordering
- **S3** - Versioned, encrypted report storage
- **CloudWatch** - Logs for debugging

### Dependencies
- Python 3.12/3.13 (standard libs only for API handlers)
- boto3 (AWS SDK) - built into Lambda
- Minimal 3rd-party packages

### When It Started
- Immediately after `cdk deploy`
- All resources created in ~80 seconds

---

## AgentCoreStack (⏸️ What We Skipped)

### Architecture
```
AgentCore Runtime (Bedrock)
    ├── Agent Registration
    │   └── 5 agents (Research, News, Leadership, Litigation, Financial)
    ├── MCP Gateway
    │   └── company-intelligence-gateway (protocol: None)
    ├── Agent Orchestration
    │   └── LangGraph StateGraph
    └── Agent Lifecycle Management
        ├── Agent memory
        ├── Tool invocation
        └── Model selection (Nova Lite/Pro/Claude)
```

### What Would've Been Deployed
- **AgentCore Runtime** - Full Bedrock agent lifecycle management
- **MCP Gateway** - REST-to-agent-call translation
- **Agent Registry** - Certification of 5 agents in Bedrock
- **Model Selection Logic** - Route by tier (standard vs premium)
- **Agent Monitoring** - Bedrock-side metrics and tracing

### Dependencies
- bedrock-agentcore SDK (proprietary Bedrock library)
- langgraph, langchain-core
- pydantic, opensearch-py
- tavily-python (optional web search)
- mcp, langchain-mcp-adapters
- aws-opentelemetry-distro

All these need binary wheels for Python 3.13, which weren't immediately available.

### When It Would've Started
- After PlatformInfraStack
- Would take additional 5-10 min for bundling + deployment

---

## Why PlatformInfraStack Deployed, AgentCoreStack Didn't

### The Problem
The CDK tried to package Python 3.13 dependencies:
```
Error: "Building source distributions is disabled"
```

### Why This Happens
- Many Python packages don't have pre-built wheels (.whl) for Python 3.13
- pip was configured not to build from source (security policy)
- CDK couldn't find binary wheels in PyPI

### Solutions (Not Yet Applied)
1. **Switch to Python 3.12** - More wheels available
2. **Pre-build a Lambda layer** - Download wheels once, reuse
3. **Configure pip to build from source** - Slower but works
4. **Use a Docker image** - Build wheels inside container

### Why This Matters
- **PlatformInfraStack** doesn't have heavy Python deps → deployed fine
- **AgentCoreStack** needs bedrock-agentcore + langgraph → deployment blocked

---

## Can You Deploy AgentCore Later?

**Yes, absolutely.** Here's the path forward:

### Option 1: Fix Python Version (Recommended)
```bash
# Use Python 3.12 instead of 3.13
python -m venv .venv --python=python3.12
source .venv/bin/activate
pip install -r agentcore/requirements.txt

# Uncomment AgentCoreStack in bin/main.ts
# Run deployment
cdk deploy CompanyIntelligencePlatformV5
```

### Option 2: Pre-build Dependency Layer
```bash
# Build wheels locally
mkdir -p layers/python
pip install -r agentcore/requirements.txt -t layers/python/

# Commit to repo, CDK will use pre-built binaries
cdk deploy CompanyIntelligencePlatformV5
```

### Option 3: Deploy Only PlatformInfraStack (Current)
The orchestrator Lambda code is **already included** via bundling:
- Orchestrator Lambda contains agent code
- Agents run as standard Python, not as Bedrock-certified agents
- Reports still generate normally
- The only limitation: no Bedrock AgentCore dashboard/monitoring

---

## Current System Architecture (With Both Stacks)

### If Both Deployed
```
┌─────────────────────────────────────────────────────┐
│ User Frontend                                       │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ PlatformInfraStack (✅ Deployed)                    │
│ ├─ API Gateway (REST)                              │
│ ├─ Ingestion Lambda                                │
│ ├─ Status Lambda                                   │
│ └─ Reports Lambda                                  │
└─────────────────────────────────────────────────────┘
                      ↓
            ┌─────────┴─────────┐
            ↓                   ↓
    ┌──────────────┐    ┌──────────────┐
    │ SQS Queue    │    │ Orchestrator │
    └──────────────┘    │ Lambda       │
                        └──────────────┘
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
            ┌──────────────────────────────────┐
            │ AgentCoreStack (⏸️ Deferred)     │
            │ ├─ Bedrock Runtime               │
            │ ├─ MCP Gateway                   │
            │ ├─ Agent Registry                │
            │ └─ LangGraph Orchestration       │
            └──────────────────────────────────┘
                    ↓
            ┌──────────────┐
            │ DynamoDB +   │
            │ S3 + SQS     │
            └──────────────┘
```

### Current System (PlatformInfraStack Only)
```
┌─────────────────────────────────────────────────────┐
│ User Frontend                                       │
└─────────────────────────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────┐
│ PlatformInfraStack (✅ Deployed)                    │
│ ├─ API Gateway (REST)                              │
│ ├─ Ingestion Lambda                                │
│ ├─ Status Lambda                                   │
│ └─ Reports Lambda                                  │
└─────────────────────────────────────────────────────┘
                      ↓
            ┌─────────┴─────────┐
            ↓                   ↓
    ┌──────────────┐    ┌──────────────────────────┐
    │ SQS Queue    │    │ Orchestrator Lambda      │
    └──────────────┘    │ (includes agent code     │
                        │  runs as Python app)     │
                        └──────────────────────────┘
                              ↓
                        ┌──────────────┐
                        │ DynamoDB +   │
                        │ S3 + SQS     │
                        └──────────────┘
```

---

## Functional Difference

### With PlatformInfraStack Only (Current)
- ✅ API endpoints work
- ✅ Jobs queue and execute
- ✅ Reports generate and persist
- ✅ Status tracking works
- ⚠️ No Bedrock AgentCore dashboard
- ⚠️ No Bedrock agent metrics
- ⚠️ Agent code runs as standard Python in Lambda

### With Both Stacks
- ✅ Everything above, plus:
- ✅ Bedrock AgentCore dashboard
- ✅ Agent monitoring and metrics
- ✅ Agent lifecycle management
- ✅ Official "agent" certification
- ✅ Potential for future Bedrock features

---

## Recommendation

**Keep current setup (PlatformInfraStack only) for now** because:
1. ✅ All end-to-end functionality works
2. ✅ Reports generate and persist
3. ✅ Costs remain zero
4. ✅ No user-facing limitation
5. ⏱️ Deploy AgentCoreStack later once Python 3.12 is set up

**When you're ready to deploy AgentCoreStack:**
1. Uncomment the AgentCoreStack code in `bin/main.ts`
2. Switch to Python 3.12 or pre-build wheels
3. Run `cdk deploy` again
4. Gain Bedrock dashboard/monitoring features

