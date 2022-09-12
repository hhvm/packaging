# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import boto3
import json
from urllib import request

import common


class Activity:
  # Subclasses must override these.
  ec2_iam_arn = None
  activity_arn = None
  script_name = None
  # Optional.
  init_script = None
  after_task_script = None

  def __init__(self, event):
    self.event = event
    self.fake_ec2 = common.fake_ec2(event)
    self.is_test_build = common.is_test_build(event)

  def version(self):
    return self.event['version']

  def platform(self):
    return self.event['platform']

  def worker_env(self):
    # Subclasses can provide extra environment variables for worker.sh (will
    # also be available from self.init_script)
    return {}

  def task_env(self):
    # Subclasses can provide extra environment variables for the individual
    # task's script (self.script_name and self.after_task_script)
    return {}

  def needs_ec2_worker(self):
    # Subclasses may override.
    return True

  def has_ec2_workers(self):
    # pylint: disable=no-member
    for _ in boto3.resource('ec2').instances.filter(
      Filters=[
        {'Name': 'tag:ActivityArn', 'Values': [self.activity_arn]},
        {'Name': 'instance-state-name', 'Values': ['pending', 'running']},
      ],
      MaxResults=5,
    ):
      return True
    return False

  def ec2_params(self):
    if not self.ec2_iam_arn or not self.activity_arn or not self.script_name:
      raise Exception('missing config in ' + type(self).__name__)

    script_url = common.url(
      'aws/hhvm1/worker/dummy-task.sh' if self.fake_ec2
      else 'aws/userdata/' + self.script_name
    )
    init_url = (
      common.url(self.init_script)
        if self.init_script and not self.fake_ec2
        else ''
    )
    after_task_url = (
      common.url(self.after_task_script)
        if self.after_task_script and not self.fake_ec2
        else ''
    )
    return {
      'ImageId': 'ami-03d5c68bab01f3496',  # ubuntu 20.04
      'MaxCount': 1,
      'MinCount': 1,
      'InstanceType': 't2.micro',
      'SecurityGroups': ['hhvm-binary-package-builders'],
      'InstanceInitiatedShutdownBehavior': 'terminate',
      'IamInstanceProfile': {'Arn': self.ec2_iam_arn},
      'KeyName': 'hhvm-package-builders',
      'TagSpecifications': [{
        'ResourceType': 'instance',
        'Tags': [
          {
            'Key': 'Name',
            'Value': 'ww-0-' + type(self).__name__,
          },
          {
            'Key': 'ActivityArn',
            'Value': self.activity_arn,
          },
        ],
      }],
      'UserData': f'''#!/bin/bash
        ACTIVITY_ARN="{self.activity_arn}"
        SCRIPT_URL="{script_url}"
        INIT_URL="{init_url}"
        AFTER_TASK_URL="{after_task_url}"
        {common.format_env(self.worker_env())}
        {common.fetch('aws/hhvm1/worker/worker.sh')}
      ''',
    }


class MakeSourceTarball(Activity):
  ec2_iam_arn = 'arn:aws:iam::223121549624:instance-profile/hhvm-source-tarball-builder'
  activity_arn = 'arn:aws:states:us-west-2:223121549624:activity:hhvm-make-source-tarball'
  script_name = 'make-source-tarball.sh'

  def should_run(self):
    env = common.env_for_version(self.version())
    return not any(
      obj['Key'] == env['S3_PATH']
        for obj in boto3.client('s3')
          .list_objects(Bucket=env['S3_BUCKET'], Prefix=env['S3_PATH'])
          .get('Contents', [])
    )

  def ec2_params(self):
    params = super().ec2_params()
    params.update({
      'BlockDeviceMappings': [{
        'DeviceName': '/dev/sda1',
        'Ebs': {
          'DeleteOnTermination': True,
          'VolumeSize': 16,  # GB
          'VolumeType': 'gp2',
        },
      }],
    })
    return params


