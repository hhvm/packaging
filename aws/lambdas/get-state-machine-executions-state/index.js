'use strict'
/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

const AWS = require('aws-sdk');
const promise = require('promise');

exports.handler = (event, context, callback) => {
  const sf = new AWS.StepFunctions();

  event.stepFunctionExecutionStates = {};
  event.allStepFunctionExecutionsFinished = true;

  promise.all(
    event.stepFunctionExecutions.map(arn => {
      return sf.describeExecution({
        executionArn: arn
      }).promise();
    })
  ).then(results => {
    results.forEach(function(r) {
      const arn = r.executionArn;
      const state = r.status;

      event.stepFunctionExecutionStates[arn] = state;
      if (state === 'RUNNING') {
        event.allStepFunctionExecutionsFinished = false;
      }
    });
    callback(null, event);
  }).done();
};
