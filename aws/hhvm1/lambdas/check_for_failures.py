# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from common import Config

def lambda_handler(event, context=None):
  failures = get_failures(event)

  if failures:
    raise Exception('The following steps have failed:\n' + '\n'.join(failures))

  return event

def get_failures(results, context=[]):
  failures = []

  for state_name, result in results.items():
    if state_name in Config.map_states:
      for key, inner_results in result.items():
        failures += get_failures(inner_results, context + [key])
    elif 'failure' in result:
      words = [state_name] + context + [result['failure'].get('Cause', '')]
      failures += [' '.join(words)]

  return failures
