'use strict'
const AWS = require('aws-sdk');

exports.handler = (event, context, callback) => {
  const version = event.version;
  if (!version) {
    callback('Version is required');
  }

  const distros = [
    'debian-8-jessie',
    'ubuntu-16.04-xenial',
  ];

  const lambda = new AWS.Lambda();
  distros.forEach(function(distro) {
    const params = {
      FunctionName: "hhvm-build-binary-package",
      InvocationType: "Event",
      Payload: JSON.stringify({
        distro: distro,
        version: version
      })
    };
    lambda.invoke(params, function(err, data) {
      if (err) {
        callback(err, distro);
      }
    });
  });
}
