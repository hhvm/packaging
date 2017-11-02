'use strict'
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');

const USERDATA_URI = 'https://raw.githubusercontent.com/hhvm/packaging/master/ng/aws/userdata/make-source-tarball.sh';

function make_source_tarball(version, user_data, callback) {
  if (version === undefined) {
    version = 'nightly';
  } else {
    user_data = "#!/bin/bash\nVERSION="+version+"\n"+user_data;
  }

  const params = {
    ImageId: /* ubuntu 16.04 */ 'ami-6e1a0117',
    MaxCount: 1,
    MinCount: 1,
    InstanceType: 't2.micro',
    SecurityGroups: [ 'hhvm-binary-package-builders' ],
    InstanceInitiatedShutdownBehavior: 'terminate',
    IamInstanceProfile: { Arn: 'arn:aws:iam::223121549624:instance-profile/hhvm-binary-package-builder' },
    KeyName: "hhvm-package-builders",
    TagSpecifications: [
      {
        ResourceType: 'instance',
        Tags: [{
          Key: 'Name',
          Value: 'hhvm-build-source-tarball-'+version
        }]
      }
    ],
    UserData: (new Buffer(user_data)).toString('base64')
  };

  const ec2 = new AWS.EC2();
  ec2.runInstances(params, function(err, data) {
    if (err) {
      callback(err, 'failed to schedule instance');
    } else {
      callback(null, {version: version});
    }
  });
}
 
exports.handler = (event, context, callback) => {
  rp(USERDATA_URI)
  .then(function(response) {
    make_source_tarball(event.version, response, callback);
  })
  .done();
};
