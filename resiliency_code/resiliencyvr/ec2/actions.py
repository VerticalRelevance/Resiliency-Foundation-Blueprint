import sys
import logging
from typing import List

import boto3
from botocore.exceptions import ClientError
from resiliencyvr.ec2.shared import get_test_instance_ids


def stress_memory(targets: List[str] = None,
					  	test_target_type: str = None,
 					  	tag_key: str = None,
 					  	tag_value: str = None, 
				  		region: str = None,
					  	duration: str = None,
					  	memory_percentage_per_worker: str = None,
					  	number_of_workers: str = None
):

	test_instance_ids = get_test_instance_ids(test_target_type = test_target_type,
											 	tag_key = tag_key,
											 	tag_value = tag_value,
											 	instance_ids = targets)

	parameters = {
		'duration': [
			duration,
		],
		'workers': [
			number_of_workers,
		],
		'percent': [
			memory_percentage_per_worker,
		]
  }

	session = boto3.Session()
	ssm = session.client('ssm', region)
	try:
		response = ssm.send_command(DocumentName = "StressMemory",
										InstanceIds = test_instance_ids,
										CloudWatchOutputConfig = {
                                			'CloudWatchOutputEnabled': True},
										Parameters = parameters)
	except ClientError as e:
		logging.error(e)
		raise

	return(True)

