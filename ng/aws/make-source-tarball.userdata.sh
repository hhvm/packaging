#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.

set -ex

export TZ=UTC
export VERSION=${VERSION:-"$(date +%Y.%m.%d)"}

apt-get update -y
apt-get install -y curl wget git awscli
git clone https://github.com/hhvm/packaging hhvm-packaging
cd hhvm-packaging/ng
bin/make-source-tarball
aws s3 cp out/*.tar.gz s3://hhvm-downloads/source/nightlies/
