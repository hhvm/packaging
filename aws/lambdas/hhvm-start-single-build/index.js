'use strict'
/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the BSD-style license found in the
 * LICENSE file in the root directory of this source tree. An additional grant
 * of patent rights can be found in the PATENTS file in the same directory.
 */

const AWS = require('aws-sdk');
const promise = require('promise');
const crypto = require('crypto');

function start_execution(
  sm_arn,
  version
) {
  const sf = new AWS.StepFunctions();
  return sf.startExecution({
    stateMachineArn: sm_arn,
    input: JSON.stringify({version: version}),
    name: version+'-build-'+crypto.randomBytes(8).toString('hex'),
  }).promise();
}

exports.handler = (event, context, callback) => {
  const sm_arn = 'arn:aws:states:us-west-2:223121549624:stateMachine:hhvm-build';
  const version = event.version;
  if (version === undefined) {
    callback('version must be defined', event);
  }

  const sf = new AWS.StepFunctions();
  sf.startExecution({
    stateMachineArn: sm_arn,
    input: JSON.stringify({version: version}),
    name: version+'-build-'+crypto.randomBytes(8).toString('hex'),
  }, function(err, data) {
    if (err) {
      callback(err, null);
      return;
    }
    event.stepFunctionExecutions = [data.executionArn];
    callback(null, event);
  });
};
