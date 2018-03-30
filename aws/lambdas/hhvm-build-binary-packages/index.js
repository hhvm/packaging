'use strict';
const AWS = require('aws-sdk');
const promise = require('promise');
const rp = require('request-promise');

function get_distros_uri(event) {
  return 'https://raw.githubusercontent.com/hhvm/packaging/'
    + event.packagingBranch + '/CURRENT_TARGETS';
}

function get_userdata_uri(event) {
  return 'https://raw.githubusercontent.com/hhvm/packaging/'
    + event.packagingBranch + '/aws/userdata/make-binary-package.sh';
}

function make_binary_package(distro, event, user_data) {
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
    InstanceType: /* 8 cores, 16GB RAM */ 'c4.2xlarge',
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

  const ec2 = new AWS.EC2();
  return ec2.runInstances(params).promise();
}

function get_distros(event) {
  return new promise((resolve, reject) => {
    if (event.distros) {
      resolve(event.distros);
      return;
    }

    rp(get_distros_uri(event)).then(response => {
      resolve(response.trim().split("\n"));
    });
  });
}

exports.handler = (event, context, callback) => {
  (new promise(
    // splay over 10 seconds for when doing multiple release builds at the same time
    resolve => setTimeout(resolve, Math.random() * 10000)
  ))
  .then(
    promise.all([
      get_distros(event),
      rp(get_userdata_uri(event))
    ])
  )
  .then(values => {
    const distros = values[0];
    const user_data = values[1];

    event.distros = distros;

    return promise.all(
      distros.map(distro => {
        return make_binary_package(distro, event, user_data);
      })
    );
  })
  .then(values => {
    event.instances = values.map(ec2_response => {
      return ec2_response.Instances[0].InstanceId;
    });
    callback(null, event);
  })
  .done();
};
