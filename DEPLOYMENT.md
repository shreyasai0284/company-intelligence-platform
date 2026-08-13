## AWS Deployment Checklist

### What's New & Needs Deploying

**New in this session:**
- ✅ Report-reader Lambda handler (`lambdas/api-reports/handler.py`)
- ✅ S3 reports bucket (already defined in CDK, needs deployment)
- ✅ API Gateway route: `GET /reports/{runId}`
- ✅ Impact classifier for report quality (`agentcore/src/processing/impact.py`)
- ✅ Retrieval layer with OpenSearch indexing (`agentcore/agents/_cache.py`)
- ✅ All 5 domain agents hardened with cache fallback + optional imports
- ✅ Gateway baseline in agentcore.json + CDK wiring

**Deployment command:**
```bash
cdk deploy CompanyIntelligencePlatformV5
```

This will:
1. Create/update S3 bucket: `cip-reports-{account}-{region}` (versioned, encrypted, private)
2. Deploy 4 Lambdas: ingestion, status, reports, orchestrator
3. Create SQS queue + DLQ
4. Create 2 DynamoDB tables with TTL
5. Set up API Gateway with 3 routes
6. Configure IAM roles with Bedrock, S3, DynamoDB, SQS permissions

### Pre-Deployment Verification

**Already done:**
- ✅ All Python files compile without syntax errors
- ✅ All 11 unit tests passing (report, focus, retrieval)
- ✅ TypeScript CDK builds successfully
- ✅ No unresolved imports (Tavily uses importlib)

**Before `cdk deploy`:**
```bash
# 1. Verify AWS credentials
aws sts get-caller-identity

# 2. Check CDK can synthesize (generates CloudFormation)
cdk synth CompanyIntelligencePlatformV5

# 3. Check for differences (what will change)
cdk diff CompanyIntelligencePlatformV5

# 4. Deploy
cdk deploy CompanyIntelligencePlatformV5
```

### Post-Deployment

After `cdk deploy` completes:

1. **Capture outputs**
   - API Endpoint URL → Use as `VITE_API_BASE_URL`
   - Reports bucket name → Verify it exists in S3 console
   - Queue URL → For orchestrator Lambda env vars

2. **Test the API**
   ```bash
   # Check ingestion
   curl -X POST https://<api-endpoint>/ingest \
     -H "Content-Type: application/json" \
     -d '{"company": "Tesla", "country": "USA", "tier": "standard"}'
   
   # Should return: {"run_id": "..."}
   
   # Check status (replace with actual run_id)
   curl https://<api-endpoint>/status/<run_id>
   
   # Check reports (after completion)
   curl https://<api-endpoint>/reports/<run_id>
   ```

3. **Monitor Orchestrator Lambda**
   - CloudWatch Logs: `/aws/lambda/cip-engine-orchestrator`
   - Check for errors in LangGraph execution
   - Verify S3 artifacts are being written to `cip-reports-{account}-{region}/outputs/`

### Environment Variables (Already in CDK)

The CDK stack automatically injects:
- `REPORTS_BUCKET` → Reports Lambda
- `RUN_STATE_TABLE` → Status + Ingestion Lambdas
- `AGENT_CACHE_TABLE` → Orchestrator Lambda
- `INGESTION_QUEUE_URL` → Ingestion Lambda

### Optional Post-Deployment Enhancements

**Not yet implemented (future phases):**
1. **Semantic embeddings** - Use Bedrock embedding models for true vector similarity
2. **Observability** - CloudWatch metrics for agent latency, retrieval hit rates
3. **Report cleanup** - S3 lifecycle policies to archive/delete old reports
4. **Access control** - Cognito or API key authentication on report reads
5. **Frontend updates** - React components to fetch and display reports

### Rollback

If something goes wrong:
```bash
# See what would be destroyed
cdk destroy --dry-run CompanyIntelligencePlatformV5

# Destroy (only deletes CloudFormation stack; S3/DynamoDB retained by RemovalPolicy.RETAIN)
cdk destroy CompanyIntelligencePlatformV5
```

**Note:** DynamoDB tables and S3 buckets have `RemovalPolicy.RETAIN`, so they survive stack deletion.

### Cost Implications

**Monthly estimate (light usage):**
- API Gateway: ~$1 (free tier covers 1M requests)
- Lambda (4 functions @ 256MB, ~1s avg): ~$5
- DynamoDB (on-demand): ~$2-5
- S3: ~$1 (storage) + data transfer
- SQS: <$1 (free tier)
- Bedrock: ~$100-500 (depends on model + token usage)

**No charges for:**
- OpenSearch if left unused (optional feature)
- Parameters Store/Secrets Manager (free tier)

Total: **~$100-600/month** depending on API volume and LLM usage tier.
