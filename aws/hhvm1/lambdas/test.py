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
import normalize_results
import parse_input
import prepare_activity


class Test(unittest.TestCase):
  maxDiff = None

  def test_parse_input(self):
    debian = 'debian-9-stretch'
    ubuntu = 'ubuntu-19.04-disco'
    macos = next(iter(Config.macos_versions))
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
      parse_input.lambda_handler(
        f'4.26.1 {macos} foo {ubuntu} --skip-ec2 {debian}'
      ),
      {
        'buildInput': {
          'versions': ['4.26.1'],
          'platforms': [macos, ubuntu, debian],
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
      f'        AFTER_TASK_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/hhvm1/worker/after-task/make-binary-package.sh"\n'
      '        \n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix,
    )

    # has INIT_URL
    ec2_params = activities.PublishBinaryPackages({}).ec2_params()
    expected_prefix = (
      '#!/bin/bash\n'
      '        ACTIVITY_ARN="arn:aws:states:us-west-2:223121549624:activity:'
        'hhvm-publish-binary-packages"\n'
      f'        SCRIPT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/userdata/update-repos.sh"\n'
      f'        INIT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/hhvm1/worker/init/update-repos.sh"\n'
      '        AFTER_TASK_URL=""\n'
      '        \n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix
    )

    # overrides worker_env()
    ec2_params = activities.BuildAndPublishMacOS({}).ec2_params()
    expected_prefix = (
      '#!/bin/bash\n'
      '        ACTIVITY_ARN="arn:aws:states:us-west-2:223121549624:activity:'
        'hhvm-build-and-publish-macos"\n'
      f'        SCRIPT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/userdata/trigger-macos-builds.sh"\n'
      '        INIT_URL=""\n'
      '        AFTER_TASK_URL=""\n'
      '        SKIP_SEND_TASK_SUCCESS="1"\n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix
    )

    # fake_ec2 (should change SCRIPT_URL and remove AFTER_TASK_URL)
    ec2_params = activities.MakeBinaryPackage({
      'buildInput': {'debug': 'fake_ec2'},
      'version': '4.26.1',
      'platform': 'ubuntu-18.04-bionic',
    }).ec2_params()
    expected_prefix = (
      '#!/bin/bash\n'
      '        ACTIVITY_ARN="arn:aws:states:us-west-2:223121549624:activity:'
        'hhvm-make-binary-package"\n'
      f'        SCRIPT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/hhvm1/worker/dummy-task.sh"\n'
      '        INIT_URL=""\n'
      f'        AFTER_TASK_URL=""\n'
      '        \n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix,
    )

    # fake_ec2 (should change SCRIPT_URL and remove INIT_URL)
    ec2_params = activities.PublishBinaryPackages(
      {'buildInput': {'debug': 'fake_ec2'}}
    ).ec2_params()
    expected_prefix = (
      '#!/bin/bash\n'
      '        ACTIVITY_ARN="arn:aws:states:us-west-2:223121549624:activity:'
        'hhvm-publish-binary-packages"\n'
      f'        SCRIPT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/hhvm1/worker/dummy-task.sh"\n'
      '        INIT_URL=""\n'
      '        AFTER_TASK_URL=""\n'
      '        \n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix
    )

    # fake_ec2 (should change SCRIPT_URL and remove SKIP_SEND_TASK_SUCCESS)
    ec2_params = activities.BuildAndPublishMacOS(
      {'buildInput': {'debug': 'fake_ec2'}}
    ).ec2_params()
    expected_prefix = (
      '#!/bin/bash\n'
      '        ACTIVITY_ARN="arn:aws:states:us-west-2:223121549624:activity:'
        'hhvm-build-and-publish-macos"\n'
      f'        SCRIPT_URL="https://raw.githubusercontent.com/{org}/packaging/'
        f'{branch}/aws/hhvm1/worker/dummy-task.sh"\n'
      '        INIT_URL=""\n'
      '        AFTER_TASK_URL=""\n'
      '        \n'
      '        #!/bin/bash\n'
    )
    self.assertEqual(
      ec2_params['UserData'][:len(expected_prefix)],
      expected_prefix
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

    # we don't publish if nothing is "built_not_published"
    with patch('common.build_statuses', return_value={
      'ubuntu-18.04-bionic': 'not_built',
      'source_gpg': 'not_built',
    }):
      self.assertEqual(
        activities.PublishBinaryPackages({'version': '4.27.0'}).should_run(),
        False
      )
      self.assertEqual(
        activities.PublishSourceTarball({'version': '4.27.0'}).should_run(),
        False
      )

    # we publish even if not everything is built
    with patch('common.build_statuses', return_value={
      'debian-8-jessie': 'not_built',
      'ubuntu-18.04-bionic': 'built_not_published',
      'source': 'not_built',
      'source_gpg': 'built_not_published',
    }):
      self.assertEqual(
        activities.PublishBinaryPackages({'version': '4.27.0'}).should_run(),
        True
      )
      self.assertEqual(
        activities.PublishSourceTarball({'version': '4.27.0'}).should_run(),
        True
      )

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

    # we shouldn't do a useless build_statuses() API call for nightlies
    with patch('common.build_statuses') as mock_function:
      self.assertEqual(
        activities.PublishSourceTarball({'version': future}).should_run(),
        False
      )
      self.assertEqual(mock_function.called, False)

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
        # skip_ec2 causes this to be True, but the taskInput is still included
        # since it's useful for debugging
        'skip': True,
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

  def get_check_if_repos_changed_event(self, successes, debug=''):
    keys = ['success' if success else 'failure' for success in successes]
    return {
      'buildInput': {'debug': debug},
      'results': {
        'ForEachVersion': [
          {
            'version': '3.30.12',
            'results': {
              'MakeSourceTarball': {'success': {}},
              'PublishBinaryPackages': {'failure': {}},
              'PublishSourceTarballAndPublishDockerImages': [
                {'results': {'PublishSourceTarball': {keys[0]: {}}}},
                {'results': {'PublishDockerImages': {'success': {}}}},
              ],
            },
          },
          {
            'version': '4.42.0',
            'results': {'PublishBinaryPackages': {keys[1]: {}}},
          },
        ],
      },
    }

  def test_check_if_repos_changed(self):
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([False, False])
      ),
      False
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([False, True])
      ),
      True
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([True, False])
      ),
      True
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([True, True])
      ),
      True
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([False, False], 'skip_ec2')
      ),
      False
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([False, True], 'fake_ec2')
      ),
      False
    )
    self.assertEqual(
      check_if_repos_changed.lambda_handler(
        self.get_check_if_repos_changed_event([True, True], 'skip_ec2')
      ),
      False
    )
    # test nightly special case
    self.assertEqual(
      check_if_repos_changed.lambda_handler({
        'results': {
          'ForEachVersion': [
            {
              'version': '2019.11.01',
              'results': {'MakeSourceTarball': {'success': {}}},
            },
          ],
        },
      }),
      True
    )

  def test_normalize_results_and_check_for_failures(self):
    v1 = '3.30.12'
    v1_before = {
      'version': v1,
      'results': {
        'MakeSourceTarball': {'skip': True},
        'ForEachPlatform': [
          {
            'platform': 'debian-8-jessie',
            'results': {
              'MakeBinaryPackage': {'success': {'ec2': 'i-faceb001'}},
            },
          },
          {
            'results': {
              'MakeBinaryPackage': {'skip': True},
            },
            'platform': 'ubuntu-14.04-trusty',
          },
        ],
        'PublishSourceTarballAndPublishDockerImages': [
          {
            'results': {
              'PublishSourceTarball': {
                'skip': False,
                'taskInput': {
                  'name': 'PublishSourceTarball-3.30.12',
                  'env': 'VERSION="3.30.12"\nIS_NIGHTLY="false"',
                },
                'success': {'ec2': 'i-faceb002'},
              },
            },
          },
          {
            'results': {
              'PublishDockerImages': {'success': {'ec2': 'i-faceb003'}},
            },
          },
        ],
      },
    }
    v1_after = {
      'MakeSourceTarball': {'skip': True},
      'ForEachPlatform': {
        'debian-8-jessie': {
          'MakeBinaryPackage': {'success': {'ec2': 'i-faceb001'}},
        },
        'ubuntu-14.04-trusty': {
          'MakeBinaryPackage': {'skip': True},
        },
      },
      'PublishSourceTarball': {'success': {'ec2': 'i-faceb002'}},
      'PublishDockerImages': {'success': {'ec2': 'i-faceb003'}},
    }
    v2 = '4.42.0'
    v2_before = {
      'version': v2,
      'results': {'foo': {'skip': True}},
    }
    v2_after = {
      'foo': {'skip': True},
    }
    parallel_steps_before = [
      {
        'results': {
          'UpdateIndices': {'success': {'ec2': 'i-faceb004'}},
        },
      },
      {
        'results': {
          'InvalidateCloudFront': {'success': {'ec2': 'i-faceb005'}},
        },
      },
    ]
    everything_after = {
      'ForEachVersion': {
        v1: v1_after,
        v2: v2_after,
      },
      'UpdateIndices': {'success': {'ec2': 'i-faceb004'}},
      'InvalidateCloudFront': {'success': {'ec2': 'i-faceb005'}},
    }
    # normalization inside ForEachVersion
    self.assertEqual(normalize_results.lambda_handler(v1_before), v1_after)
    self.assertEqual(normalize_results.lambda_handler(v2_before), v2_after)
    # final normalization after ForEachVersion
    self.assertEqual(
      check_for_failures.lambda_handler(normalize_results.lambda_handler({
        'buildInput': {},
        'results': {
          'ForEachVersion': [
            {
              'version': v1,
              'results': v1_after,
            },
            {
              'version': v2,
              'results': v2_after,
            },
          ],
          'UpdateIndicesAndInvalidateCloudFront': parallel_steps_before,
        },
      })),
      everything_after
    )
    # normalization of everything at once (not used right now but was used in
    # the past and we may need it again at some point)
    self.assertEqual(
      check_for_failures.lambda_handler(normalize_results.lambda_handler({
        'buildInput': {},
        'results': {
          'ForEachVersion': [
            v1_before,
            v2_before,
          ],
          'UpdateIndicesAndInvalidateCloudFront': parallel_steps_before,
        },
      })),
      everything_after
    )

    with self.assertRaisesRegex(
      Exception,
      '^The following steps have failed:\nfoo bar$'
    ):
      check_for_failures.lambda_handler(normalize_results.lambda_handler(
        {'results': {'foo': {'failure': {'Cause': 'bar'}}}}
      ))

    with self.assertRaisesRegex(
      Exception,
      '^The following steps have failed:\n'
      'MakeSourceTarball 4.2.0 \n'
      'PublishBinaryPackage 4.2.0 debian \n'
      'MakeBinaryPackage 4.2.1 ubuntu \n'
      'PublishBinaryPackage 4.2.1 ubuntu \n'
      'PublishBinaryPackage 4.2.1 debian \n'
      'bar $'
    ):
      check_for_failures.lambda_handler(normalize_results.lambda_handler({
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
      }))

  def test_health_check(self):
    execution_arn = (
      'arn:aws:states:us-west-2:223121549624:execution:'
      'one-state-machine-to-rule-them-all:'
      '4.43.0-jjergus-2020-02-03-09-33'
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

  def test_build_and_publish_macos(self):
    future = (date.today() + timedelta(days=2)).strftime('%Y.%m.%d')
    macos1, macos2 = list(Config.macos_versions.keys())[:2]

    activity = activities.BuildAndPublishMacOS(
      {'version': future, 'buildInput': {'platforms': []}}
    )
    self.assertEqual(
      activity.platforms_to_build(),
      Config.macos_versions.keys()
    )
    self.assertEqual(activity.should_run(), True)
    self.assertEqual(activity.task_env(), {})

    activity = activities.BuildAndPublishMacOS(
      {'version': future, 'buildInput': {'platforms': [macos1, 'ubuntu']}}
    )
    self.assertEqual(activity.platforms_to_build(), {macos1})
    self.assertEqual(activity.should_run(), True)
    self.assertEqual(
      activity.task_env(),
      {'PLATFORM': Config.macos_versions[macos1]}
    )

    activity = activities.BuildAndPublishMacOS(
      {'version': future, 'buildInput': {'platforms': [macos1, macos2]}}
    )
    self.assertEqual(activity.platforms_to_build(), {macos1, macos2})
    self.assertEqual(activity.should_run(), True)
    self.assertEqual(activity.task_env(), {})

    activity = activities.BuildAndPublishMacOS(
      {'version': future, 'buildInput': {'platforms': ['ubuntu']}}
    )
    self.assertEqual(activity.should_run(), False)
    self.assertEqual(activity.platforms_to_build(), set())

    activity = activities.BuildAndPublishMacOS(
      {'version': '4.29.0', 'buildInput': {'platforms': []}}
    )
    self.assertEqual(activity.platforms_to_build(), set())
    self.assertEqual(activity.should_run(), False)

    activity = activities.BuildAndPublishMacOS(
      {'version': '4.29.0', 'buildInput': {'platforms': [macos1]}}
    )
    self.assertEqual(activity.platforms_to_build(), set())
    self.assertEqual(activity.should_run(), False)


if __name__ == '__main__':
  unittest.main()
