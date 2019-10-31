# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import boto3

from activities import Activity
from common import skip_ec2

def lambda_handler(event, context=None):
  if skip_ec2(event):
    # Nothing to check if this is a test run with no EC2 -- quit (and don't
    # repeat).
    return False

  execution_arn = event['execution']
  end_state = event['endState']

  # Get all execution history events.
  client = boto3.client('stepfunctions')

  response = client.get_execution_history(
    executionArn=execution_arn,
    maxResults=1000,
  )
  events = response['events']

  while 'nextToken' in response:
    response = client.get_execution_history(
      executionArn=execution_arn,
      maxResults=1000,
      nextToken=response['nextToken'],
    )
    events += response['events']

  # Quit (and don't repeat) if we've reached the end state.
  for e in events:
    if e.get('stateEnteredEventDetails', {}).get('name') == end_state:
      return False

  # The actual health check: Find any activities that are scheduled but not
  # started and make sure there's a worker ready for each.
  ec2 = boto3.client('ec2')
  for activity_class in get_pending_activities(events):
    activity = activity_class(event)
    if activity.needs_ec2_worker():
      ec2.run_instances(**activity.ec2_params())

  # Wait and repeat.
  return True


def get_pending_activities(events):
  started_event_ids = {
    e['previousEventId'] for e in events if e['type'] == 'ActivityStarted'
  }

  pending_arns = {
    e['activityScheduledEventDetails']['resource'] for e in events
      if e['type'] == 'ActivityScheduled' and not e['id'] in started_event_ids
  }

  if not pending_arns:
    return []

  return [
    a for a in Activity.__subclasses__() if a.activity_arn in pending_arns
  ]
