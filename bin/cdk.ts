#!/usr/bin/env node
import 'source-map-support/register';
import { App } from 'aws-cdk-lib';
import * as path from 'path';
import * as fs from 'fs';
import { AgentCoreStack, type HarnessConfig } from '../lib/cdk-stack';
import { ConfigIO, HarnessSpecSchema, type AwsDeploymentTarget } from '@aws/agentcore-cdk';


const toMcpSpec = (spec: any): any | undefined => {
  if (!spec?.agentCoreGateways?.length && !spec?.mcpRuntimeTools?.length && !spec?.unassignedTargets?.length) {
    return undefined;
  }

  return {
    agentCoreGateways: spec.agentCoreGateways ?? [],
    mcpRuntimeTools: spec.mcpRuntimeTools ?? [],
    unassignedTargets: spec.unassignedTargets ?? [],
  };
};

// Helper to convert target to CDK Environment
const toEnvironment = (target: AwsDeploymentTarget) => ({
  account: target.account,
  region: target.region,
});

const sanitize = (name: string) => name.replace(/_/g, '-');
const toStackName = (projectName: string, targetName: string) => 
  `AgentCore-${sanitize(projectName)}-${sanitize(targetName)}`;

async function main() {
  const configRoot = path.resolve(__dirname, '..', 'agentcore');
  const projectRoot = path.resolve(__dirname, '..');
  const configIO = new ConfigIO({ baseDir: configRoot });

  const spec = await configIO.readProjectSpec();
  const mcpSpec = toMcpSpec(spec);
  const targets = await configIO.readAWSDeploymentTargets();

  if (!targets || targets.length === 0) {
    throw new Error('No deployment targets found.');
  }

  // Preview flag check
  const previewEnabled = process.env.AGENTCORE_PREVIEW === '1';

  // Harness configuration loading
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

  const app = new App();

  for (const target of targets) {
    new AgentCoreStack(app, toStackName(spec.name, target.name), {
      spec,
      mcpSpec,
      harnesses: harnessConfigs.length > 0 ? harnessConfigs : undefined,
      env: toEnvironment(target),
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