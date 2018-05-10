'use strict'
/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

const AWS = require('aws-sdk');

const CLOUDFRONT_DISTRIBUTION_ID = 'E35YBTV6QCR5BA';

exports.handler = (event, context, callback) => {
  // Don't invalidate pool/ : all filenames there are versioned.
  const targets = [
    '/debian/conf/*',
    '/debian/db/*',
    '/debian/dists/*',
    '/ubuntu/conf/*',
    '/ubuntu/db/*',
    '/ubuntu/dists/*',
  ];

  const version = event.version ? event.version : 'no_version';

  const cf = new AWS.CloudFront();
  cf.createInvalidation(
    {
      DistributionId: CLOUDFRONT_DISTRIBUTION_ID,
      InvalidationBatch: {
        CallerReference: 'hhvm-repository-update-'+version+'-'+(new Date()).toISOString(),
        Paths: {
          Quantity: targets.length,
          Items: targets
        }
      }
    },
    (err, data) => {
      if (err) {
        callback(err, data);
      } else {
        event.cloudfrontResponse = data;
        callback(null, event);
      }
    }
  );
}
