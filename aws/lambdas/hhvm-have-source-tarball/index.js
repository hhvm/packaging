'use strict'
/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */
const AWS = require('aws-sdk');
 
exports.handler = (event, context, callback) => {
  const source = event.source;
  if (!(source && source.bucket && source.path)) {
    callback("Input does not include source information");
    return;
  }

  const params = {
    Bucket: source.bucket,
    Key: source.path
  };
  const s3 = new AWS.S3();
  s3.headObject(params, function(err, data) {
    if (err) {
      callback(err, data);
    }
    callback(null, event);
  });
}
