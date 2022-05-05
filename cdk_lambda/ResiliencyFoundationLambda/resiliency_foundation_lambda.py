from cgi import test
from fileinput import filename
from multiprocessing import Condition
import os
from random import random
from sqlite3 import Timestamp
from ssl import _create_default_https_context
from unicodedata import category
import zipfile
import random
from zipfile import ZipFile
import yaml
import shutil
import aws_cdk as core
from aws_cdk import (
    aws_iam as iam,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy,
    aws_lambda as lambda_,
    aws_kms as kms,
    aws_ssm as ssm,
    Stack
)

class ResiliencyFoundationLambdaStack(Stack):
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
   
    def uploadLambdaCode(self,random_bucket_suffix,domain_name,owner,repo_name):
        resiliency_reqs_path="../resiliency_code/lambda/requirements.txt"
        # os.system("pip install -r "+resiliency_reqs_path)
        # with open(resiliency_reqs_path) as f:
        #     lines = f.readlines()
        #     print(lines

        print("aws codeartifact login --tool pip --domain {} --domain-owner {} --repository {}".format(domain_name,owner,repo_name))
        os.system("aws codeartifact login --tool pip --domain {} --domain-owner {} --repository {}".format(domain_name,owner,repo_name))
        print("Attempting to run pip requirements below:")
        os.system("pip install -r {} -t ../resiliency_code/lambda".format(resiliency_reqs_path))
               
        def zipdir(path, ziph):
            # ziph is zipfile handle
            for root, dirs, files in os.walk(path):
                for file in files:
                    ziph.write(os.path.join(root, file), 
                            os.path.relpath(os.path.join(root, file), 
                                            os.path.join(path, '..')))
        
        with zipfile.ZipFile('resiliency_code.zip', 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipdir('../resiliency_code/lambda', zipf)

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
            handler="handler.handler",
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
    
    def uploadSSMDocument(self):
        
        with open('ssm/StressMemory.yml') as file:
            try:
                ssm_doc = yaml.safe_load(file)   
            except yaml.YAMLError as e:
                print(e)
       
            ssm_document=ssm.CfnDocument(
                self,'StressMemory',
                name="StressMemory",
                content=ssm_doc,
                document_format="YAML",
                document_type="Command"
            )

            return ssm_document

    def uploadExperiments(self, random_bucket_suffix):

        experiment_bucket = s3.Bucket(self, "resiliency-experiment-bucket-"+random_bucket_suffix, bucket_name="resiliency-experiment-bucket"+random_bucket_suffix,access_control=s3.BucketAccessControl.PRIVATE)

        experiment_upload = s3deploy.BucketDeployment(self, "ExperimentFiles",
            sources=[s3deploy.Source.asset("./experiments")],
            destination_bucket=experiment_bucket,
        )

        return experiment_bucket, experiment_upload
        
    def __init__(self, scope, id):
        super().__init__(scope, id)
        try:
            random_bucket_suffix = os.getlogin()
        except:
            random_bucket_suffix = str(random.randint(100000,999999))

        domain_name="res-ca-devckd"
        #owner=core.Token.as_string(self.account)
        owner=os.getenv("CDK_DEFAULT_ACCOUNT")
        repo_name="res-ca-dev"

        s3_key = ResiliencyFoundationLambdaStack.createKMSKey(self,"s3_key","Customer managed KMS key to encrypt S3 resources")
        resiliency_lambda_role = ResiliencyFoundationLambdaStack.createIAMRole(self,"resiliency_lambda_role",["lambda.amazonaws.com"])
        resiliency_lambda_policy = ResiliencyFoundationLambdaStack.createResiliencyLambdaIAMPolicy(self)
        resiliency_lambda_policy.attach_to_role(resiliency_lambda_role)
        
        code_upload_resources = ResiliencyFoundationLambdaStack.uploadLambdaCode(self,random_bucket_suffix,domain_name,owner,repo_name)
        code_upload = code_upload_resources["code_upload"]
        lambda_code_bucket = code_upload_resources["lambda_code_bucket"]
        experiment_resources = ResiliencyFoundationLambdaStack.uploadExperiments(self,random_bucket_suffix)

        lambda_function = ResiliencyFoundationLambdaStack.createFunction(self,resiliency_lambda_role,lambda_code_bucket,code_upload)
        ssm_document = ResiliencyFoundationLambdaStack.uploadSSMDocument(self)