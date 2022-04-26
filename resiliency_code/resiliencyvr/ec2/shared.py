import sys
import boto3
import logging
from random import randint
from typing import List

logging.basicConfig(level=logging.ERROR)


def get_random_instance_id_by_tag(tagKey, tagValue):
    """Returns an instance id from a given tagname"""
    
    session = boto3.Session()
    ec2 = session.client('ec2', 'us-east-1')

    filters = [{'Name': tagKey, 'Values': [ tagValue ],},]

    instance_list = ec2.describe_instances(Filters = filters)
    instance_id = None

    num_instances = len(instance_list['Reservations'])

    if (num_instances <= 0): 
        logging.error("Error with finding instance-id")
        return 0

    index = randint(0, num_instances - 1)
    instance_id = instance_list['Reservations'][index]['Instances'][0]['InstanceId']

    return instance_id

def get_all_instance_ids_by_tag(tagKey, tagValue):
    """Returns a list of instance ida from a given tagname"""
    
    session = boto3.Session()
    ec2 = session.client('ec2', 'us-east-1')
    
    instance_list = ec2.describe_instances(
        Filters=[{'Name': tagKey, 
                  'Values': [ tagValue ],},],)
    instance_ids = []

    num_instances = len(instance_list['Reservations'])

    if (num_instances <= 0): 
        logging.error("Error with finding instance-id")
        return instance_ids

    for instance in instance_list['Reservations']:
        instance_ids.append(instance['Instances'][0]['InstanceId'])

    return instance_ids


def get_test_instance_ids(test_target_type: str ='RANDOM',
                              tag_key: str = 'tag:Name',
                              tag_value: str = 'nodes.resiliencyvr-us-east-1.k8s.local',
                              instance_ids: List[str] = None):

    test_instance_ids = []

    if (test_target_type == "RANDOM"):
        test_instance_id = get_random_instance_id_by_tag(tag_key, tag_value)
        test_instance_ids = [test_instance_id,]
    elif (test_target_type == 'ALL'):
        test_instance_ids = get_all_instance_ids_by_tag(tag_key, tag_value)
    elif (test_target_type == 'NAMED_LIST'):
        test_instance_ids = instance_ids
    else: 
        logging.error('Illegal test target type specified.')
        return(False)

    return(test_instance_ids)


def get_instance_profile_name(tagKey, tagValue):
    """Returns a str of instance IAM profile instances 'name' from a given tagname"""
    
    session = boto3.Session()
    ec2 = session.client('ec2', 'us-east-1')
    
    instance_list = ec2.describe_instances(
        Filters=[{'Name': tagKey, 
                  'Values': [ tagValue ],},],)

    instance_profile_arn = instance_list['Reservations'][0]['Instances'][0]['IamInstanceProfile']['Arn']
    
    return instance_profile_arn.split('/')[1]

def get_role_from_instance_profile(instanceProfile: str = None):
    session = boto3.Session()
    iam = session.client('iam', 'us-east-1')

    instance_profile = iam.get_instance_profile(InstanceProfileName = instanceProfile)
    #print(instance_profile['InstanceProfile']['Roles'][0]['RoleName'])
    return instance_profile['InstanceProfile']['Roles'][0]['RoleName']

