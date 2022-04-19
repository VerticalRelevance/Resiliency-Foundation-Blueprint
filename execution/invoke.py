#!/bin/python3

import argparse
import logging
import json
from typing import List


import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.ERROR)


def invoke_lambda(function, payload):

    session = boto3.Session()
    res_lambda = session.client("lambda")

    try:
        response = res_lambda.invoke(FunctionName=function, Payload=payload)
    except ClientError as e:
        logging.error(e)
        raise
    print(response)


def create_payload(bucket, experiment):

    payload = {"bucket_name": bucket, "experiment_source": experiment}
    return json.dumps(payload)


def main():

    parser = argparse.ArgumentParser(
        description="Invoke Resiliency Lambda with payload"
    )
    parser.add_argument(
        "--bucket",
        dest="bucket",
        type=str,
        help="Bucket where experiment files are stored",
        required=True,
    )
    parser.add_argument(
        "--function",
        dest="function",
        type=str,
        help="Name of Resiliency Lambda Function",
        required=True,
    )
    parser.add_argument(
        "--experiment",
        dest="experiment",
        type=str,
        help="Experiment to run",
        required=True,
    )
    args = parser.parse_args()

    payload = create_payload(args.bucket, args.experiment)
    invoke_lambda(args.function, payload)


if __name__ == "__main__":
    main()
