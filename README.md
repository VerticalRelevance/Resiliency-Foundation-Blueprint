
# Resiliency Testing Framework
The Resiliency Testing Framework is a framework to automate resiliency tests in an AWS account. This is accomplished through Chaostoolkit, Python, CDK, and AWS Lambda. This guide is intended to walk a user through the installation process and general use guidelines for the Resiliency Testing repository. This repository is used to house the actions and probes that are referenced by experiments.

## Resiliency Testing Framework Architecture
![image](https://user-images.githubusercontent.com/36248052/161159836-90ba3d9c-4371-480a-b571-25d7228f9f1f.png)


## Installation Guide

### Clone the Repo
First, clone this repository:
```shell
git clone https://github.com/VerticalRelevance/resiliency-framework-code
```
The master branch of this tool is the AWS Branch. All development is done via a personalized branch, *i.e.* ` user_aws `. Once code has been tested and finalized, a Pull Request can be made to the AWS branch to merge the code with the main framework.

 Next, navigate to the checkout the appropriate branch.
```shell
cd resiliency-framework-code
git checkout <branch>
```
This repository holds the actions and probes used in the [Resiliency Testing Experiments](https://github.com/VerticalRelevance/resiliency-framework-experiments.git) repository. 

### Installation
Before installing the code dependencies, we recommend installing and preparing a virtual environment

#### MacOS
First, install pyenv and pyenv virtual-env to allow the creation of new environments. You must then configure your shell to use it. Note: this installation requires [Homebrew](https://brew.sh/) to be installed as well. If it is not, follow the instructions on the linked page to install.
```sh
brew install pyenv pyenv-virtualenv
echo 'eval "$(pyenv init --path)"' >> ~/.zprofile
echo 'eval "$(pyenv init -)"' >> ~/.zshrc
eval "$(pyenv virtualenv-init -)"  >> ~/.zshrc
```
Then, you will need install the version of python which is used by the lambda. You can then create a virtual environment and name it as you please.

```
pyenv install 3.8.11
pyenv virtualenv 3.8.11 <env_name>
```

Then, use the `requirements.txt` file to install the dependencies necessary for development.
```
cd resiliencyvr
pip install -r requirements.txt
```
You are now set to begin creating actions and probes.
## Creating Actions and Probes

Actions and probes are the way that an experiment is able to both induce failure in the environment and get information from the environment. 
* **Actions**:  Python functions referenced by experiments which either induce failure or have some sort of effect on the environment. 
* **Probes**: Python functions which retrieve information from the environment.

### Folder Structure

For each service to be tested, there is a directory created under `resiliency`, *e.g. EC2*. Each directory has between 2 and 3 files: `__init__.py`, `actions.py`, `probes.py` and `shared.py`. The init file is there as a requirement for Chaostoolkit, while the actions file holds the actions for that service and the probes file holds the probes for that service. Not all services require probes or actions. The shared file is used for code that is shared across services. Below is a representation of the folder structure.

<pre>
resiliencyvr
 ┣ az
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┗ shared.py
 ┣ dynamodb
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┗ shared.py
 ┣ ebs
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┗ shared.py
 ┣ ec2
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┗ shared.py
 ┣ k8s
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┣ probes.py
 ┃ ┗ shared.py
 ┣ kafka
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┗ shared.py
 ┣ network
 ┃ ┣ __init__.py
 ┃ ┗ actions.py
 ┣ s3
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┣ probes.py
 ┃ ┗ shared.py
 ┣ ssm
 ┃ ┣ __init__.py
 ┃ ┣ actions.py
 ┃ ┗ probes.py
 ┣ vpc
 ┃ ┣ __init__.py
 ┃ ┗ shared.py
</pre>
### Creating an Action or Probe

Imagine a new experiment is written to stress all network I/O. The experiment will need to reference an action to accomplish this failure. The YAML code referencing the action in the experiment is shown here:
```YAML
type: action
    name: black_hole_network
    provider:
      type: python
      module: resiliencyvr.ec2.actions
      func: gpn_stress_all_network_io
      arguments:
        test_target_type: 'RANDOM'
        tag_key: 'tag:Name'
        tag_value: 'node_value'
        region: 'us-east-1'
        duration: '60'
```
Under `module`, the experiment refers to `resiliencyvr.ec2.actions`. This tells us the corresponding action is referencing the `actions.py` file under the **chaosgpn/ec2/** directory, as discussed in the folder structure section above. That is where the code for all ec2 actions are written. 
<pre>
resiliencyvr
 ┣ <b>ec2</b>
 ┃ ┣ __init__.py
 ┃ ┣ <b>actions.py</b>
 ┃ ┗ shared.py
 </pre>

Many custom functions are required to have these arguments: 
 * `test_target_type` :  'ALL' or 'RANDOM'. Determines if the action/probe is run on 1 randomly selected instance or all instances.
 * `test_target_key`  :  'tag:Name'. The tag key of the tag used to identify the instance(s) the action/probe is run on.
 * `test_target_value` : The tage value used to identify the instance(s) to run the action/probe on.
 
Actions which require command line utilities such as `stress-ng` or `tc` will require the use of an SSM document. For the Stress Network I/O function, we will need a duration of time for the failure to take place. Since this action will require the use of a command line utility, we will use an SSM document in this example. The function header for our Stress Network I/O function will look like this: 

 ```Python
 def stress_all_network_io(targets: List[str] = None,
							   test_target_type: str ='RANDOM',
							   tag_key: str = None, 
							   tag_value: str = None, 
				  			   region: str = 'us-east-1',
							   duration: str = None):
```

The first step of the function is to identify the EC2 instance on which the test will run. This requires the use of a shared function, `get_test_instance_ids`. This is where we will use the arguments passed to the function. In order to use this function, you must make sure to import the function to the `actions.py` file.
```python
from resiliencyvr.ec2.shared import gpn_get_test_instance_ids
```
We can then call the function using the arguments passed into the function such as the `tag_key`, `tag_value`, and `test_target_type`. `tag_key` is a tag key such as "tag:Name", and `tag_value` refers to the value associated with that key. The `test_target_type` parameter determines if the function returns 1 random instance-id or all instance-ids associated with that tag. These parameters are passed from the experiment.
```python
test_instance_ids = get_test_instance_ids(test_target_type = test_target_type, tag_key = tag_key, tag_value = tag_value)
```
Next, we set the parameters required for the SSM document. 
```python
parameters = {'duration': [duration,]}
```
Since we are using a command line utility to complete this action, this action calls an SSM document, "StressAllNetworkIO". This is done via [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html). First we create a boto3 ssm client, then use that ssm client to issue a Systems Manager `runCommand` using the SSM Document  "StressAllNetworkIO". Then, we use the boto3 `send_command` function to run our commands. 
Some of the parameters sent via boto3:
* `DocumentName`: The name of the SSM document which to run
* `InstanceIds`: the instance-ids of the instance too run the commands on.
* `CloudwatchOutputConfig`: Determines if the output is sent to CloudWatch for monitoring purposes.
* `OutputS3BucketName`: Gives the name of the S3 bucket used for SSM stdout. For monitoring purposes like CloudWatch
* `Parameters`: This is the list of parameters to be sent to the SSM document being run by this function. These parameters were set in the last step. 
 
We also attempt to catch any ClientErrors returned by the boto3 function call. 
```python
session = boto3.Session()
ssm = session.client('ssm', region)
	try:
		response = ssm.send_command(DocumentName = "StressAllNetworkIO",
									InstanceIds = test_instance_ids,
									CloudWatchOutputConfig = {
                                		'CloudWatchOutputEnabled':True
                                    },
                                    OutputS3BucketName = 'resiliency-ssm-command-output'
									Parameters = parameters)
	except ClientError as e:
		logging.error(e)
		raise
return response
```

We then return the response from boto3 as the result of the action. This concludes the body of the function. We have now written our first action to go along with an experiment! Please refer to [Resiliency Testing Experiments](https://github.com/VerticalRelevance/resiliency-framework-experiments.git) repository to learn about Experiment creation in YAML.

## Deployment
Deploy using the CI/CD pipeline of your choice. An example CDK and AWS CodePipeline-based build is included in this repository under ./cdk_pipelines. To start, simply issue `cdk deploy` in the `cdk_pipelines` directory of this repository.

## Building and using the resiliency package
To utilize the code written in this repository in experiments, you will be required to build and upload the package `resiliencyvr` to a private PyPi repository, or have it built and have the pip command in the Lambda CDK point to it. A CI/CD pipeline to build the package and upload it to AWS CodeArtifact is under ./cdk_pipelines/ResiliencyAutomationPipelines.

 
