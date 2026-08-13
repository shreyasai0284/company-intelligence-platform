## External Data APIs — Setup & Configuration Guide

All external API integrations are **optional fallback layers**. The system works without them, but they provide richer data when available.

### Quick Start

No setup required for MVP — agents work with Tavily + DynamoDB cache. To enable external APIs, follow below.

---

## 1. GDELT (Global Events Database)

**What it provides:** Free global events database updated hourly. No authentication required.

**When used:** 
- news_agent.py: Breaking news fallback when Tavily unavailable
- research_agent.py: Company event context when Tavily unavailable

**Setup:** 
- ✅ No setup required — automatically called if news_agent fails Tavily fetch
- Returns 10 most recent events for company + country in past 30 days

**Example:**
```python
from agentcore.agents._external_apis import fetch_gdelt_events

events = fetch_gdelt_events(
    company="Samsung",
    country="USA",
    days_back=30
)
# Returns: [{"title": "...", "content": "...", "url": "...", "source": "GDELT"}, ...]
```

---

## 2. CourtListener (Active Litigation API)

**What it provides:** Structured legal database with active court cases.

**When used:**
- litigation_agent.py: Case details fallback when Tavily unavailable

**Setup:**
1. Register free account: https://www.courtlistener.com/api/
2. Get API key from: https://www.courtlistener.com/api/rest-info/
3. Set environment variable:
   ```bash
   export COURTLISTENER_API_KEY="your_api_key_here"
   ```
4. Verify in Lambda:
   - Add to `lambdas/engine-orchestrator/requirements.txt`: (requests already included)
   - Deploy: `cdk deploy CompanyIntelligencePlatformV5`

**Example:**
```python
from agentcore.agents._external_apis import fetch_courtlistener_cases

# Requires COURTLISTENER_API_KEY env var
cases = fetch_courtlistener_cases(
    company="Samsung",
    country="USA"
)
# Returns: [{"title": "Case Name (Court)", "content": "...", "url": "...", "source": "CourtListener"}, ...]
```

**Rate Limit:** 1 request/second (free tier)

---

## 3. SEC XBRL (Financial Filings)

**What it provides:** Official SEC filings (10-K, 10-Q, 8-K). Free public API via Edgar.

**When used:**
- financial_agent.py: Financial detail fallback for public companies without ticker match

**Setup:**
- ✅ No authentication required
- Works automatically when financial_agent encounters unlisted/private company
- Looks up CIK (Central Index Key) via company name
- Fetches most recent 10-K, 10-Q, 8-K filings

**Example:**
```python
from agentcore.agents._external_apis import fetch_sec_filings

filings = fetch_sec_filings(
    company="Apple Inc",
    country="USA",
    filing_types=["10-K", "10-Q", "8-K"]
)
# Returns: [{"title": "SEC 10-K filing - 2025-12-31", "content": "...", "url": "...", "source": "SEC Edgar"}, ...]
```

**Rate Limit:** 10 requests/second (free)

---

## 4. Knowledge Base Ingestion Pipeline

**What it provides:** Pre-ingested internal company documents, research, custom knowledge.

**When used:**
- All agents: Last-resort fallback when external APIs unavailable
- Provides company-specific context beyond web search

**Setup — Manual Ingestion During Platform Init:**

```python
from agentcore.agents._cache import cache_put

# Initialize knowledge base (run once during platform setup)
knowledge_docs = [
    {
        "title": "Q4 2025 Earnings Report",
        "content": "Revenue: $500M, YoY growth: 25%...",
        "url": "internal://earnings-q4-2025"
    },
    {
        "title": "Product Roadmap 2026",
        "content": "Q1: Launch AI features, Q2: Expand to Asia...",
        "url": "internal://product-roadmap"
    },
    {
        "title": "Executive Team Updates",
        "content": "New CTO: Jane Doe...",
        "url": "internal://executive-updates"
    },
]

# Company profile domain
company = "Samsung"
country = "South Korea"

# Ingest into knowledge base
for doc in knowledge_docs:
    cache_put(
        key=f"{company}#{country}#RESEARCH#{doc['title']}",
        payload={
            "articles": [doc],
            "recent_headlines": [doc["title"]],
            "profile": {
                "summary": doc["content"][:200],
                "sources": [{"title": doc["title"], "url": doc["url"]}],
            },
        },
        ttl_seconds=86400 * 30  # 30 day TTL
    )

# News domain
for doc in knowledge_docs:
    cache_put(
        key=f"{company}#{country}#NEWS#{doc['title']}",
        payload={
            "recent_headlines": [doc["title"]],
            "sentiment_score": 0.5,
            "headline_sources": [{"title": doc["title"], "content": doc["content"][:500], "url": doc["url"]}],
        },
        ttl_seconds=86400 * 30
    )

# Litigation domain
litigation_docs = [
    {"title": "Trademark dispute in Japan (2025)", "content": "Resolved in favor..."},
]
for doc in litigation_docs:
    cache_put(
        key=f"{company}#{country}#LITIGATION#{doc['title']}",
        payload={
            "cases": [doc["title"]],
            "active_count": 0,
        },
        ttl_seconds=86400 * 30
    )
```

