#!/usr/bin/env python3

import aws_cdk as cdk

from ResiliencyFoundation.resiliency_foundation import ResiliencyFoundationStack

app = cdk.App()
ResiliencyFoundationStack(app,"resiliency-foundation")
app.synth()
