'use strict';
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');

const USERDATA_URI = 'https://raw.githubusercontent.com/hhvm/packaging/master/aws/userdata/update-repos.sh';

exports.handler = (event, context, callback) => {
  rp(USERDATA_URI)
  .then(userdata => {
    let userdata_prefix =
      "#!/bin/bash\n"+
      "PACKAGING_BRANCH="+event.packagingBranch+"\n";
    if (event.version) {
      userdata_prefix += "VERSION="+event.version+"\n";
    }
    userdata = userdata_prefix + userdata;

    const params = {
      ImageId: /* ubuntu 16.04 */ 'ami-6e1a0117',
      Placement: {
        // This is required as we have a persistent EBS volume containing
        // the repositories, and the instance must be in the same
        // availability zone as an EBS volume to attach it.
        AvailabilityZone: 'us-west-2a'
      },
      MaxCount: 1,
      MinCount: 1,
      InstanceType: 't2.micro',
      SecurityGroups: [ 'hhvm-binary-package-builders' ],
      InstanceInitiatedShutdownBehavior: 'terminate',
      IamInstanceProfile: { Arn: 'arn:aws:iam::223121549624:instance-profile/hhvm-repo-builders' },
      KeyName: "hhvm-package-builders",
      TagSpecifications: [
        {
          ResourceType: 'instance',
          Tags: [{
            Key: 'Name',
            Value: 'hhvm-update-repos',
          }]
        }
      ],
      BlockDeviceMappings: [{
        DeviceName: '/dev/sda1',
        Ebs: {
          DeleteOnTermination: true,
          VolumeSize: 100 /*gb*/,
          VolumeType: 'gp2'
        }
      }],
      UserData: (new Buffer(userdata)).toString('base64')
    };

    const ec2 = new AWS.EC2();
    return ec2.runInstances(params).promise();
  })
  .then(ec2_response => {
    event.instances = ec2_response.Instances.map(
      instance => instance.InstanceId
    );
    callback(null, event);
  })
  .done();
}
