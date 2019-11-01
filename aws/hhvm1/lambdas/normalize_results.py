# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from common import normalize_results

def lambda_handler(event, context=None):
  return normalize_results(event.get('results', {}))
