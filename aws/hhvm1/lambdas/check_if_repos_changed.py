# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from common import fake_ec2, skip_ec2

def lambda_handler(event, context=None):
  if skip_ec2(event) or fake_ec2(event):
    return False

  for version in event.get('results', {}).get('ForEachVersion', []):
    if 'success' in version.get('results', {}).get('PublishBinaryPackages', {}):
        return True

  return False
