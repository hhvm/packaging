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
exports.handler = (event, context, callback) => {
    const ec2 = new AWS.EC2();
    ec2.describeInstanceStatus(
        { InstanceIds: event.instances, IncludeAllInstances: true },
        function(err, data) {
            if (err) {
                callback(err, data);
            }
            event.instanceStates = {};
            event.allInstancesFinished = true;
            data.InstanceStatuses.forEach(function(s) {
                const state = s.InstanceState.Name;
                event.instanceStates[s.InstanceId] = state;
                if (state === "pending" || state === "running") {
                    event.allInstancesFinished = false;
                }
            });
            callback(null, event);
        }
    );
};