class MakeBinaryPackage(Activity):
  ec2_iam_arn = 'arn:aws:iam::223121549624:instance-profile/hhvm-binary-package-builder'
  activity_arn = 'arn:aws:states:us-west-2:223121549624:activity:hhvm-make-binary-package'
  script_name = 'make-binary-package.sh'
  after_task_script = 'aws/hhvm1/worker/after-task/make-binary-package.sh'

  def task_env(self):
    if self.is_test_build:
      return {'SKIP_PUBLISH': '1'}
    return {}

  def should_run(self):
    return common.build_status(self.version(), self.platform()) == 'not_built'

  def ec2_params(self):
    params = super().ec2_params()
    params.update({
      'InstanceType': 'r6i.4xlarge',  # 16 cores, 128GB RAM
      'BlockDeviceMappings': [{
        'DeviceName': '/dev/sda1',
        'Ebs': {
          'DeleteOnTermination': True,
          'VolumeSize': 256,  # GB
          'VolumeType': 'gp2',
        },
      }],
    })
    return params


class PublishBinaryPackages(Activity):
  ec2_iam_arn = 'arn:aws:iam::223121549624:instance-profile/hhvm-repo-builders'
  activity_arn = 'arn:aws:states:us-west-2:223121549624:activity:hhvm-publish-binary-packages'
  script_name = 'update-repos.sh'

  def task_env(self):
    return {'REPOS_ONLY': '1'}

  def should_run(self):
    return any(
      status == 'built_not_published'
        for platform, status in common.build_statuses(self.version()).items()
        if common.is_linux(platform)
    )

  def ec2_params(self):
    params = super().ec2_params()
    params.update({
      # This is required as we have a persistent EBS volume containing the
      # repositories, and the instance must be in the same availability zone
      # as an EBS volume to attach it.
      'Placement': {'AvailabilityZone': 'us-west-2a'},
      'BlockDeviceMappings': [{
        'DeviceName': '/dev/sda1',
        'Ebs': {
          'DeleteOnTermination': True,
          'VolumeSize': 100,  # GB
          'VolumeType': 'gp2',
        },
      }],
    })
    return params

  def needs_ec2_worker(self):
    # These access a shared EBS volume, so only one can run at a time.
    return not self.has_ec2_workers()


class PublishSourceTarball(Activity):
  ec2_iam_arn = 'arn:aws:iam::223121549624:instance-profile/hhvm-source-tarball-builder'
  activity_arn = 'arn:aws:states:us-west-2:223121549624:activity:hhvm-publish-source-tarball'
  script_name = 'publish-release-source.sh'

  def should_run(self):
    if common.is_nightly(self.version()):
      return False
    statuses = common.build_statuses(self.version())
    return (
      statuses.get('source') == 'built_not_published' or
      statuses.get('source_gpg') == 'built_not_published'
    )


class PublishDockerImages(Activity):
  ec2_iam_arn = 'arn:aws:iam::223121549624:instance-profile/hhvm-repo-builders'
  activity_arn = 'arn:aws:states:us-west-2:223121549624:activity:hhvm-publish-docker-images'
  script_name = 'update-repos.sh'

  def task_env(self):
    return {'DOCKER_ONLY': '1'}

  def should_run(self):
    return True


class BuildAndPublishMacOS(Activity):
  ec2_iam_arn = 'arn:aws:iam::223121549624:instance-profile/hhvm-macos-builds-triggerer'
  activity_arn = 'arn:aws:states:us-west-2:223121549624:activity:hhvm-build-and-publish-macos'
  script_name = 'trigger-macos-builds.sh'

  def platforms_to_build(self):
    requested = common.Config.macos_versions.keys()
    if self.event['buildInput']['platforms']:
      requested = {
        p for p in requested if p in self.event['buildInput']['platforms']
      }

    return set() if not requested else {
      platform
        for platform, status in common.build_statuses(self.version()).items()
        if status != 'succeeded' and platform in requested
    }

  def worker_env(self):
    if self.fake_ec2:
      return {}
    return {'SKIP_SEND_TASK_SUCCESS': '1'}

  def task_env(self):
    task_env = {}

    if self.is_test_build:
      task_env['SKIP_PUBLISH'] = '1'

    # Right now we can only correctly trigger a build for a single platform or
    # for all platforms, but the Azure pipeline will skip any platforms that are
    # already built, so at worst this wastes a few CPU cycles.
    platforms = self.platforms_to_build()
    if len(platforms) == 1:
      task_env['PLATFORM'] = common.Config.macos_versions[next(iter(platforms))]

    return task_env

  def should_run(self):
    return bool(self.platforms_to_build())
