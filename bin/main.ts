#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import * as fs from 'fs';
import * as path from 'path';
import { ConfigIO, HarnessSpecSchema, type AwsDeploymentTarget } from '@aws/agentcore-cdk';
import { AgentCoreStack, type HarnessConfig } from '../lib/cdk-stack';
import { PlatformInfraStack } from '../lib/platform-infra-stack';


function toEnvironment(target: AwsDeploymentTarget): cdk.Environment {
  return {
    account: target.account,
    region: target.region,
  };
}

function sanitize(name: string): string {
  return name.replace(/_/g, '-');
}

function toStackName(projectName: string, targetName: string): string {
  return `AgentCore-${sanitize(projectName)}-${sanitize(targetName)}`;
}

function toMcpSpec(spec: any): any | undefined {
  if (!spec?.agentCoreGateways?.length && !spec?.mcpRuntimeTools?.length && !spec?.unassignedTargets?.length) {
    return undefined;
  }

  return {
    agentCoreGateways: spec.agentCoreGateways ?? [],
    mcpRuntimeTools: spec.mcpRuntimeTools ?? [],
    unassignedTargets: spec.unassignedTargets ?? [],
  };
}


async function main() {
  const app = new cdk.App();
  const platformEnv = {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION ?? 'ap-south-1',
  };

  new PlatformInfraStack(app, 'CompanyIntelligencePlatformV5', { env: platformEnv });

  if (process.env.SKIP_AGENTCORE === '1') {
    app.synth();
    return;
  }

  const configRoot = path.resolve(__dirname, '..', 'agentcore');
  const projectRoot = path.resolve(__dirname, '..');
  const configIO = new ConfigIO({ baseDir: configRoot });
  const spec = await configIO.readProjectSpec();
  const targets = await configIO.readAWSDeploymentTargets();
  const mcpSpec = toMcpSpec(spec);
  const previewEnabled = process.env.AGENTCORE_PREVIEW === '1';

  const harnessConfigs: HarnessConfig[] = [];
  if (previewEnabled && (spec as any).harnesses) {
    for (const entry of (spec as any).harnesses) {
      const harnessPath = path.resolve(projectRoot, entry.path, 'harness.json');
      if (fs.existsSync(harnessPath)) {
        const harnessSpec = HarnessSpecSchema.parse(JSON.parse(fs.readFileSync(harnessPath, 'utf-8')));
        harnessConfigs.push({
          name: entry.name,
          executionRoleArn: harnessSpec.executionRoleArn,
          memoryName: harnessSpec.memory?.mode === 'existing' ? harnessSpec.memory.name : undefined,
          containerUri: harnessSpec.containerUri,
          hasDockerfile: !!harnessSpec.dockerfile,
          dockerfile: harnessSpec.dockerfile,
          codeLocation: harnessSpec.dockerfile ? path.resolve(projectRoot, entry.path) : undefined,
          tools: harnessSpec.tools,
          skills: harnessSpec.skills,
          apiKeyArn: harnessSpec.model?.apiKeyArn,
          efsAccessPoints: harnessSpec.efsAccessPoints,
          s3AccessPoints: harnessSpec.s3AccessPoints,
          apiFormat: harnessSpec.model?.apiFormat,
          spec: harnessSpec,
          harnessDir: path.resolve(projectRoot, entry.path),
        });
      }
    }
  }

  for (const target of targets) {
    new AgentCoreStack(app, toStackName(spec.name, target.name), {
      env: toEnvironment(target),
      spec,
      mcpSpec,
      harnesses: harnessConfigs.length > 0 ? harnessConfigs : undefined,
      description: `AgentCore stack for ${spec.name}`,
      tags: {
        'agentcore:project-name': spec.name,
        'agentcore:target-name': target.name,
      },
    });
  }

  app.synth();
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});