**Or use REST API to ingest:**
```bash
# POST to Lambda + SQS (future feature)
curl -X POST https://.../ingest-knowledge \
  -H "Content-Type: application/json" \
  -d '{
    "company": "Samsung",
    "country": "South Korea",
    "documents": [...],
    "ttl_days": 30
  }'
```

**Retrieval:** Agents call `fetch_from_knowledge_base()` automatically on fallback.

---

## Integration Architecture

### Fallback Chain Per Agent

Each agent follows this priority order:

```
1. Check DynamoDB cache (fast, expired after TTL)
   ↓ [MISS]
2. Try primary source (Tavily or yfinance)
   ↓ [EMPTY/FAIL]
3. Try external API (GDELT, CourtListener, SEC)
   ↓ [EMPTY/FAIL]
4. Try knowledge base
   ↓ [EMPTY/FAIL]
5. Try semantic search on cache
   ↓ [EMPTY]
6. Return empty/placeholder result
```

### Code Integration Points

**news_agent.py:**
```python
# Lines 80-90: Added GDELT fallback
gdelt_records = fetch_gdelt_events(company, country, days_back=30)
if gdelt_records:
    live_records.extend(gdelt_records)
```

**litigation_agent.py:**
```python
# Lines 50-58: Added CourtListener fallback
cl_cases = fetch_courtlistener_cases(company, country)
if cl_cases:
    case_results.extend([case.get("title", "") for case in cl_cases])
```

**financial_agent.py:**
```python
# Lines 140-155: Added SEC + KB fallback for unlisted companies
sec_filings = fetch_sec_filings(company, country)
if sec_filings:
    mcp_insight = f"SEC filings: {len(sec_filings)} recent filings..."
```

**research_agent.py:**
```python
# Lines 85-110: Added GDELT + KB fallback
gdelt_records = fetch_gdelt_events(company, country, days_back=30)
kb_records = fetch_from_knowledge_base(company, country, "RESEARCH")
```

---

## Environment Variables

Add to `.env` or Lambda environment:

```bash
# Optional: CourtListener authentication
COURTLISTENER_API_KEY=your_api_key

# Optional: Tavily API (primary, already supported)
TAVILY_API_KEY=your_tavily_key

# Optional: GDELT configuration (defaults to 30 days)
GDELT_LOOKBACK_DAYS=30

# Optional: SEC Edgar user agent (defaults to platform user agent)
SEC_EDGAR_USER_AGENT="CompanyIntelligencePlatform/1.0"
```

---

## Deployment

### 1. Update requirements.txt (already included):
```bash
# No new dependencies needed
# requests is already in Lambda layer
```

### 2. Redeploy Lambda:
```bash
cdk deploy CompanyIntelligencePlatformV5 --require-approval never
```

### 3. Verify in CloudWatch logs:
```bash
aws logs tail /aws/lambda/cip-engine-orchestrator --region ap-south-1 --since 5m | grep -E "GDELT|CourtListener|SEC|KB"
```

---

## Monitoring & Debugging

### Check which API was used in logs:

```bash
# Check news_agent
aws logs filter-log-events \
  --log-group-name /aws/lambda/cip-engine-orchestrator \
  --filter-pattern "GDELT fallback returned"

# Check litigation_agent
aws logs filter-log-events \
  --log-group-name /aws/lambda/cip-engine-orchestrator \
  --filter-pattern "CourtListener fallback"

# Check financial_agent
aws logs filter-log-events \
  --log-group-name /aws/lambda/cip-engine-orchestrator \
  --filter-pattern "SEC fallback"
```

### Test locally:

```python
# Test GDELT
from agentcore.agents._external_apis import fetch_gdelt_events
events = fetch_gdelt_events("Apple", "USA", days_back=7)
print(f"GDELT: {len(events)} events")

# Test CourtListener (requires API key)
import os
os.environ["COURTLISTENER_API_KEY"] = "your_key"
from agentcore.agents._external_apis import fetch_courtlistener_cases
cases = fetch_courtlistener_cases("Microsoft", "USA")
print(f"CourtListener: {len(cases)} cases")

# Test SEC
from agentcore.agents._external_apis import fetch_sec_filings
filings = fetch_sec_filings("Tesla", "USA")
print(f"SEC: {len(filings)} filings")
```

---

## Performance Considerations

| API | Latency | Rate Limit | Cost | Recommended Use |
|-----|---------|-----------|------|-----------------|
| GDELT | 2-5s | Unlimited | Free | Always-on fallback |
| CourtListener | 1-3s | 1/sec | Free | Litigation focus |
| SEC Edgar | 3-8s | 10/sec | Free | Financial detail |
| Knowledge Base | <100ms | N/A | Free | Fastest fallback |

**Timeout:** All external APIs have 10-second timeout. If slower, agent continues to next fallback.

---

## Disabling an API

To disable an API without removing code:

```python
# In agent function, wrap call:
if os.getenv("ENABLE_GDELT") != "false":
    gdelt_records = fetch_gdelt_events(company, country)
```

Or comment out the import:
```python
# from ._external_apis import fetch_gdelt_events  # DISABLED
```

---

## Future Enhancements

- [ ] Streaming results from external APIs (real-time updates)
- [ ] Caching external API responses to reduce latency
- [ ] Hybrid search: combine keyword + semantic scoring
- [ ] Custom data source integration (company APIs, data lakes)
- [ ] Batch ingestion UI for knowledge base documents
