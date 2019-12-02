#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

if [ -z "$PACKAGING_BRANCH" ]; then
  echo "PACKAGING_BRANCH must be set."
  exit 1
fi

if [ -z "$VERSION" ]; then
  echo "VERSION must be set."
  exit 1
fi

git clone https://github.com/hhvm/packaging hhvm-packaging
ln -s $(pwd)/hhvm-packaging /opt/hhvm-packaging
(cd hhvm-packaging; git checkout $PACKAGING_BRANCH)

export VERSION
export PACKAGING_BRANCH

if [ -z "$DOCKER_ONLY" ]; then
  /opt/hhvm-packaging/aws/bin/update-repos
fi

if [ -z "$REPOS_ONLY" ]; then
  /opt/hhvm-packaging/aws/bin/update-docker
fi
