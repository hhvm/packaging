'use strict'
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');

const USERDATA_URI = 'https://raw.githubusercontent.com/hhvm/packaging/master/aws/userdata/publish-release-source.sh';

function publish_release_source(event, user_data, callback) {
  if (!event.version) {
    callback("Need version and source on input");
    return;
  }

  user_data = "#!/bin/bash\n"+"VERSION="+event.version+"\n"+user_data;

  const params = {
    ImageId: /* ubuntu 16.04 */ 'ami-6e1a0117',
    MaxCount: 1,
    MinCount: 1,
    InstanceType: 't2.micro',
    SecurityGroups: [ 'hhvm-binary-package-builders' ],
    InstanceInitiatedShutdownBehavior: 'terminate',
    IamInstanceProfile: { Arn: 'arn:aws:iam::223121549624:instance-profile/hhvm-source-tarball-builder' },
    KeyName: "hhvm-package-builders",
    TagSpecifications: [
      {
        ResourceType: 'instance',
        Tags: [{
          Key: 'Name',
          Value: 'hhvm-'+event.version+'-publish-source'
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
      event.instances = data.Instances.map(instance => instance.InstanceId);
      callback(null, event);
    }
  });
}
 
exports.handler = (event, context, callback) => {
  if (event.nightly) {
    event.instances = [];
    event.comment = "Not published sources, nightly build";
    callback(null, event);
    return;
  }

  rp(USERDATA_URI)
  .then(function(response) {
    publish_release_source(event, response, callback);
  })
  .done();
};
