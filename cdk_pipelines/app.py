#!/usr/bin/env python3

import aws_cdk as cdk

from ResiliencyFoundationPipelines.resiliency_foundation_pipelines import ResiliencyFoundationPipelinesStack

app = cdk.App()
ResiliencyFoundationPipelinesStack(app,"resiliency-foundation-pipelines")
app.synth()
