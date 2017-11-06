#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

set -ex

shutdown -h 120 # 2 hour timeout

apt-get update -y
apt-get install -y docker.io awscli
git clone https://github.com/hhvm/packaging hhvm-packaging
ln -s $(pwd)/hhvm-packaging/ng /opt/hhvm-packaging
git clone https://github.com/hhvm/hhvm-docker /opt/hhvm-docker

aws configure set default.region us-west-2

docker login -u hhvmawsbot -p "$(aws kms decrypt --ciphertext-blob 'fileb:///opt/hhvm-packaging/aws/docker-pass.kms-ciphertext' --query Plaintext --output text | base64 --decode)"

/opt/hhvm-docker/build-and-tag.sh

shutdown -h now
