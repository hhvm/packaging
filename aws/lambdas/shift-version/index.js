'use strict';
/**
 * Copyright (c) 2017-present, Facebook, Inc.
 * All rights reserved.
 *
 * This source code is licensed under the MIT license found in the
 * LICENSE file in the root directory of this source tree.
 */

exports.handler = (event, context, callback) => {
  if (event.versions.length === 0) {
    event.version = '';
  } else {
    event.version = event.versions[0];
    event.versions = event.versions.slice(1);
  }
  callback(null, event);
}
