from cgi import test
import email
from fileinput import filename
import os
from pyclbr import Function
from sqlite3 import Timestamp
from ssl import _create_default_https_context
import time
from zipfile import ZipFile
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
    core
)

class ResiliencyFoundationStack(core.Stack):
    
    def createTopic(self,email_list):
        topic = sns.Topic(self,"topic")
        delivered = topic.metric_number_of_notifications_delivered()
        failed = topic.metric_number_of_notifications_failed()
        for email in email_list:
            topic.add_subscription(subscriptions.EmailSubscription(email))

        return topic.topic_arn

    def __init__(self, scope, id):
        super().__init__(scope, id)

        #SNS TOPIC WHICH EMAILS/TEXTS THE PROCESSED MESSAGE
        email_list = ["example@verticalrelevance.com"]
        topic_arn = ResiliencyFoundationStack.createTopic(self,email_list)
