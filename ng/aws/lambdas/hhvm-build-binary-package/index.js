'use strict'
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');

const USERDATA_URI = 'https://raw.githubusercontent.com/hhvm/packaging/master/ng/aws/userdata/make-binary-package.sh';

function make_binary_package(distro, version, user_data, callback) {
  if (distro === undefined) {
    throw "distro must be specified";
  }
  if (version === undefined) {
    version = 'nightly';
  } else {
    user_data = "VERSION="+version+"\n"+user_data;
  }
  user_data = "#!/bin/bash\nDISTRO="+distro+"\n"+user_data;

  const params = {
    ImageId: /* ubuntu 16.04 */ 'ami-6e1a0117',
    MaxCount: 1,
    MinCount: 1,
    InstanceType: /* 16 cores, 32GB RAM */ 'c4.4xlarge',
    SecurityGroups: [ 'hhvm-binary-package-builders' ],
    InstanceInitiatedShutdownBehavior: 'terminate',
    IamInstanceProfile: { Arn: 'arn:aws:iam::223121549624:instance-profile/hhvm-binary-package-builder' },
    KeyName: "hhvm-package-builders",
    TagSpecifications: [
      {
        ResourceType: 'instance',
        Tags: [{
          Key: 'Name',
          Value: 'hhvm-build-'+version+'-'+distro
        }]
      }
    ],
    BlockDeviceMappings: [{
      DeviceName: '/dev/sda1',
      Ebs: {
        DeleteOnTermination: true,
        VolumeSize: 50 /*gb*/,
        VolumeType: 'gp2'
      }
    }],
    UserData: (new Buffer(user_data)).toString('base64')
  };

  const ec2 = new AWS.EC2();
  ec2.runInstances(params, function(err, data) {
    if (err) {
    callback(err, 'failed to schedule instance');
    } else {
    callback(null, "data");
    }
  });
}
 
exports.handler = (event, context, callback) => {
  rp(USERDATA_URI)
  .then(function(response) {
    make_binary_package(event.distro, event.version, response, callback);
  })
  .done();
};
