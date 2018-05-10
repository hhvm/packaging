#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

shutdown -h 30 # auto-shutdown after 30 minutes

if [ -z "$VERSION" ]; then
  echo "Must set VERSION"
  exit 1
fi

set -ex
export VERSION

apt-get update -y
apt-get install -y curl wget git awscli

aws configure set default.region us-west-2

git clone https://github.com/hhvm/packaging hhvm-packaging
ln -s $(pwd)/hhvm-packaging /opt/hhvm-packaging

/opt/hhvm-packaging/aws/bin/publish-release-source

shutdown -h now
