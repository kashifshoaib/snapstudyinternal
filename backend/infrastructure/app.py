#!/usr/bin/env python3
"""CDK app for SnapStudy backend infrastructure."""

import aws_cdk as cdk
from constructs import Construct
from stacks.snapstudy_stack import SnapStudyStack

app = cdk.App()

SnapStudyStack(
    app, 
    "SnapStudyStack",
    env=cdk.Environment(
        account=app.node.try_get_context("account"),
        region=app.node.try_get_context("region") or "us-east-1"
    )
)

app.synth()