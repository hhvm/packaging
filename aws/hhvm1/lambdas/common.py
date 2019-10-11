import boto3
import functools
import json
import re
from urllib import request

class Config:
  override_org = 'jjergus'
  override_branch = 'hhvm1'

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
