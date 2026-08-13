# How to Test the Live AWS API - Step by Step

## The Confusion Explained

**The Problem:** You clicked the API link → got "Missing Authentication Token"

**The Reality:** 
- Your API is working fine ✅
- The error is misleading (it's not auth, it's HTTP method)
- Browsers do GET by default, /ingest only accepts POST
- You need to use a tool that can send POST requests with a JSON body

---

## Method 1: PowerShell (What You Have Now)

### Step 1: Submit a Job
```powershell
$endpoint = "https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod"

$body = @{
    company = "Tesla"
    country = "USA"
    tier = "standard"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "$endpoint/ingest" -Method POST `
  -Body $body -ContentType "application/json"

$runId = $response.run_id
Write-Host "Job submitted! Run ID: $runId"
Write-Host "Status: $($response.status)"
```

**Expected Output:**
```
Job submitted! Run ID: 550e8400-e29b-41d4-a716-446655440000
Status: QUEUED
```

### Step 2: Check Status (while job runs)
```powershell
$statusUrl = "$endpoint/status/$runId"
$status = Invoke-RestMethod -Uri $statusUrl

Write-Host "Current Status: $($status.status)"
Write-Host "Execution Time: $($status.execution_time_seconds)s"
Write-Host "Report Location: $($status.report_url)"
```

**Expected Output (while processing):**
```
Current Status: PROCESSING
Execution Time: 23.5s
Report Location: s3://cip-reports-704134886191-ap-south-1/outputs/550e8400-e29b-41d4-a716-446655440000.json
```

### Step 3: Fetch the Report (after COMPLETED)
```powershell
# Wait for status to be COMPLETED, then:
$reportUrl = "$endpoint/reports/$runId"
$report = Invoke-RestMethod -Uri $reportUrl

Write-Host "Report Generated!"
Write-Host "Company: $($report.company)"
Write-Host "Status: $($report.status)"
Write-Host "Generated At: $($report.generated_at)"
Write-Host ""
Write-Host "Report Markdown (first 200 chars):"
Write-Host $report.report.markdown.Substring(0, 200)
```

**Expected Output:**
```
Report Generated!
Company: Tesla
Status: COMPLETED
Generated At: 2026-07-20T03:15:22Z

Report Markdown (first 200 chars):
# Tesla - Executive Summary

## Key Risks
- Regulatory investigation into vehicle safety practices
- Litigation: Class action lawsuit filed in Q3 2026
...
```

---

## Method 2: Full Testing Script (PowerShell)

Save this as `test-api.ps1`:

```powershell
#!/usr/bin/env pwsh

$endpoint = "https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Company Intelligence Platform - API Test" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Submit Job
Write-Host "[1/3] Submitting job..." -ForegroundColor Yellow
$body = @{
    company = "Apple"
    country = "USA"
    tier = "premium"
} | ConvertTo-Json

$ingestResp = Invoke-RestMethod -Uri "$endpoint/ingest" -Method POST `
  -Body $body -ContentType "application/json"

$runId = $ingestResp.run_id
Write-Host "✅ Job Submitted" -ForegroundColor Green
Write-Host "   Run ID: $runId"
Write-Host "   Initial Status: $($ingestResp.status)"
Write-Host ""

# 2. Poll Status
Write-Host "[2/3] Waiting for completion (polling status)..." -ForegroundColor Yellow
$maxWait = 300  # 5 minutes
$elapsed = 0
$pollInterval = 5  # 5 seconds

while ($elapsed -lt $maxWait) {
    Start-Sleep -Seconds $pollInterval
    $statusResp = Invoke-RestMethod -Uri "$endpoint/status/$runId"
    
    Write-Host "   Status: $($statusResp.status) | Elapsed: ${elapsed}s"
    
    if ($statusResp.status -eq "COMPLETED" -or $statusResp.status -eq "FAILED") {
        break
    }
    
    $elapsed += $pollInterval
}

if ($statusResp.status -eq "COMPLETED") {
    Write-Host "✅ Job Completed" -ForegroundColor Green
    Write-Host "   Execution Time: $($statusResp.execution_time_seconds)s"
} else {
    Write-Host "❌ Job Failed or Timeout" -ForegroundColor Red
    Write-Host "   Status: $($statusResp.status)"
    exit 1
}
Write-Host ""

# 3. Fetch Report
Write-Host "[3/3] Fetching Report..." -ForegroundColor Yellow
$reportResp = Invoke-RestMethod -Uri "$endpoint/reports/$runId"

Write-Host "✅ Report Retrieved" -ForegroundColor Green
Write-Host "   Company: $($reportResp.company)"
Write-Host "   Tier: $($reportResp.tier)"
Write-Host "   Generated: $($reportResp.generated_at)"
Write-Host ""
Write-Host "Report Preview:" -ForegroundColor Cyan
Write-Host $reportResp.report.markdown.Substring(0, 500)
Write-Host "..."
Write-Host ""

Write-Host "========================================" -ForegroundColor Green
Write-Host "✅ Full cycle complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
```

