from cgi import test
import email
from email import policy
from fileinput import filename
from multiprocessing import Condition
import os
from pickle import TRUE
from pyclbr import Function
import re
from sqlite3 import Timestamp
from ssl import _create_default_https_context
import time
from zipfile import ZipFile
import json
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    #aws_s3_assets as s3_assets,
    aws_s3_deployment as s3deploy,
    aws_lambda as lambda_,
    aws_sqs as sqs,
    aws_events as events,
    aws_servicecatalog as servicecatalog,
    aws_cloudformation as cloudformation,
    aws_events_targets as targets,
    aws_sns as sns,
    aws_sns_subscriptions as subscriptions,
    aws_stepfunctions as sfn,
    aws_kms as kms,
    aws_codeartifact as codeartifact,
    aws_elasticsearch as elasticsearch,
    aws_codebuild as codebuild,
    core
)

class ResiliencyFoundationLambdaStack(core.Stack):
    def createKMSKey(self,name,description):
        key = kms.Key(self, 
            name,
            description=description,
            pending_window=core.Duration.days(14),
            enable_key_rotation=True,
        )
        return key

    def createIAMRole(self,name,service_principal):
        role = iam.Role(
                self, name, 
                assumed_by=iam.ServicePrincipal(service_principal),
                #max_session_duration=core.Duration.seconds(43200),
                path=None,
                role_name=name
            )
        return role

    def createResiliencyLambdaIAMPolicy(self):
        resiliency_lambda_policy = iam.ManagedPolicy(
            self, "resiliency_lambda_policy",
            managed_policy_name="resiliency_lambda_policy",
            statements=[
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "ssm:SendCommand"
                    ],
                    resources=[
                        "*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "s3:GetObject",
                        "s3:Listbucket",
                        "s3:PutObject"
                    ],
                    resources=[
                        "arn:aws:s3:::resiliency-testing-experiments",
                        "arn:aws:s3:::resiliency-testing-experiments/*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "ec2:DescribeInstances"
                    ],
                    resources=[
                        "*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "ec2:RunInstances",
                        "ec2:TerminateInstances",
                        "ec2:StopInstances",
                        "ec2:StartInstances"
                    ],
                    resources=[
                        "*"
                    ],
                    # conditions=[{
                    #     "StringEquals":{
                    #         "ec2:ResourceTag/Type": "Resiliency",
                    #     },
                    # }
                    # ],
                ),
            ],
        )

        return resiliency_lambda_policy

    def __init__(self, scope, id):
        super().__init__(scope, id)
        
        s3_key = ResiliencyFoundationLambdaStack.createKMSKey(self,"s3_key","Customer managed KMS key to encrypt S3 resources")
        resiliency_lambda_role = ResiliencyFoundationLambdaStack.createIAMRole(self,"resiliency_lambda_role","lambda.amazonaws.com")
        resiliency_lambda_policy = ResiliencyFoundationLambdaStack.createResiliencyLambdaIAMPolicy(self)
        