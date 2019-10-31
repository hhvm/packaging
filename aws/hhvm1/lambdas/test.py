#!/usr/bin/python3 -W ignore
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from datetime import date, timedelta
import unittest
from unittest.mock import patch

import activities
import check_if_repos_changed
import check_for_failures
from common import Config
import get_platforms_for_version
import health_check
import parse_input
import prepare_activity


class Test(unittest.TestCase):
  maxDiff = None

  def test_parse_input(self):
    debian = 'debian-9-stretch'
    ubuntu = 'ubuntu-19.04-disco'
    self.assertEqual(
      parse_input.lambda_handler({}),
      {
        'buildInput': {
          'versions': [date.today().strftime('%Y.%m.%d')],
          'platforms': [],
          'activities': [],
          'debug': '',
        },
      },
    )
    self.assertEqual(
      parse_input.lambda_handler({
        'foo': ['4.2', 'a', '1.2a'],
        'bar': {'foo': '0.42.0', 'bar': 'MakeBinaryPackage'},
        'baz': '42',
      }),
      {
        'buildInput': {
          'versions': ['0.42.0'],
          'platforms': [],
          'activities': ['MakeBinaryPackage'],
          'debug': '',
        },
      },
    )
    self.assertEqual(
      parse_input.lambda_handler({'inputs': ['--fake-ec2']}),
      {
        'buildInput': {
          'versions': [date.today().strftime('%Y.%m.%d')],
          'platforms': [],
          'activities': [],
          'debug': 'fake_ec2',
        },
      },
    )
    self.assertEqual(
      parse_input.lambda_handler(f'4.26.1 foo {ubuntu} --skip-ec2 {debian}'),
      {
        'buildInput': {
          'versions': ['4.26.1'],
          'platforms': [ubuntu, debian],
          'activities': [],
          'debug': 'skip_ec2',
        },
      },
    )

  def test_get_platforms_for_version(self):
    self.assertEqual(
      get_platforms_for_version.lambda_handler(
        {'version': '4.26.1', 'buildInput': {'platforms': []}},
      ),
      [
        'debian-8-jessie',
        'debian-9-stretch',
        'debian-10-buster',
        'ubuntu-16.04-xenial',
        'ubuntu-18.04-bionic',
        'ubuntu-18.10-cosmic',
        'ubuntu-19.04-disco',
      ],
    )
    self.assertEqual(
      get_platforms_for_version.lambda_handler(
        {'version': '3.30.11', 'buildInput': {'platforms': []}},
      ),
      [
        'debian-8-jessie',
        'debian-9-stretch',
        'ubuntu-14.04-trusty',
        'ubuntu-16.04-xenial',
        'ubuntu-18.04-bionic',
        'ubuntu-18.10-cosmic',
      ],
    )
    self.assertEqual(
      get_platforms_for_version.lambda_handler({
        'version': '4.26.1',
        'buildInput': {'platforms': ['ubuntu-19.04-disco', 'debian-10-buster']},
      }),
      ['debian-10-buster', 'ubuntu-19.04-disco'],
    )
    # incompatible platforms are excluded
    input = {'platforms': ['ubuntu-19.04-disco', 'ubuntu-14.04-trusty']}
    self.assertEqual(
      get_platforms_for_version.lambda_handler(
        {'version': '2019.10.10', 'buildInput': input}
      ),
      ['ubuntu-19.04-disco'],
    )
    self.assertEqual(
      get_platforms_for_version.lambda_handler(
        {'version': '3.30', 'buildInput': input}
      ),
      ['ubuntu-14.04-trusty'],
    )

  def test_ec2_params(self):
    ec2_params = activities.MakeBinaryPackage(
      {'version': '4.26.1', 'platform': 'ubuntu-18.04-bionic'}
    ).ec2_params()
    self.assertEqual(ec2_params['MinCount'], 1)
    self.assertEqual(ec2_params['InstanceType'], 'm5.2xlarge')
    self.assertEqual(
      ec2_params['BlockDeviceMappings'][0]['DeviceName'],
      '/dev/sda1',
    )
    org = Config.override_org or 'hhvm'
    branch = Config.override_branch or 'master'
    expected_prefix = (
      '#!/bin/bash\n'
      '        ACTIVITY_ARN="arn:aws:states:us-west-2:223121549624:activity:'
        'hhvm-make-binary-package"\n'
      f'        SCRIPT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/userdata/make-binary-package.sh"\n'
      '        INIT_URL=""\n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix,
    )

  def test_should_run(self):
    past = (date.today() - timedelta(days=2)).strftime('%Y.%m.%d')
    future = (date.today() + timedelta(days=2)).strftime('%Y.%m.%d')

    self.assertEqual(
      activities.MakeSourceTarball({'version': '4.20.12345'}).should_run(),
      True
    )
    self.assertEqual(
      activities.MakeSourceTarball({'version': past}).should_run(),
      False
    )
    self.assertEqual(
      activities.MakeSourceTarball({'version': future}).should_run(),
      True
    )

    self.assertEqual(
      activities.MakeBinaryPackage(
        {'version': '4.27.0', 'platform': 'ubuntu-18.04-bionic'}
      ).should_run(),
      False
    )
    self.assertEqual(
      activities.MakeBinaryPackage(
        {'version': future, 'platform': 'ubuntu-18.04-bionic'}
      ).should_run(),
      True
    )

    self.assertEqual(
      activities.PublishBinaryPackages({'version': '4.27.0'}).should_run(),
      False
    )
    self.assertEqual(
      activities.PublishSourceTarball({'version': '4.27.0'}).should_run(),
      False
    )

    with patch('common.build_statuses', return_value={
      'ubuntu-18.04-bionic': 'not_built',
      'source_gpg': 'not_built',
    }):
      with self.assertRaisesRegex(
        Exception,
        'cannot publish because there are unbuilt packages: ubuntu-18.04-bionic'
      ):
        activities.PublishBinaryPackages({'version': '4.27.0'}).should_run()
      with self.assertRaisesRegex(
        Exception,
        'cannot publish because there are unbuilt packages: source_gpg'
      ):
        activities.PublishSourceTarball({'version': '4.27.0'}).should_run()

    with patch('common.build_statuses', return_value={
      'ubuntu-18.04-bionic': 'built_not_published',
      'debian-42-zaphod': 'succeeded',
      'source': 'succeeded',
      'source_gpg': 'succeeded',
    }):
      self.assertEqual(
        activities.PublishBinaryPackages({'version': '4.27.0'}).should_run(),
        True
      )
      self.assertEqual(
        activities.PublishSourceTarball({'version': '4.27.0'}).should_run(),
        False
      )

    with patch('common.build_statuses', return_value={
      'ubuntu-18.04-bionic': 'succeeded',
      'source': 'built_not_published',
      'debian-42-zaphod': 'succeeded',
      'source_gpg': 'built_not_published',
    }):
      self.assertEqual(
        activities.PublishBinaryPackages({'version': '4.27.0'}).should_run(),
        False
      )
      self.assertEqual(
        activities.PublishSourceTarball({'version': '4.27.0'}).should_run(),
        True
      )

    self.assertEqual(
      activities.PublishDockerImages({'version': '4.27.0'}).should_run(),
      False
    )
    self.assertEqual(
      activities.PublishDockerImages({'version': past}).should_run(),
      False
    )
    self.assertEqual(
      activities.PublishDockerImages({'version': future}).should_run(),
      True
    )


  def test_prepare_activity(self):
    self.assertEqual(
      prepare_activity.lambda_handler({
        'buildInput': {'debug': 'skip_ec2'},
        'activity': 'MakeBinaryPackage',
        'version': '4.26.12345',
        'platform': 'ubuntu-18.04-bionic',
      }),
      {
        'skip': False,
        'taskInput': {
          'name': 'MakeBinaryPackage-4.26.12345-ubuntu-18.04-bionic',
          'env': (
            'VERSION="4.26.12345"\n'
            'DISTRO="ubuntu-18.04-bionic"\n'
            'IS_NIGHTLY="false"\n'
            'S3_BUCKET="hhvm-scratch"\n'
            'S3_PATH="hhvm-4.26.12345.tar.gz"\n'
            'S3_SOURCE="s3://hhvm-scratch/hhvm-4.26.12345.tar.gz"\n'
            'PACKAGING_BRANCH="HHVM-4.26"'
          ),
        },
      }
    )

    future = (date.today() + timedelta(days=2)).strftime('%Y.%m.%d')
    self.assertEqual(
      prepare_activity.lambda_handler({
        'buildInput': {'debug': 'skip_ec2'},
        'activity': 'PublishDockerImages',
        'version': future,
      }),
      {
        'skip': False,
        'taskInput': {
          'name': f'PublishDockerImages-{future}',
          'env': (
            f'VERSION="{future}"\n'
            'IS_NIGHTLY="true"\n'
            'S3_BUCKET="hhvm-downloads"\n'
            f'S3_PATH="source/nightlies/hhvm-nightly-{future}.tar.gz"\n'
            'S3_SOURCE="s3://hhvm-downloads/source/nightlies/'
              f'hhvm-nightly-{future}.tar.gz"\n'
            'PACKAGING_BRANCH="master"\n'
            'DOCKER_ONLY="1"'
          ),
        },
      }
    )

  def get_check_if_repos_changed_event(self, success, debug=''):
    key = 'success' if success else 'failure'
    return {
      'buildInput': {'debug': debug},
      'results': {
        'ForEachVersion': [
          {'results': {'PublishBinaryPackages': {'failure': {}}}},
          {'results': {'PublishBinaryPackages': {key: {}}}},
        ],
      },
    }

  def test_check_if_repos_changed(self):
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event(False)
      ),
      False
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event(True)
      ),
      True
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event(False, 'skip_ec2')
      ),
      False
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event(True, 'fake_ec2')
      ),
      False
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event(True, 'skip_ec2')
      ),
      False
    )

  def test_check_for_failures(self):
    event = {'results': {'foo': {'success': {}}}}
    self.assertEqual(check_for_failures.lambda_handler(event), event)
    with self.assertRaisesRegex(
      Exception,
      '^The following steps have failed:\nfoo bar$'
    ):
      check_for_failures.lambda_handler(
        {'results': {'foo': {'failure': {'Cause': 'bar'}}}}
      )

    with self.assertRaisesRegex(
      Exception,
      r'^The following steps have failed:\n'
      r'MakeSourceTarball \(4\.2\.0\) \n'
      r'PublishBinaryPackage \(4\.2\.0, debian\) \n'
      r'MakeBinaryPackage \(4\.2\.1, ubuntu\) \n'
      r'PublishBinaryPackage \(4\.2\.1, ubuntu\) \n'
      r'PublishBinaryPackage \(4\.2\.1, debian\) \n'
      r'bar $'
    ):
      check_for_failures.lambda_handler({
        'results': {
          'foo': {'success': {}},
          'ForEachVersion': [
            {
              'version': '4.2.0',
              'results': {
                'MakeSourceTarball': {'failure': {}},
                'ForEachPlatform': [
                  {
                    'platform': 'ubuntu',
                    'results': {'PublishBinaryPackage': {'success': {}}}
                  },
                  {
                    'platform': 'debian',
                    'results': {'PublishBinaryPackage': {'failure': {}}},
                  },
                ],
              },
            },
            {
              'version': '4.2.1',
              'results': {
                'MakeSourceTarball': {'success': {}},
                'ForEachPlatform': [
                  {
                    'platform': 'ubuntu',
                    'results': {
                      'MakeBinaryPackage': {'failure': {}},
                      'PublishBinaryPackage': {'failure': {}},
                    }
                  },
                  {
                    'platform': 'debian',
                    'results': {
                      'MakeBinaryPackage': {'success': {}},
                      'PublishBinaryPackage': {'failure': {}},
                    },
                  },
                ],
              },
            },
          ],
          'bar': {'failure': {}},
        },
      })

  def test_health_check(self):
    execution_arn = (
      'arn:aws:states:us-west-2:223121549624:execution:'
      'one-state-machine-to-rule-them-all:'
      '--fake-ec2_4.27.1_4.-jjergus-2019-10-15-18-33'
    )
    self.assertEqual(
      health_check.lambda_handler({
        'execution': execution_arn,
        'endState': 'CheckIfReposChanged',
      }),
      False
    )
    self.assertEqual(
      health_check.lambda_handler({
        'execution': execution_arn,
        'endState': 'IDoNotExist',
      }),
      True
    )

  def test_get_pending_activities(self):
    events = [
      {
        'type': 'ActivityScheduled',
        'id': 29,
        'activityScheduledEventDetails': {
          'resource':
            'arn:aws:states:us-west-2:223121549624:activity:'
            'hhvm-make-source-tarball',
        }
      },
      {
        'type': 'ActivityScheduled',
        'id': 31,
        'activityScheduledEventDetails': {
          'resource':
            'arn:aws:states:us-west-2:223121549624:activity:'
            'hhvm-make-binary-package',
        }
      },
    ]
    self.assertEqual(
      health_check.get_pending_activities(events),
      [activities.MakeSourceTarball, activities.MakeBinaryPackage]
    )
    events += [{'type': 'ActivityStarted', 'previousEventId': 29}]
    self.assertEqual(
      health_check.get_pending_activities(events),
      [activities.MakeBinaryPackage]
    )
    events += [{'type': 'ActivityStarted', 'previousEventId': 31}]
    self.assertEqual(health_check.get_pending_activities(events), [])


if __name__ == '__main__':
  unittest.main()
