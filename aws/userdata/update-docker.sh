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

if [ -z "$VERSION" ]; then
  echo "VERSION must be set."
  exit 1
fi

apt-get update -y
apt-get install -y awscli software-properties-common curl apt-transport-https ca-certificates

# We depend on being able to use build arguments in FROM, which requires a very recent Docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
add-apt-repository \
  "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"
apt-get update -y
apt-get install -y docker-ce

git clone https://github.com/hhvm/packaging hhvm-packaging
ln -s $(pwd)/hhvm-packaging /opt/hhvm-packaging
git clone https://github.com/hhvm/hhvm-docker /opt/hhvm-docker

aws configure set default.region us-west-2

aws kms decrypt \
  --ciphertext-blob 'fileb:///opt/hhvm-packaging/aws/docker-pass.kms-ciphertext' \
  --query Plaintext --output text \
  | base64 --decode \
  | docker login -u hhvmawsbot --password-stdin

/opt/hhvm-docker/build-and-tag.sh "$VERSION"

shutdown -h now
