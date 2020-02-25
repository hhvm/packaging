#!/usr/bin/env python3
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

import json
import sys
from lambdas.common import all_execution_events

if len(sys.argv) < 2:
  print('Usage: %s <execution-arn>' % sys.argv[0])
  quit(1)

events = {e['id']: e for e in all_execution_events(sys.argv[1])}

finished = {}
for finished_event in events.values():
  if finished_event['type'] == 'TaskStateExited':
    started_event = finished_event
    while started_event['type'] != 'TaskStateEntered':
      started_event = events[started_event['previousEventId']]
    finished[started_event['id']] = started_event, finished_event

unfinished = {
  id: e for id, e in events.items()
    if id not in finished and e['type'] == 'TaskStateEntered'
}

def output(s, f, prev):
  details = s['stateEnteredEventDetails']
  name = details['name']
  if name == 'HealthCheck' or name.startswith('PrepareTo'):
    return
  out = [name]
  input = json.loads(details['input'])
  if type(input) == dict:
    out.append(input.get('version'))
    out.append(input.get('platform'))
  if f:
    timedelta = f['timestamp'] - s['timestamp']
    out.append('(' + str(timedelta).rstrip('0') + ')')
  prefix = ''
  if prev:
    if prev['type'].endswith('Succeeded'):
      prefix = '\033[32m'
    elif prev['type'].endswith('Failed'):
      prefix = '\033[31mFAILED: '
  print('  ' + prefix + ' '.join(o for o in out if o) + '\033[0m')

if finished:
  print('Finished tasks:')
  for s, f in finished.values():
    output(s, f, events[f['previousEventId']])
  print()

if unfinished:
  print('Unfinished tasks:')
  for s in unfinished.values():
    output(s, None, None)
  print()
