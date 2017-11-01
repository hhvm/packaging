'use strict'
const AWS = require('aws-sdk');
 
exports.handler = (event, context, callback) => {
  const version = event.version;
  if (!version) {
    callback('Version is required');
  }

  const nightly = /^\d{4}(\.\d{2}){2}$/.exec(version);
  const path = nightly
    ? 'source/nightlies/hhvm-nightly-'+version+'.tar.gz'
    : 'source/hhvm-'+version+'.tar.gz';

  const params = {
    Bucket: 'hhvm-downloads',
    Key: path
  };
  const s3 = new AWS.S3();
  s3.headObject(params, function(err, data) {
    if (err) {
      callback(err, params);
    }
    callback(null, {version: version, params: params});
  });
}
