# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import boto3
import random
from time import sleep

import activities
from common import env_for_version, fake_ec2, skip_ec2

def lambda_handler(event, context=None):
  activity_name = event['activity']
  requested_activities = event.get('buildInput', {}).get('activities', [])

  if requested_activities and activity_name not in requested_activities:
    return {'skip': True}

  activity_class = getattr(activities, activity_name)
  activity = activity_class(event)

  # spread these out, in case several run at once
  sleep(random.uniform(1, 10))

  if not skip_ec2(event) and not fake_ec2(event) and not activity.should_run():
    return {'skip': True}

  if not skip_ec2(event) and activity.needs_ec2_worker():
    boto3.client('ec2').run_instances(**activity.ec2_params())

  version = event['version']
  task_name = f'{activity_name}-{version}'
  env = {'VERSION': version}

  if 'platform' in event:
    task_name += '-{platform}'.format(**event)
    env['DISTRO'] = event['platform']

  env.update(env_for_version(version))
  env.update(activity.env)

  return {
    'skip': False,
    'taskInput': {
      'name': task_name,
      'env': '\n'.join([f'{var}="{value}"' for var, value in env.items()]),
    },
  }
