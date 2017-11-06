'use strict';
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');

const USERDATA_URI = 'https://raw.githubusercontent.com/hhvm/packaging/master/ng/aws/userdata/update-repos.sh';

exports.handler = (event, context, callback) => {
  rp(USERDATA_URI)
  .then(userdata => {
    const params = {
      ImageId: /* ubuntu 16.04 */ 'ami-6e1a0117',
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
