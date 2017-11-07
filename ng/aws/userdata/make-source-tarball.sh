#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

shutdown -h 30 # auto-shutdown after 30 minutes

if [ -z "$VERSION" -o -z "$S3_BUCKET" -o -z "$S3_PATH" -o -z "$IS_NIGHTLY" ]; then
  echo "Must set VERSION, S3_BUCKET, S3_PATH, and IS_NIGHTLY"
  exit 1
fi

set -ex

export TZ=UTC
export VERSION
export IS_NIGHTLY
export IS_AWS=true

apt-get update -y
apt-get install -y curl wget git awscli
git clone https://github.com/hhvm/packaging hhvm-packaging
cd hhvm-packaging/ng

bin/make-source-tarball

aws s3 cp out/*.tar.gz "s3://${S3_BUCKET}/${S3_PATH}"

shutdown -h now
