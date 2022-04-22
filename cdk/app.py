#!/usr/bin/env python3

from aws_cdk import core

from ResiliencyFoundation.resiliency_foundation import ResiliencyFoundationStack

app = core.App()
ResiliencyFoundationStack(app,"resiliency-foundation")
app.synth()
