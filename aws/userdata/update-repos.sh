#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

shutdown -h 180 # 3 hour timeout

if [ -z "$PACKAGING_BRANCH" ]; then
  echo "PACKAGING_BRANCH must be set."
  exit 1
fi

if [ -z "$VERSION" ]; then
  echo "VERSION must be set."
  exit 1
fi

if [ -z "$SKIP_CLOUDWATCH" ]; then
  CLOUDWATCH_CONFIG_FILE="$(mktemp)"
  cat > "${CLOUDWATCH_CONFIG_FILE}" <<EOF
[general]
state_file = /var/awslogs/state/agent-state

[/var/log/cloud-init-output.log]
file = /var/log/cloud-init-output.log
log_group_name = hhvm-binary-package-builds/cloud-init-output.log
log_stream_name = $(date "+%Y/%m/%d")/hhvm-${VERSION}_update-repos_{instance_id}
EOF
  curl -O https://s3.amazonaws.com//aws-cloudwatch/downloads/latest/awslogs-agent-setup.py
  python3 awslogs-agent-setup.py -n -r us-west-2 -c "${CLOUDWATCH_CONFIG_FILE}"
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

shutdown -h +1
