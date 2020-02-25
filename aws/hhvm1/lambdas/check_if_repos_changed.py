# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from common import fake_ec2, is_nightly, is_test_build, normalize_results, skip_ec2

def lambda_handler(event, context=None):
  if skip_ec2(event) or fake_ec2(event) or is_test_build(event):
    return False

  results = normalize_results(event.get('results', {}))

  for version, vr in results.get('ForEachVersion', {}).items():
    if (
      'success' in vr.get('PublishBinaryPackages', {}) or
      'success' in vr.get('PublishSourceTarball', {}) or
      'success' in vr.get('BuildAndPublishMacOS', {}) or
      # nightlies are published directly from MakeSourceTarball
      is_nightly(version) and 'success' in vr.get('MakeSourceTarball', {})
    ):
      return True

  return False
