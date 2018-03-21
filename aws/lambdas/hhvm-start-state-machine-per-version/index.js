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
  const sm_arn = event.stateMachineARN;
  if (sm_arn === undefined) {
    callback('stateMachineARN must be defined', event);
    return;
  }
  const versions = event.versions;
  if (versions === undefined) {
    callback('versions must be defined', event);
  }

  promise.all(
    versions.map(version => {
      return start_execution(sm_arn, version);
    })
  ).then(values => {
    event.stepFunctionExecutions = values.map(value => value.executionArn);
    callback(null, event);
  }).done();
};
