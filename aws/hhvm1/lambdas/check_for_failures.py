# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

def lambda_handler(event, context=None):
  failures = get_failures(event.get('results', {}))

  if failures:
    raise Exception('The following steps have failed:\n' + '\n'.join(failures))

  return event

def get_failures(results, context=[]):
  context_str = ' ({0})'.format(', '.join(context)) if context else ''
  failures = []

  for step_name, result in results.items():
    if type(result) == list:
      for item in result:
        failures += get_failures(
          item.get('results', {}),
          context + [item[k] for k in ['version', 'platform'] if k in item]
        )
    elif 'failure' in result:
      failures += [
        step_name + context_str + ' ' + result['failure'].get('Cause', '')
      ]

  return failures
