import { Construct } from "constructs";
import { Stack, StackProps, Duration, RemovalPolicy, CfnOutput } from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as lambdaEventSources from "aws-cdk-lib/aws-lambda-event-sources";
import * as apigw from "aws-cdk-lib/aws-apigateway";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as iam from "aws-cdk-lib/aws-iam";
import * as logs from "aws-cdk-lib/aws-logs";
import * as path from "path";
import * as fs from 'fs';
import * as cdk from 'aws-cdk-lib';

export class PlatformInfraStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // 1. DynamoDB Tables
    const cacheTable = new dynamodb.Table(this, "AgentCacheTable", {
      tableName: "cip-agent-cache",
      partitionKey: { name: "cache_key", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "ttl",
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: RemovalPolicy.RETAIN,
    });

    const runStateTable = new dynamodb.Table(this, "RunStateTable", {
      tableName: "cip-run-state",
      partitionKey: { name: "run_id", type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      timeToLiveAttribute: "ttl",
      removalPolicy: RemovalPolicy.RETAIN,
    });

    // 2. SQS Queues
    const dlq = new sqs.Queue(this, "IngestionDLQ", { queueName: "cip-ingestion-dlq.fifo", fifo: true, retentionPeriod: Duration.days(14) });
    const ingestionQueue = new sqs.Queue(this, "IngestionQueue", {
      queueName: "cip-ingestion.fifo",
      fifo: true,
      visibilityTimeout: Duration.minutes(15),
      retentionPeriod: Duration.days(4),
      deadLetterQueue: { queue: dlq, maxReceiveCount: 3 },
    });

    // 3. IAM Role
    const lambdaRole = new iam.Role(this, "PlatformLambdaRole", {
      assumedBy: new iam.ServicePrincipal("lambda.amazonaws.com"),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"),
        iam.ManagedPolicy.fromAwsManagedPolicyName("AWSXRayDaemonWriteAccess"),
      ],
    });
    cacheTable.grantReadWriteData(lambdaRole);
    runStateTable.grantReadWriteData(lambdaRole);
    ingestionQueue.grantSendMessages(lambdaRole);

    // 4. Lambdas with explicit log groups
    const ingestionFn = new lambda.Function(this, "ApiIngestionFn", {
      functionName: "cip-api-ingestion",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "ingestion_handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "lambdas", "api-ingestion")),
      role: lambdaRole,
      logGroup: new logs.LogGroup(this, "IngestionLogs", { logGroupName: "/aws/lambda/cip-api-ingestion", retention: logs.RetentionDays.TWO_WEEKS, removalPolicy: RemovalPolicy.DESTROY }),
      environment: { INGESTION_QUEUE_URL: ingestionQueue.queueUrl, RUN_STATE_TABLE: runStateTable.tableName },
    });

    const statusFn = new lambda.Function(this, "ApiStatusFn", {
      functionName: "cip-api-status",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "lambdas", "api-status")),
      role: lambdaRole,
      logGroup: new logs.LogGroup(this, "StatusLogs", { logGroupName: "/aws/lambda/cip-api-status", retention: logs.RetentionDays.TWO_WEEKS, removalPolicy: RemovalPolicy.DESTROY }),
      environment: { RUN_STATE_TABLE: runStateTable.tableName },
    });

    const reportsFn = new lambda.Function(this, "ApiReportsFn", {
      functionName: "cip-api-reports",
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "lambdas", "api-reports")),
      role: lambdaRole,
      logGroup: new logs.LogGroup(this, "ReportsLogs", { logGroupName: "/aws/lambda/cip-api-reports", retention: logs.RetentionDays.TWO_WEEKS, removalPolicy: RemovalPolicy.DESTROY }),
      environment: { REPORTS_DIR: "/tmp/reports" },
    });

    const dependencyLayer = new lambda.LayerVersion(this, "PlatformDependencyLayer", {
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "layers")),
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_12],
    });

  
    // Orchestrator Lambda
    const orchestratorFn = new lambda.Function(this, "EngineOrchestratorFn", {
      functionName: "cip-engine-orchestrator",
      runtime: lambda.Runtime.PYTHON_3_12,
      timeout: cdk.Duration.seconds(900), 
      memorySize: 512,
      code: lambda.Code.fromAsset(path.join(__dirname, "..", "lambdas", "engine-orchestrator"), {
        bundling: {
          local: {
            tryBundle(outputDir: string) {
              try {
                const handlerDir = path.join(__dirname, "..", "lambdas", "engine-orchestrator");
                const agentCoreSrcDir = path.join(__dirname, "..", "agentcore", "src");
                
                // Copy handler to root of zip
                fs.cpSync(handlerDir, outputDir, { recursive: true });
                // Copy core logic to 'src' folder inside zip
                fs.cpSync(agentCoreSrcDir, path.join(outputDir, "src"), { recursive: true });
                
                return true;
              } catch (e) {
                console.error("Local bundling failed: ", e);
                return false;
              }
            }
          }
        }
      }as any),
      handler: "orchestrator_handler.handler",
      role: lambdaRole,
      layers: [dependencyLayer],
      logGroup: new logs.LogGroup(this, "OrchestratorLogs", { logGroupName: "/aws/lambda/cip-engine-orchestrator", retention: logs.RetentionDays.TWO_WEEKS, removalPolicy: RemovalPolicy.DESTROY }),
      environment: {
        RUN_STATE_TABLE: runStateTable.tableName,
        AGENT_CACHE_TABLE: cacheTable.tableName,
        REPORTS_DIR: "/tmp/reports",
      },
    });

    ingestionQueue.grantConsumeMessages(orchestratorFn);
    orchestratorFn.addEventSource(new lambdaEventSources.SqsEventSource(ingestionQueue, { batchSize: 1 }));

    // 5. API Gateway
    const api = new apigw.RestApi(this, "PlatformApi", {
      restApiName: "cip-public-api",
      defaultCorsPreflightOptions: {
        allowOrigins: apigw.Cors.ALL_ORIGINS,
        allowMethods: apigw.Cors.ALL_METHODS,
        allowHeaders: apigw.Cors.DEFAULT_HEADERS,
      },
    });
    api.root.addResource("ingest").addMethod("POST", new apigw.LambdaIntegration(ingestionFn));
    api.root.addResource("status").addResource("{runId}").addMethod("GET", new apigw.LambdaIntegration(statusFn));
    api.root.addResource("reports").addResource("{runId}").addMethod("GET", new apigw.LambdaIntegration(reportsFn));

    // 6. Outputs
    new CfnOutput(this, "ApiEndpoint", { value: api.url });
    new CfnOutput(this, "QueueUrl", { value: ingestionQueue.queueUrl });
  }
} 