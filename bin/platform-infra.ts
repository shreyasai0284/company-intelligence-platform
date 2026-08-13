#!/usr/bin/env node
import "source-map-support/register";
import * as cdk from "aws-cdk-lib";
import { PlatformInfraStack } from "../lib/platform-infra-stack";

const app = new cdk.App();

new PlatformInfraStack(app, "CompanyIntelligencePlatformV5", {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? "ap-south-1",
  },
  description:
    "Company Intelligence Platform V5.0 — LangGraph macro-orchestrator + Bedrock AgentCore execution layer.",
});

app.synth();