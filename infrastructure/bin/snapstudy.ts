#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { SnapStudyStack } from '../lib/snapstudy-stack-simple';

const app = new cdk.App();

new SnapStudyStack(app, 'SnapStudyStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});