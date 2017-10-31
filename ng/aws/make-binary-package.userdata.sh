#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

set -ex
shutdown -h 180 # auto-shutdown after 3 hours

export TZ=UTC
export VERSION=${VERSION:-"$(date +%Y.%m.%d)"}
if [ -z "$DISTRO" ]; then
  echo "Environment variable 'DISTRO' must be set"
  exit 1
fi

apt-get update -y
apt-get install -y docker.io curl wget git awscli

git clone https://github.com/hhvm/packaging hhvm-packaging
cd hhvm-packaging/ng

aws s3 cp s3://hhvm-downloads/source/nightlies/hhvm-nightly-${VERSION}.tar.gz out/

bin/make-package-in-throwaway-container "$DISTRO"

rm out/hhvm-nightly-${VERSION}.tar.gz

aws s3 cp --include '*' --recursive ./ s3://hhvm-scratch/nightlies/

shutdown -h now
