from cgi import test
import email
from email import policy
from fileinput import filename
from multiprocessing import Condition
import os
from pyclbr import Function
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
    core
)

class ResiliencyFoundationStack(core.Stack):
    def createCodeArtifactory(self,codebuild_package_role,codebuild_lambda_role):
        cfn_domain_permissions_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codeartifact:PublishPackageVersion"
                    ],
                    principals=[iam.ArnPrincipal(codebuild_package_role.role_arn)],
                    resources=[
                        "*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codeartifact:DescribePackageVersion",
                        "codeartifact:DescribeRepository",
                        "codeartifact:GetPackageVersionReadme",
                        "codeartifact:GetRepositoryEndpoint",
                        "codeartifact:ListPackages",
                        "codeartifact:ListPackageVersions",
                        "codeartifact:ListPackageVersionAssets",
                        "codeartifact:ListPackageVersionDependencies",
                        "codeartifact:ReadFromRepository"
                    ],
                    principals=[iam.ArnPrincipal(codebuild_lambda_role.role_arn)],
                    resources=[
                        "*"
                    ],
                ),
            ]
        )

        encryption_key = kms.Key(self, "res-ca-dev-repo-key", description="res-ca-dev repository key")

        cfn_domain = codeartifact.CfnDomain(self, "MyCfnDomain",
            domain_name="res-ca-devckd",
            permissions_policy_document=cfn_domain_permissions_policy,
            # encryption_at_rest_options=elasticsearch.CfnDomain.EncryptionAtRestOptionsProperty(
            #     enabled=False,
            #     kms_key_id=encryption_key.key_id
            # ),
        )

        cfn_repository_pypistore = codeartifact.CfnRepository(self, "cfn_repository_pypistore",
            domain_name=cfn_domain.domain_name,
            repository_name="pypi-store",
            external_connections=["public:pypi"],
        )

        cfn_repository_pypistore.add_depends_on(cfn_domain)

        cfn_repository_res_ca_dev = codeartifact.CfnRepository(self, "cfn_repository_res_ca_dev",
            domain_name=cfn_domain.domain_name,
            repository_name="res-ca-dev",
            upstreams=[cfn_repository_pypistore.repository_name],
        )

        cfn_repository_res_ca_dev.add_depends_on(cfn_domain)

        

    def createCodePipelineBucket(self):
        code_pipeline_bucket = s3.Bucket(self, "code_pipeline_bucket", bucket_name="resiliency-package-build-bucket3",access_control=s3.BucketAccessControl.PRIVATE)
        return code_pipeline_bucket
    
    def createBackendBucket(self):
        backend_bucket = s3.Bucket(self, "backend_bucket", bucket_name="resiliency-terraform-backend-bucket3",access_control=s3.BucketAccessControl.PRIVATE,versioned=True)
        return backend_bucket

    def createCodePipelineIAMResources(self,codepipeline_bucket_arn,codestar_connections_github_arn):
        codepipeline_policy = iam.ManagedPolicy(
            self, "codepipeline_policy",
            managed_policy_name="codepipeline_policy",
            statements=[
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "s3:GetObject",
                        "s3:GetObjectVersion",
                        "s3:GetBucketVersioning",
                        "s3:PutObjectAcl",
                        "s3:PutObject"
                    ],
                    resources=[
                        codepipeline_bucket_arn,
                        codepipeline_bucket_arn+"/*",
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codestar-connections:UseConnection"
                    ],
                    resources=[
                        codestar_connections_github_arn
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codebuild:BatchGetBuilds",
                        "codebuild:StartBuild"
                    ],
                    resources=[
                        "*"
                    ],
                ),
            ]
        )
        codepipeline_role = iam.Role(
            self, "codepipeline_role", 
            assumed_by=iam.ServicePrincipal("codepipeline.amazonaws.com"),
            managed_policies=[codepipeline_policy],
            #max_session_duration=core.Duration.seconds(43200),
            path=None,
            role_name="resiliencyvr-package-build-pipeline-role"
        )
        return {
            "policy" : codepipeline_policy,
            "role" : codepipeline_role
        }

    def createCodeBuildPackageIAMResources(self,codeartifact_repository_res_ca_dev_arn,codeartifact_domain_res_ca_dev_domain_arn,codepipeline_bucket_arn):
        resiliencyvr_codebuild_package_policy = iam.ManagedPolicy(
            self, "resiliencyvr_codebuild_package_policy",
            managed_policy_name="resiliencyvr_codebuild_package_policy",
            statements=[
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        "*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codeartifact:GetAuthorizationToken",
                        "codeartifact:GetRepositoryEndpoint"
                    ],
                    resources=[
                        codeartifact_repository_res_ca_dev_arn,
                        codeartifact_domain_res_ca_dev_domain_arn+"/*",
                        codeartifact_domain_res_ca_dev_domain_arn,
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "sts:GetServiceBearerToken"
                    ],
                    resources=[
                        "*"
                    ],
                    # conditions=[{
                    #     "StringEquals":{
                    #         "sts:AWSServiceName": ["codeartifact.amazonaws.com"],
                    #     },
                    # }
                    # ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "s3:*"
                    ],
                    resources=[
                        codepipeline_bucket_arn,
                        codepipeline_bucket_arn + "/*",
                    ],
                ),
            ],
        )

        resiliencyvr_codebuild_package_role = iam.Role(
            self, "resiliencyvr_codebuild_package_role", 
            assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
            managed_policies=[resiliencyvr_codebuild_package_policy],
            #max_session_duration=core.Duration.seconds(43200),
            path=None,
            role_name="resiliencyvr-codebuild-package-role"
        )

        return {
            "policy" : resiliencyvr_codebuild_package_policy,
            "role" : resiliencyvr_codebuild_package_role
        }


    def createCodeBuildLambdaIAMResources(self,codeartifact_repository_res_ca_dev_arn,codeartifact_domain_res_ca_dev_domain_arn,codepipeline_bucket_arn,backend_bucket_arn):
        resiliencyvr_codebuild_lambda_policy = iam.ManagedPolicy(
            self, "resiliencyvr_codebuild_lambda_policy",
            managed_policy_name="resiliencyvr_codebuild_lambda_policy",
            statements=[
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents"
                    ],
                    resources=[
                        "*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codeartifact:GetAuthorizationToken",
                        "codeartifact:GetRepositoryEndpoint"
                    ],
                    resources=[
                        codeartifact_repository_res_ca_dev_arn,
                        codeartifact_domain_res_ca_dev_domain_arn+"/*",
                        codeartifact_domain_res_ca_dev_domain_arn
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "sts:GetServiceBearerToken"
                    ],
                    resources=[
                        "*"  
                    ],
                    # conditions=[{
                    #     "StringEquals":{
                    #         "sts:AWSServiceName": "codeartifact.amazonaws.com",
                    #     }
                    # }
                    # ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "s3:*"
                    ],
                    resources=[
                        codepipeline_bucket_arn,
                        codepipeline_bucket_arn + "/*",
                        backend_bucket_arn,
                        backend_bucket_arn + "/*",
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "kms:*"
                    ],
                    resources=[
                        "*"
                    ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "iam:PassRole"
                    ],
                    resources=[
                        "*"
                    ],
                    # conditions=[{
                    #     "StringEquals":{
                    #         "iam:PassedToService": "lambda.amazonaws.com",
                    #     }
                    # }
                    # ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "iam:*"
                    ],
                    resources=[
                        "*"
                    ],
                    # conditions=[{
                    #     "StringEquals":{
                    #         "aws:ResourceTag/Team": "ResiliencyTeam",
                    #     }
                    # }
                    # ],
                ),
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "lambda:CreateFunction",
                        "lambda:GetFunction",
                        "lambda:List*",
                        "lambda:GetFunctionCodeSigningConfig",
                        "lambda:GetCodeSigningConfig",
                        "lambda:DeleteFunction"
                    ],
                    resources=[
                        "*"
                    ],
                ),
            ]
        )

        resiliencyvr_codebuild_lambda_role = iam.Role(
                self, "resiliencyvr_codebuild_lambda_role", 
                assumed_by=iam.ServicePrincipal("codebuild.amazonaws.com"),
                managed_policies=[resiliencyvr_codebuild_lambda_policy],
                #max_session_duration=core.Duration.seconds(43200),
                path=None,
                role_name="resiliencyvr-codebuild-lambda-role"
            )
        
        return {
            "policy" : resiliencyvr_codebuild_lambda_policy,
            "role" : resiliencyvr_codebuild_lambda_role
        }


    def __init__(self, scope, id):
        super().__init__(scope, id)

        #codepipeline_bucket_arn = "arn:aws:s3:::bucket_name"

        codepipeline_bucket_arn = ResiliencyFoundationStack.createCodePipelineBucket(self).bucket_arn
        codestar_connections_github_arn = "arn:aws:codestar-connections:region:account-id:connection/connection-id"
        codeartifact_repository_res_ca_dev_arn = "arn:aws:codeartifact:region-id:111122223333:repository/my_domain/my_repo"
        codeartifact_domain_res_ca_dev_domain_arn = "arn:aws:codeartifact:us-west-2:111122223333:domain/my_domain"
        backend_bucket_arn = ResiliencyFoundationStack.createBackendBucket(self).bucket_arn

        codepipeline_iam_resources = ResiliencyFoundationStack.createCodePipelineIAMResources(self,
            codepipeline_bucket_arn,
            codestar_connections_github_arn
        )
        codepipeline_policy = codepipeline_iam_resources["policy"]
        codepipeline_role = codepipeline_iam_resources["role"]

        codebuild_package_iam_resources = ResiliencyFoundationStack.createCodeBuildPackageIAMResources(self,
            codeartifact_repository_res_ca_dev_arn,
            codeartifact_domain_res_ca_dev_domain_arn,
            codepipeline_bucket_arn
        )
        codebuild_package_policy = codebuild_package_iam_resources["policy"]
        codebuild_package_role = codebuild_package_iam_resources["role"]

        codebuild_lambda_iam_resources = ResiliencyFoundationStack.createCodeBuildLambdaIAMResources(self,
            codeartifact_repository_res_ca_dev_arn,
            codeartifact_domain_res_ca_dev_domain_arn,
            codepipeline_bucket_arn,
            backend_bucket_arn,
        )
        codebuild_lambda_policy = codebuild_lambda_iam_resources["policy"]
        codebuild_lambda_role = codebuild_lambda_iam_resources["role"]
        ResiliencyFoundationStack.createCodeArtifactory(self,codebuild_package_role,codebuild_lambda_role)
