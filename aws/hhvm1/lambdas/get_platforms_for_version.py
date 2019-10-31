# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from common import fetch

def lambda_handler(event, context=None):
  platforms = fetch('CURRENT_TARGETS', event['version']).strip().split('\n')

  if event['buildInput']['platforms']:
    platforms = [p for p in platforms if p in event['buildInput']['platforms']]

  return platforms
