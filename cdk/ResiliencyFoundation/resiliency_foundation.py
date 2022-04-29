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
    aws_codepipeline_actions as codepipeline_actions,
    Stack
)

class ResiliencyFoundationStack(Stack):
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

        cfn_domain_res_ca_devckd = codeartifact.CfnDomain(self, "MyCfnDomain",
            domain_name="res-ca-devckd",
            permissions_policy_document=cfn_domain_permissions_policy,
            # encryption_at_rest_options=elasticsearch.CfnDomain.EncryptionAtRestOptionsProperty(
            #     enabled=False,
            #     kms_key_id=encryption_key.key_id
            # ),
        )

        cfn_repository_pypistore = codeartifact.CfnRepository(self, "cfn_repository_pypistore",
            domain_name=cfn_domain_res_ca_devckd.domain_name,
            repository_name="pypi-store",
            external_connections=["public:pypi"],
        )

        cfn_repository_pypistore.add_depends_on(cfn_domain_res_ca_devckd)

        cfn_repository_res_ca_dev = codeartifact.CfnRepository(self, "cfn_repository_res_ca_dev",
            domain_name=cfn_domain_res_ca_devckd.domain_name,
            repository_name="res-ca-dev",
            upstreams=[cfn_repository_pypistore.repository_name],
        )

        cfn_repository_res_ca_dev.add_depends_on(cfn_domain_res_ca_devckd)
        cfn_repository_res_ca_dev.add_depends_on(cfn_repository_pypistore)

        return {
            "cfn_domain_res_ca_devckd" : cfn_domain_res_ca_devckd,
            "cfn_repository_res_ca_dev" : cfn_repository_res_ca_dev
        }

    def createCodePipelineBucket(self):
        code_pipeline_bucket = s3.Bucket(self, "code_pipeline_bucket", bucket_name="resiliency-package-build-bucket3",access_control=s3.BucketAccessControl.PRIVATE,removal_policy=core.RemovalPolicy.DESTROY)
        return code_pipeline_bucket
    
    def createBackendBucket(self):
        backend_bucket = s3.Bucket(self, "backend_bucket", bucket_name="resiliency-terraform-backend-bucket3",access_control=s3.BucketAccessControl.PRIVATE,versioned=True,removal_policy=core.RemovalPolicy.DESTROY)
        return backend_bucket

    def createCodePipelineIAMPolicy(self,codepipeline_bucket,codestar_connections_github_arn):
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
                        codepipeline_bucket.bucket_arn,
                        codepipeline_bucket.bucket_arn+"/*",
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

        return codepipeline_policy

    def createCodeBuildPackageIAMPolicy(self,codeartifact_repository_res_ca_dev_arn,codeartifact_domain_res_ca_dev_domain_arn,codepipeline_bucket):
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
                        codepipeline_bucket.bucket_arn,
                        codepipeline_bucket.bucket_arn + "/*",
                    ],
                ),
            ],
        )

        return resiliencyvr_codebuild_package_policy

    def createCodeBuildLambdaIAMPolicy(self,codeartifact_repository_res_ca_dev_arn,codeartifact_domain_res_ca_dev_domain_arn,codepipeline_bucket,backend_bucket_arn):
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
                        codepipeline_bucket.bucket_arn,
                        codepipeline_bucket.bucket_arn + "/*",
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

        return resiliencyvr_codebuild_lambda_policy

    def createIAMRole(self,name,service_principal):
        role = iam.Role(
                self, name, 
                assumed_by=iam.ServicePrincipal(service_principal),
                #max_session_duration=core.Duration.seconds(43200),
                path=None,
                role_name=name
            )
        return role

    def createCodeBuildPipelineProjects(self,codebuild_package_role,codebuild_lambda_role,codepipeline_bucket):
        zf = ZipFile("buildspec-resiliencyvr.zip", "w")
        zf.write("buildspec-resiliencyvr.yml")
        zf.close()
        resiliencyvr_project = codebuild.PipelineProject(self, "resiliencyvr_project",
            project_name = "resiliencyvr-package-codebuild",
            description = "Builds the resiliencyvr package",
            role = codebuild_package_role,
            timeout = core.Duration.minutes(5),

            # artifacts=codebuild.Artifacts(type="CODEPIPELINE")

            environment= codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL
            ),

            logging=codebuild.LoggingOptions(
                s3=codebuild.S3LoggingOptions(
                    bucket=codepipeline_bucket,
                    prefix="build-log"
                )
            ),

            build_spec=codebuild.BuildSpec.from_source_filename("buildspec-resiliencyvr.zip")
        )
        zf = ZipFile("buildspec-lambda.zip", "w")
        zf.write("buildspec-lambda.yml")
        zf.close()
        lambda_project = codebuild.PipelineProject(self, "lambda_project",
            project_name = "resiliency-lambda-codebuild",
            description = "Builds the resiliency lambda to run VR Resiliency tests",
            role = codebuild_lambda_role,
            timeout = core.Duration.minutes(5),

            # artifacts=codebuild.Artifacts(type="CODEPIPELINE")

            environment= codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL,
                environment_variables={
                    "TF_COMMAND": codebuild.BuildEnvironmentVariable(
                        value=""
                    ),
                    "TF_VAR_resiliency_bucket": codebuild.BuildEnvironmentVariable(
                        value=codepipeline_bucket.bucket_name
                    )
                }
            ),

            logging=codebuild.LoggingOptions(
                s3=codebuild.S3LoggingOptions(
                    bucket=codepipeline_bucket,
                    prefix="build-log"
                )
            ),

            build_spec=codebuild.BuildSpec.from_source_filename("buildspec-lambda.zip")
        )

    def createPipeline(self,repo):

        build_project = codebuild.PipelineProject(self, "InvalidateProject",
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "build": {
                        "commands": ["ls"]
                    }
                }
            }),
        )
        pipeline = codepipeline.Pipeline(self, "Pipeline")

        source_stage = pipeline.add_stage(stage_name="Source")

        source_output = codepipeline.Artifact()

        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="Github_Source",
            output=source_output,
            owner="ethanbegalka",
            repo="AccessKeyCleanup",
            oauth_token=core.SecretValue.secrets_manager("resiliency-pipeline-github-oauth-token"),
            # variables_namespace="MyNamespace"
        )

        source_stage.add_action(source_action)

        dest_stage = pipeline.add_stage(stage_name="Dest")

        dest_output = codepipeline.Artifact(artifact_name="dest_output")
        dest_input = codepipeline.Artifact(artifact_name="dest_input")

        dest_action = codepipeline_actions.CodeBuildAction(
                action_name="InvalidateCache",
                project=build_project,
                input=source_output,
                run_order=2
        )

        dest_stage.add_action(dest_action)


    def __init__(self, scope, id):
        super().__init__(scope, id)

        #codepipeline_bucket.bucket_arn = "arn:aws:s3:::bucket_name"

        codepipeline_role = ResiliencyFoundationStack.createIAMRole(self,
            "resiliencyvr-package-build-pipeline-role",
            "codepipeline.amazonaws.com",
        )
        codebuild_package_role = ResiliencyFoundationStack.createIAMRole(self,
            "resiliencyvr_codebuild_package_role",
            "codebuild.amazonaws.com",
        )
        codebuild_lambda_role = ResiliencyFoundationStack.createIAMRole(self,
            "resiliencyvr_codebuild_lambda_role",
            "codebuild.amazonaws.com",
        )

        codeartifact_resources = ResiliencyFoundationStack.createCodeArtifactory(self,codebuild_package_role,codebuild_lambda_role)
        cfn_domain_res_ca_devckd = codeartifact_resources["cfn_domain_res_ca_devckd"]
        cfn_repository_res_ca_dev = codeartifact_resources["cfn_repository_res_ca_dev"]

        codepipeline_bucket = ResiliencyFoundationStack.createCodePipelineBucket(self)
        codestar_connections_github_arn = "arn:aws:codestar-connections:region:account-id:connection/connection-id"
        codeartifact_domain_res_ca_dev_domain_arn = cfn_domain_res_ca_devckd.attr_arn
        codeartifact_repository_res_ca_dev_arn = cfn_repository_res_ca_dev.attr_arn

        backend_bucket_arn = ResiliencyFoundationStack.createBackendBucket(self).bucket_arn

        codepipeline_policy = ResiliencyFoundationStack.createCodePipelineIAMPolicy(self,
            codepipeline_bucket,
            codestar_connections_github_arn
        )
        codepipeline_policy.attach_to_role(codepipeline_role)

        codebuild_package_policy = ResiliencyFoundationStack.createCodeBuildPackageIAMPolicy(self,
            codeartifact_repository_res_ca_dev_arn,
            codeartifact_domain_res_ca_dev_domain_arn,
            codepipeline_bucket,
        )
        codebuild_package_policy.attach_to_role(codebuild_package_role)

        codebuild_lambda_policy = ResiliencyFoundationStack.createCodeBuildLambdaIAMPolicy(self,
            codeartifact_repository_res_ca_dev_arn,
            codeartifact_domain_res_ca_dev_domain_arn,
            codepipeline_bucket,
            backend_bucket_arn,
        )
        codebuild_lambda_policy.attach_to_role(codebuild_lambda_role)
        
        codebuild_resources = ResiliencyFoundationStack.createCodeBuildPipelineProjects(self,
            codebuild_package_role,
            codebuild_lambda_role,
            codepipeline_bucket
        )

        ResiliencyFoundationStack.createPipeline(self,cfn_repository_res_ca_dev)
        