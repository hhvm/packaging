# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import boto3
import functools
import json
import re
from urllib import request

class Config:
  override_org = None
  override_branch = None
  map_states = {
    # state name: map key
    'ForEachVersion': 'version',
    'ForEachPlatform': 'platform',
  }
  macos_versions = {
    # key: name as reported by build_statuses()
    # value: version as reported by sw_vers -productVersion | cut -d . -f 1,2
    # note: activity.BuildAndPublishMacOS depends on this having at most 2 items
    'macos-high_sierra': '10.13',
    'macos-mojave': '10.14',
  }

def is_nightly(version):
  return re.fullmatch(r'[0-9]{4}\.[0-9]{2}\.[0-9]{2}', version)

def is_binary_platform(platform):
  return re.fullmatch(r'(debian|ubuntu)-[0-9\.]+-[a-z]+', platform)

def branch(version):
  if not version or is_nightly(version):
    return 'master'
  else:
    return 'HHVM-' + re.match(r'[0-9]+\.[0-9]+', version)[0]

def url(path, version=None):
  org = 'hhvm'
  br = branch(version)

  # overrides from Config only apply to URLs without version
  if not version:
    org = Config.override_org or org
    br = Config.override_branch or br

  return f'https://raw.githubusercontent.com/{org}/packaging/{br}/{path}'

def fetch(path, version=None):
  return request.urlopen(url(path, version)).read().decode('ascii')

def env_for_version(version):
  env = {
    'IS_NIGHTLY': 'true',
    'S3_BUCKET': 'hhvm-downloads',
    'S3_PATH': f'source/nightlies/hhvm-nightly-{version}.tar.gz',
  } if is_nightly(version) else {
    'IS_NIGHTLY': 'false',
    'S3_BUCKET': 'hhvm-scratch',
    'S3_PATH': f'hhvm-{version}.tar.gz',
  }
  env['S3_SOURCE'] = 's3://{S3_BUCKET}/{S3_PATH}'.format(**env)
  env['PACKAGING_BRANCH'] = branch(version)
  return env

def format_env(env):
  return '\n'.join([f'{var}="{value}"' for var, value in env.items()])

@functools.lru_cache()
def build_statuses(version):
  response = json.loads(
    boto3.client('lambda').invoke(
      FunctionName='hhvm-get-build-status',
      Payload='{"version":"' + version + '"}',
    )['Payload'].read().decode('ascii')
  )
  return {
    platform: status
      for status in ['succeeded', 'built_not_published', 'not_built']
      for platform in response.get(status, {})
  }

def build_status(version, platform):
  return build_statuses(version)[platform]

# debugging options
def skip_ec2(event):
  return event.get('buildInput', {}).get('debug') == 'skip_ec2'

def fake_ec2(event):
  return event.get('buildInput', {}).get('debug') == 'fake_ec2'

def normalize_results(results):
  """
  The state machine output has some unnecessary nesting due to how the state
  machine is structured -- this cleans it up:

  - unnecessary nesting due to "parallel states" is flattened
  - lists of version/platform outputs are normalized into a map of results keyed
    by the version/platform
  - this makes the state machine output robust against changes like adding a new
    state that runs in parallel with some existing states, which is important
    because the logic in check_if_repos_changed and check_for_failures depends
    on the structure of the results
  """

  normalized = {}

  for state_name, result in results.items():
    if state_name in Config.map_states:
      # convert from list to map
      key = Config.map_states[state_name]
      normalized[state_name] = {
        item[key]: normalize_results(item['results']) for item in result
      }
    elif type(result) == list:
      # flatten
      for item in result:
        normalized.update(normalize_results(item['results']))
    else:
      # just remove some redundant stuff
      result.pop('taskInput', None)
      if result.get('skip') == False:
        del result['skip']
      normalized[state_name] = result

  return normalized
