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

class ResiliencyFoundationPipelinesStack(Stack):
    def createCodeArtifactory(self,domain_name,repo_name):
        cfn_domain_permissions_policy = iam.PolicyDocument(
            statements=[
                iam.PolicyStatement(effect= 
                    iam.Effect.ALLOW,
                    actions= [
                        "codeartifact:PublishPackageVersion"
                    ],
                    principals=[iam.AnyPrincipal()],
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
                        "codeartifact:ReadFromRepository",
                        "codeartifact:GetAuthorizationToken"
                    ],
                    principals=[iam.AnyPrincipal()],
                    resources=[
                        "*"
                    ],
                ),
            ]
        )

        encryption_key = kms.Key(self, "res-ca-dev-repo-key", description="res-ca-dev repository key")

        cfn_domain_res_ca_devckd = codeartifact.CfnDomain(self, "MyCfnDomain",
            domain_name=domain_name,
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
            repository_name=repo_name,
            upstreams=[cfn_repository_pypistore.repository_name],
        )

        cfn_repository_res_ca_dev.add_depends_on(cfn_domain_res_ca_devckd)
        cfn_repository_res_ca_dev.add_depends_on(cfn_repository_pypistore)

        return {
            "cfn_domain_res_ca_devckd" : cfn_domain_res_ca_devckd,
            "cfn_repository_res_ca_dev" : cfn_repository_res_ca_dev
        }

    def createCodePipelineBucket(self,random_bucket_suffix):
        code_pipeline_bucket = s3.Bucket(self, "code_pipeline_bucket", bucket_name="resiliencyvr-package-build-bucket"+random_bucket_suffix,access_control=s3.BucketAccessControl.PRIVATE,removal_policy=core.RemovalPolicy.DESTROY,auto_delete_objects=True)
        return code_pipeline_bucket

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
                        "codebuild:StartBuild",
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

    def createCodeBuildLambdaIAMPolicy(self,codeartifact_repository_res_ca_dev_arn,codeartifact_domain_res_ca_dev_domain_arn,codepipeline_bucket):
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

    def createResiliencyVRCodeBuildPipelineProject(self,codebuild_package_role,codepipeline_bucket,domain_name,owner,repo_name):
        resiliencyvr_project = codebuild.PipelineProject(self, "resiliencyvr_codebuild_project",
            project_name = "resiliencyvr-package-codebuild",
            description = "Builds the resiliencyvr package",
            role = codebuild_package_role,
            timeout = core.Duration.minutes(5),

            # artifacts=codebuild.Artifacts(type="CODEPIPELINE")

            environment= codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL,
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables={
                    "DOMAIN_NAME": codebuild.BuildEnvironmentVariable(
                        value=domain_name
                    ),
                    "OWNER": codebuild.BuildEnvironmentVariable(
                        value=owner
                    ),
                    "REPO_NAME": codebuild.BuildEnvironmentVariable(
                        value=repo_name
                    )
                }
            ),

            logging=codebuild.LoggingOptions(
                s3=codebuild.S3LoggingOptions(
                    bucket=codepipeline_bucket,
                    prefix="build-log"
                )
            ),

            build_spec=codebuild.BuildSpec.from_source_filename("cdk/buildspec-resiliencyvr.yml")
        )
        return resiliencyvr_project
    def createLambdaCodeBuildPipelineProject(self,codebuild_lambda_role,domain_name,owner,repo_name):
        lambda_deploy_project = codebuild.PipelineProject(self, "cdk_deploy",
            role = codebuild_lambda_role,
            build_spec=codebuild.BuildSpec.from_object({
                "version": "0.2",
                "phases": {
                    "build": {
                        "commands": [
                            "aws codeartifact login --tool pip --domain $DOMAIN_NAME --domain-owner $OWNER --repository $REPO_NAME",
                            "npm install -g aws-cdk",  # Installs the cdk cli on Codebuild
                            "pip install -r cdk_lambda/requirements.txt",  # Instructs Codebuild to install required packages
                            "pip install aws-cdk-lib",
                            "cdk --version",
                            "cd cdk_lambda",
                            "npx cdk deploy",

                        ]
                    }
                }
            }),
            environment= codebuild.BuildEnvironment(
                compute_type=codebuild.ComputeType.SMALL,
                build_image=codebuild.LinuxBuildImage.STANDARD_5_0,
                environment_variables={
                    "DOMAIN_NAME": codebuild.BuildEnvironmentVariable(
                        value=domain_name
                    ),
                    "OWNER": codebuild.BuildEnvironmentVariable(
                        value=owner
                    ),
                    "REPO_NAME": codebuild.BuildEnvironmentVariable(
                        value=repo_name
                    )
                }
            ),
        )
        return lambda_deploy_project

    def createResiliencyVRPipeline(self,resiliencyvr_codebuild_pipeline_project):
        resiliencyvr_pipeline = codepipeline.Pipeline(self, "resiliencyvr_pipeline")

        source_output = codepipeline.Artifact(artifact_name="source_output")
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="Github_Source",
            output=source_output,
            owner="VerticalRelevance",
            repo="Resiliency-Foundation-Blueprint",
            branch="dev",
            #oauth_token=core.SecretValue.secrets_manager("resiliency-pipeline-github-oauth-token"),
            #oauth_token=core.SecretValue.unsafe_plain_text("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"),
            oauth_token=core.SecretValue.unsafe_plain_text("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"),
            run_order=1
        )
        source_stage = resiliencyvr_pipeline.add_stage(stage_name="Source")
        source_stage.add_action(source_action)

        build_action = codepipeline_actions.CodeBuildAction(
                action_name="Build",
                type = codepipeline_actions.CodeBuildActionType.BUILD,
                project=resiliencyvr_codebuild_pipeline_project,
                input=source_output,
                run_order=2
        )
        build_stage = resiliencyvr_pipeline.add_stage(stage_name="Build")
        build_stage.add_action(build_action)
    
    def createLambdaPipeline(self,lambda_deploy_project):
        lambda_pipeline = codepipeline.Pipeline(self, "lambda_pipeline")

        source_output = codepipeline.Artifact(artifact_name="source_output")
        source_action = codepipeline_actions.GitHubSourceAction(
            action_name="Github_Source",
            output=source_output,
            owner="VerticalRelevance",
            repo="Resiliency-Foundation-Blueprint",
            branch="dev",
            oauth_token=core.SecretValue.secrets_manager("resiliency-pipeline-github-oauth-token"),
            run_order=1
        )
        source_stage = lambda_pipeline.add_stage(stage_name="Source")
        source_stage.add_action(source_action)

        deploy_action = codepipeline_actions.CodeBuildAction(
            action_name="Deploy",
            type = codepipeline_actions.CodeBuildActionType.BUILD,
            project=lambda_deploy_project,
            input=source_output,
            # environment_variables={
            #     "DOMAIN_NAME": codebuild.BuildEnvironmentVariable(
            #         value=domain_name
            #     ),
            #     "OWNER": codebuild.BuildEnvironmentVariable(
            #         value=owner
            #     ),
            #     "REPO_NAME": codebuild.BuildEnvironmentVariable(
            #         value=repo_name
            #     ),
            # },
            run_order=2,
        )
        deploy_stage = lambda_pipeline.add_stage(stage_name="Deploy")
        deploy_stage.add_action(deploy_action)
       

        # plan_action = codepipeline_actions.CodeBuildAction(
        #     action_name="Plan",
        #     type = codepipeline_actions.CodeBuildActionType.BUILD,
        #     project=lambda_codebuild_pipeline_project,
        #     input=source_output,
        #     run_order=2,
        #     environment_variables={
        #         "TF_COMMAND": codebuild.BuildEnvironmentVariable(
        #             value="plan"
        #         )
        #     }
        # )
        # plan_stage = lambda_pipeline.add_stage(stage_name="Plan")
        # plan_stage.add_action(plan_action)

        # approval_action = codepipeline_actions.ManualApprovalAction(
        #     action_name="Approve",
        #     run_order = 3,
        # )
        # approval_stage = lambda_pipeline.add_stage(stage_name="Approval")
        # approval_stage.add_action(approval_action)

        # apply_action = codepipeline_actions.CodeBuildAction(
        #     action_name="Apply",
        #     type = codepipeline_actions.CodeBuildActionType.BUILD,
        #     project=lambda_codebuild_pipeline_project,
        #     input=source_output,
        #     run_order=4,
        #     environment_variables={
        #         "TF_COMMAND": codebuild.BuildEnvironmentVariable(
        #             value="apply -auto-approve"
        #         )
        #     }
        # )
        # apply_stage = lambda_pipeline.add_stage(stage_name="Apply")
        # apply_stage.add_action(apply_action)


    def __init__(self, scope, id):
        super().__init__(scope, id)

        domain_name="res-ca-devckd"
        owner=self.account
        repo_name="res-ca-dev"

        random_bucket_suffix = os.getlogin()

        codepipeline_role = ResiliencyFoundationPipelinesStack.createIAMRole(self,
            "resiliencyvr-package-build-pipeline-role",
            ["codepipeline.amazonaws.com","codebuild.amazonaws.com"],
        )
        codebuild_package_role = ResiliencyFoundationPipelinesStack.createIAMRole(self,
            "resiliencyvr_codebuild_package_role",
            ["codebuild.amazonaws.com"],
        )
        codebuild_lambda_role = ResiliencyFoundationPipelinesStack.createIAMRole(self,
            "resiliencyvr_codebuild_lambda_role",
            ["codebuild.amazonaws.com"],
        )

        codeartifact_resources = ResiliencyFoundationPipelinesStack.createCodeArtifactory(self,domain_name,repo_name)
        cfn_domain_res_ca_devckd = codeartifact_resources["cfn_domain_res_ca_devckd"]
        cfn_repository_res_ca_dev = codeartifact_resources["cfn_repository_res_ca_dev"]

        codepipeline_bucket = ResiliencyFoundationPipelinesStack.createCodePipelineBucket(self,random_bucket_suffix)
        codestar_connections_github_arn = "arn:aws:codestar-connections:region:account-id:connection/connection-id"
        codeartifact_domain_res_ca_dev_domain_arn = cfn_domain_res_ca_devckd.attr_arn
        codeartifact_repository_res_ca_dev_arn = cfn_repository_res_ca_dev.attr_arn

        codepipeline_policy = ResiliencyFoundationPipelinesStack.createCodePipelineIAMPolicy(self,
            codepipeline_bucket,
            codestar_connections_github_arn
        )
        codepipeline_policy.attach_to_role(codepipeline_role)

        codebuild_package_policy = ResiliencyFoundationPipelinesStack.createCodeBuildPackageIAMPolicy(self,
            codeartifact_repository_res_ca_dev_arn,
            codeartifact_domain_res_ca_dev_domain_arn,
            codepipeline_bucket,
        )
        codebuild_package_policy.attach_to_role(codebuild_package_role)

        codebuild_lambda_policy = ResiliencyFoundationPipelinesStack.createCodeBuildLambdaIAMPolicy(self,
            codeartifact_repository_res_ca_dev_arn,
            codeartifact_domain_res_ca_dev_domain_arn,
            codepipeline_bucket,
        )
        codebuild_lambda_policy.attach_to_role(codebuild_lambda_role)
        
        resiliencyvr_codebuild_pipeline_project = ResiliencyFoundationPipelinesStack.createResiliencyVRCodeBuildPipelineProject(self,codebuild_package_role,codepipeline_bucket,domain_name,owner,repo_name)
        lambda_codebuild_pipeline_project = ResiliencyFoundationPipelinesStack.createLambdaCodeBuildPipelineProject(self,codebuild_lambda_role,domain_name,owner,repo_name)
        ResiliencyFoundationPipelinesStack.createResiliencyVRPipeline(self,resiliencyvr_codebuild_pipeline_project)
        ResiliencyFoundationPipelinesStack.createLambdaPipeline(self,lambda_codebuild_pipeline_project)
        