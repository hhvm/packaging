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
if [
  -z "$DISTRO"
  -o -z "$VERSION"
  -o -z "$S3_SOURCE"
  -o -z "$IS_NIGHTLY"
]; then
  echo "DISTRO, VERSION, S3_SOURCE, and IS_NIGHTLY must all be set"
  exit 1
fi
SOURCE_BASENAME="$(basename "$S3_SOURCE")"

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get clean
apt-get install -y docker.io curl wget git awscli

git clone https://github.com/hhvm/packaging hhvm-packaging
cd hhvm-packaging
git checkout "$PACKAGING_BRANCH"

aws s3 cp "$S3_SOURCE" out/

export VERSION
export IS_NIGHTLY

bin/make-package-in-throwaway-container "$DISTRO" > /var/log/hhvm-build

rm "out/${SOURCE_BASENAME}"

aws s3 cp --include '*' --recursive out/ s3://hhvm-scratch/pkg${REPO_SUFFIX}/${VERSION}/${DISTRO}/

shutdown -h now
