# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from datetime import date
import re

from activities import Activity, BuildAndPublishMacOS, MakeBinaryPackage
from common import is_binary_platform

def lambda_handler(event, context=None):
  available_activities = {c.__name__ for c in Activity.__subclasses__()}

  versions = []
  platforms = []
  activities = []
  debug = ''

  for part in parts(event):
    if part in ['skip_ec2', 'skip-ec2', '--skip-ec2']:
      debug = 'skip_ec2'
    elif part in ['fake_ec2', 'fake-ec2', '--fake-ec2']:
      debug = 'fake_ec2'
    elif part in ['test', 'test_build', 'test-build', '--test', '--test-build']:
      debug = 'test_build'
    elif part in available_activities:
      activities += [part]
    elif re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', part):
      versions += [part]
    elif is_binary_platform(part):
      platforms += [part]

  if debug == 'test_build':
    available_activities = [
      MakeBinaryPackage.__name__,
      BuildAndPublishMacOS.__name__,
    ]
    for a in activities:
      if a not in available_activities:
        raise Exception(a + ' is not a valid test build step')
    if not activities:
      activities = available_activities

  if not versions:
    versions = [date.today().strftime('%Y.%m.%d')]

  return {
    'buildInput': {
      'versions': versions,
      'platforms': platforms,
      'activities': activities,
      'debug': debug,
    }
  }

def parts(input):
  if type(input) in [list, dict]:
    if type(input) == dict:
      input = input.values()
    return [part for item in input for part in parts(item)]

  return str(input).split(' ')
