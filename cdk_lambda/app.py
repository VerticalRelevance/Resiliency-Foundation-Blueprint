#!/usr/bin/env python3

import aws_cdk as cdk

from ResiliencyFoundationLambda.resiliency_foundation_lambda import ResiliencyFoundationLambdaStack

app = cdk.App()
ResiliencyFoundationLambdaStack(app,"resiliency-foundation-lambda")
app.synth()
