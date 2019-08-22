'use strict';
const AWS = require('aws-sdk');
const rp = require('request-promise');

function get_distros_uri(event) {
  return 'https://raw.githubusercontent.com/hhvm/packaging/'
    + event.packagingBranch + '/CURRENT_TARGETS';
}

function get_userdata_uri(event) {
  return 'https://raw.githubusercontent.com/hhvm/packaging/'
    + event.packagingBranch + '/aws/userdata/make-binary-package.sh';
}

async function make_binary_package(distro, event, user_data) {
  if (distro === undefined) {
    throw "distro must be specified";
  }

  user_data =
    "#!/bin/bash\n"+
    "DISTRO="+distro+"\n"+
    "VERSION="+event.version+"\n"+
    "IS_NIGHTLY="+(event.nightly ? 'true' : 'false')+"\n"+
    "S3_SOURCE=s3://"+event.source.bucket+'/'+event.source.path+"\n"+
    "PACKAGING_BRANCH="+event.packagingBranch+"\n"+
    user_data;

  const params = {
    ImageId: /* ubuntu 16.04 */ 'ami-6e1a0117',
    MaxCount: 1,
    MinCount: 1,
    InstanceType: /* 8 cores, 32GB RAM */ 'm5.2xlarge',
    SecurityGroups: [ 'hhvm-binary-package-builders' ],
    IamInstanceProfile: { Arn: 'arn:aws:iam::223121549624:instance-profile/hhvm-binary-package-builder' },
    KeyName: "hhvm-package-builders",
    TagSpecifications: [
      {
        ResourceType: 'instance',
        Tags: [{
          Key: 'Name',
          Value: 'hhvm-build-'+event.version+'-'+distro
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

  let tries = 0;
  let interval_s = (Math.random() * 4) + 1; // float 1.0-5.0
  const ec2 = new AWS.EC2();
  while (tries < 5) {
    try {
      return await ec2.runInstances(params).promise();
    } catch (_err) {
      tries++;
      await new Promise(resolve => setTimeout(resolve, interval_s * 1000));
      interval_s *= 2;
    }
  }
  await new Promise(resolve => setTimeout(resolve, interval_s * 1000));
  return await ec2.runInstances(params).promise();
}

async function get_distros(event) {
  if (event.distros) {
    return event.distros;
  }
  const response = await rp(get_distros_uri(event));
  return response.trim().split("\n");
}

exports.handler = async (event) => {
  // Reduce chance of issues when there's many simultaneous builds
  const splay_ms = Math.random() * 60 * 1000;
  await new Promise(resolve => setTimeout(resolve, splay_ms));
  const [distros, user_data] = await Promise.all([
    get_distros(event),
    rp(get_userdata_uri(event))
  ]);
  event.distros = distros;
  const ec2_responses = await Promise.all(
    distros.map(distro => {
      return make_binary_package(distro, event, user_data);
    })
  );
  event.instances = ec2_responses.map(ec2_response => {
    return ec2_response.Instances[0].InstanceId;
  });
  return event;
};
