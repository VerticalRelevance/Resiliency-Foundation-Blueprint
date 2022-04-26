import json

import boto3
from chaoslib.types import Configuration
from logzero import logger

from .s3.shared import get_configuration_state


def save_rollback_config(rollback_config: dict,
                         filename: str,
                         configuration: Configuration):
    """Saves a rollback configuration state to S3"""
    state = get_configuration_state(filename, configuration)
    logger.info('Storing state: arn:aws:s3:::%s/%s',
        state.bucket_name, state.key)
    state.put(Body=json.dumps(rollback_config).encode('utf-8'))


def load_rollback_config(filename: str, configuration: Configuration):
    """Loads a configuration state from S3"""
    state = get_configuration_state(filename, configuration)
    logger.info('Loading state: arn:aws:s3:::%s/%s',
        state.bucket_name, state.key)

    try:
        return json.loads(state.get()['Body'].read().decode('utf-8'))
    except boto3.client('s3').exceptions.NoSuchKey:
        logger.info('No state found: arn:aws:s3:::%s/%s',
            state.bucket_name, state.key)
        return None


def delete_rollback_config(filename: str, configuration: Configuration):
    """Deletes a configuration state from S3"""
    state = get_configuration_state(filename, configuration)
    logger.info('Delete state: arn:aws:s3:::%s/%s',
        state.bucket_name, state.key)
    state.delete()
