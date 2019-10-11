from datetime import date
import re

from activities import Activity
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
    elif part in available_activities:
      activities += [part]
    elif re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+', part):
      versions += [part]
    elif is_binary_platform(part):
      platforms += [part]

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
