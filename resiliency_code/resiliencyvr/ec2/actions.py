import sys
import logging
from typing import List
from time import sleep

import boto3
from botocore.exceptions import ClientError
from resiliencyvr.ec2.shared import get_test_instance_ids, get_role_from_instance_profile, get_instance_profile_name


def stress_memory(targets: List[str] = None,
					  	test_target_type: str = None,
 					  	tag_key: str = None,
 					  	tag_value: str = None, 
				  		region: str = None,
					  	duration: str = None,
					  	memory_percentage_per_worker: str = None,
					  	number_of_workers:  str = None
):

	function_name = sys._getframe(  ).f_code.co_name

	test_instance_ids = get_test_instance_ids(test_target_type = test_target_type,
											 	tag_key = tag_key,
											 	tag_value = tag_value,
											 	instance_ids = targets)
	logging.info(function_name, "(): test_instance_ids= ", test_instance_ids)

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

def stress_cpu(targets: List[str] = None,
					  	test_target_type: str = None,
 					  	tag_key: str = None,
 					  	tag_value: str = None, 
				  		region: str = None,
					  	duration: str = None,
					  	cpu: str = None
):

	function_name = sys._getframe(  ).f_code.co_name

	test_instance_ids = get_test_instance_ids(test_target_type = test_target_type,
											 	tag_key = tag_key,
											 	tag_value = tag_value,
											 	instance_ids = targets)
	logging.info(function_name, "(): test_instance_ids= ", test_instance_ids)

	parameters = {
		'duration': [
			duration,
		],
		'cpu': [
			cpu,
		]
  }

	session = boto3.Session()
	ssm = session.client('ssm', region)
	try:
		response = ssm.send_command(DocumentName = "StressCPU",
										InstanceIds = test_instance_ids,
										CloudWatchOutputConfig = {
                                			'CloudWatchOutputEnabled': True},
										Parameters = parameters)
	except ClientError as e:
		logging.error(e)
		raise

	return(True)

def terminate_instance(targets: List[str] = None,
							test_target_type: str ='RANDOM',
							tag_key: str = None, 
							tag_value: str = None, 
							region: str = 'us-east-1',
							):
	function_name = sys._getframe(  ).f_code.co_name
	test_instance_ids = get_test_instance_ids(test_target_type = test_target_type,
											 	  tag_key = tag_key,
											 	  tag_value = tag_value,
											 	  instance_ids = targets)
	logging.info(function_name, "(): test_instance_ids= ", test_instance_ids)

	session = boto3.Session()
	ec2 = session.client('ec2', region)

	try:
		response = ec2.terminate_instances(InstanceIds=test_instance_ids)
	except ClientError as e:
		logging.error(e)
		raise

	return(True)