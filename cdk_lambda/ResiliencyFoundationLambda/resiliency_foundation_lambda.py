from cgi import test
import random
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
from unicodedata import category
import zipfile
from zipfile import ZipFile
import json
import aws_cdk as core
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
    aws_codepipeline as codepipeline,
    pipelines as pipelines,
    aws_codepipeline_actions as codepipeline_actions,
    aws_codecommit as codecommit,
    Stack
)


class ResiliencyFoundationLambdaStack(core.Stack):
  
    def createIAMRole(self,name,service_principal_list):
        composite_principal = iam.CompositePrincipal(iam.ServicePrincipal(service_principal_list[0]))
        if len(service_principal_list) > 1:
            for service_principal in service_principal_list[1:]:
                composite_principal.add_principals(iam.ServicePrincipal(service_principal))
        role = iam.Role(
                self, name, 
                assumed_by=composite_principal,
                #assumed_by=iam.ServicePrincipal(service_principal),
                #max_session_duration=core.Duration.seconds(43200),
                path=None,
                role_name=name
            )
        return role

    def createKMSKey(self,name,description):
        key = kms.Key(self, 
            name,
            description=description,
            pending_window=core.Duration.days(14),
            enable_key_rotation=True,
        )
        return key

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
   
    def uploadLambdaCode(self,random_bucket_suffix):
        def zipdir(path, ziph):
            # ziph is zipfile handle
            for root, dirs, files in os.walk(path):
                for file in files:
                    ziph.write(os.path.join(root, file), 
                            os.path.relpath(os.path.join(root, file), 
                                            os.path.join(path, '..')))
        
        with zipfile.ZipFile('resiliency_code.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipdir('../resiliency_code', zipf)

        ZipFile("resiliency_code_zipped.zip", mode='w').write("resiliency_code.zip")

        lambda_code_bucket = s3.Bucket(self, "resiliency_lambda_code_bucket"+random_bucket_suffix, bucket_name="resiliency-lambda-code-bucket"+random_bucket_suffix,access_control=s3.BucketAccessControl.PRIVATE,removal_policy=core.RemovalPolicy.DESTROY,auto_delete_objects=True)
        code_upload = s3deploy.BucketDeployment(self, "LambdaCodeSource",
            sources=[s3deploy.Source.asset("resiliency_code_zipped.zip")],
            destination_bucket=lambda_code_bucket,
        )

        return{
            "lambda_code_bucket" : lambda_code_bucket,
            "code_upload" : code_upload
        }

    def createFunction(self,resiliency_lambda_role,lambda_code_bucket,code_upload):
        lambda_function=lambda_.Function(self,
            "lambda_function",
            function_name="ResiliencyLambdaFunction",
            role=resiliency_lambda_role,
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="resiliency_foundation.lambda_handler",
            code=lambda_.Code.from_bucket(
                bucket=lambda_code_bucket,
                key="resiliency_code.zip"
            ),
            # environment={
            #     "ROLE_NAME": role_name,
            #     "TOPICARN": topic_arn
            # },
        )

        
        lambda_function.node.add_dependency(code_upload)
        # lambda_function.add_depends_on(code_upload)

        return lambda_function
    
    def __init__(self, scope, id):
        super().__init__(scope, id)
        random_bucket_suffix = os.getlogin()

        s3_key = ResiliencyFoundationLambdaStack.createKMSKey(self,"s3_key","Customer managed KMS key to encrypt S3 resources")
        resiliency_lambda_role = ResiliencyFoundationLambdaStack.createIAMRole(self,"resiliency_lambda_role",["lambda.amazonaws.com"])
        resiliency_lambda_policy = ResiliencyFoundationLambdaStack.createResiliencyLambdaIAMPolicy(self)
        resiliency_lambda_policy.attach_to_role(resiliency_lambda_role)
        
        code_upload_resources = ResiliencyFoundationLambdaStack.uploadLambdaCode(self,random_bucket_suffix)
        code_upload = code_upload_resources["code_upload"]
        lambda_code_bucket = code_upload_resources["lambda_code_bucket"]
        lambda_function = ResiliencyFoundationLambdaStack.createFunction(self,resiliency_lambda_role,lambda_code_bucket,code_upload)