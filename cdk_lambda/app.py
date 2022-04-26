#!/usr/bin/env python3

from aws_cdk import core

from ResiliencyFoundationLambda.resiliency_foundation_lambda import ResiliencyFoundationLambdaStack

app = core.App()
ResiliencyFoundationLambdaStack(app,"resiliency-foundation-lambda")
app.synth()