Run it:
```powershell
./test-api.ps1
```

---

## Method 3: Using curl (Windows 10+)

### Test Submit Job
```bash
curl -X POST https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/ingest ^
  -H "Content-Type: application/json" ^
  -d "{\"company\":\"Tesla\",\"country\":\"USA\",\"tier\":\"standard\"}"
```

Response:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "QUEUED"
}
```

### Test Check Status
```bash
curl https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/status/550e8400-e29b-41d4-a716-446655440000
```

### Test Get Report
```bash
curl https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/reports/550e8400-e29b-41d4-a716-446655440000
```

---

## Method 4: Using Postman (GUI)

1. **Download Postman** from https://www.postman.com/downloads/
2. **Create a new request:**
   - Method: `POST`
   - URL: `https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/ingest`
   - Headers: `Content-Type: application/json`
   - Body (raw JSON):
     ```json
     {
       "company": "Google",
       "country": "USA",
       "tier": "premium"
     }
     ```
3. **Click Send** → See `run_id` in response
4. **Create second request:**
   - Method: `GET`
   - URL: `https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/status/{runId}`
   - Click Send → Monitor status
5. **When COMPLETED, create third request:**
   - Method: `GET`
   - URL: `https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod/reports/{runId}`
   - Click Send → See full report JSON

---

## What Happens Behind the Scenes

```
Your Request (1)
    ↓
API Gateway receives POST /ingest
    ↓
Ingestion Lambda validates JSON
    ↓
Lambda writes to SQS queue (QUEUED)
    ↓
Returns run_id to you ✅
    ↓
[Time: 1-2 seconds]
    ↓
Orchestrator Lambda picks up SQS message
    ↓
Orchestrator Lambda runs 5 agents in parallel
    ├─ Research Agent (company profile)
    ├─ News Agent (headlines + sentiment)
    ├─ Litigation Agent (active cases)
    ├─ Leadership Agent (executives)
    └─ Financial Agent (financial analysis)
    ↓
Agents query Tavily OR cache (PROCESSING)
    ↓
Results synthesized and ranked
    ↓
Report generated with Bedrock
    ↓
Full artifact written to S3
    ↓
Status updated to COMPLETED ✅
    ↓
Your GET /reports/{runId} gets full JSON
```

**Total time:** 30-120 seconds depending on live search API latency

---

## Testing Right Now - Live Example

### Copy-paste this into PowerShell:

```powershell
$ep = "https://q5ufgq5sc5.execute-api.ap-south-1.amazonaws.com/prod"
$job = Invoke-RestMethod -Uri "$ep/ingest" -Method POST -Body '{"company":"Tesla","country":"USA","tier":"standard"}' -ContentType "application/json"
Write-Host "Run ID: $($job.run_id)`nStatus: $($job.status)"
```

**You'll see:**
```
Run ID: 550e8400-e29b-41d4-a716-446655440000
Status: QUEUED
```

Then wait 30 seconds and check status:
```powershell
$status = Invoke-RestMethod -Uri "$ep/status/550e8400-e29b-41d4-a716-446655440000"
$status | ConvertTo-Json
```

---

## Why You DON'T Need AgentCore to Use the System

| Feature | PlatformInfraStack Only | With AgentCore |
|---------|------------------------|----------------|
| Submit job via API | ✅ YES | ✅ YES |
| Get reports | ✅ YES | ✅ YES |
| Agent execution | ✅ YES (Python) | ✅ YES (Bedrock certified) |
| Dashboard/monitoring | ❌ NO | ✅ YES |
| User-facing functionality | ✅ COMPLETE | ✅ COMPLETE |

**You have a fully working system RIGHT NOW.** AgentCore is just optional monitoring/certification.

---

## TL;DR

**The "Missing Authentication Token" error:**
- ❌ NOT an authentication problem
- ✅ Just API Gateway saying "can't GET /ingest, it's POST only"

**How to test:**
1. Use PowerShell Invoke-RestMethod (included with Windows)
2. Or use curl (Windows 10+)
3. Or use Postman (GUI)
4. Do NOT try to visit the URL in a browser

**Do you need AgentCore?**
- ❌ NO - everything works without it
- ✅ Deploy it later for Bedrock dashboard (optional)

**Your system is live and ready to use. Test it with the PowerShell script above.**
