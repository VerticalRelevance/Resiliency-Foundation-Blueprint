import io
import logging
import sys

from resiliencyvr.s3.shared import get_object, create_presigned_url
from chaoslib.experiment import run_experiment
from chaoslib.loader import load_experiment
from chaostoolkit.logging import configure_logger
from logzero import logger


configure_logger()


# name the package: resiliency (chaostoolkit-resiliency)

def handler(event, context):
  """Runs an experiment by `experiment_source`.

  Provide the following event data to invoke the function:

  {
    "experiment_source": "authorizations/tc001.yml",
    "bucket_name": "chaos-testing-bucket",
    ...(additional values for running experiment: AZ, Region, Environment, etc.)
  }
  """
  log_capture, report_capture = __capture_experiment_logs()

  experiment_source = event.get('experiment_source')
  if experiment_source:
    logger.info('ChaosToolkit attempting to load experiment: %s', experiment_source)

  try:
    get_object(event.get('bucket_name'), experiment_source, event.get('configuration', {}))
  except Exception as e:
    logger.exception('Unable to retrieve experiment %s: %s', experiment_source, e)
  
  experiment = load_experiment(create_presigned_url(event.get('bucket_name'), experiment_source))

  run_experiment(experiment)

  # If any errors were captured, exit with non-zero status
  # (shows as failure in Lambda)
  if log_capture.getvalue():
    sys.exit(1)


def __capture_experiment_logs():
  """Captures logs for ChaosToolkit experiments"""
  log_capture_string = io.StringIO()
  error_handler = logging.StreamHandler(log_capture_string)
  error_handler.setLevel(logging.ERROR)
  logger.addHandler(error_handler)

  report_capture_string = io.StringIO()
  info_handler = logging.StreamHandler(report_capture_string)
  info_handler.setLevel(logging.INFO)
  logger.addHandler(info_handler)

  return log_capture_string, report_capture_string
