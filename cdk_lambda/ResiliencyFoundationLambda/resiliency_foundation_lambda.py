from cgi import test
import email
from email import policy
from fileinput import filename
from multiprocessing import Condition
import os
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
    def createIAMRole(self,name,service_principal):
        role = iam.Role(
                self, name, 
                assumed_by=iam.ServicePrincipal(service_principal),
                #max_session_duration=core.Duration.seconds(43200),
                path=None,
                role_name=name
            )
        return role

    

    def __init__(self, scope, id):
        super().__init__(scope, id)
        
        codepipeline_role = ResiliencyFoundationLambdaStack.createIAMRole(self,
            "resiliencyvr-package-build-pipeline-role",
            "codepipeline.amazonaws.com",
        )