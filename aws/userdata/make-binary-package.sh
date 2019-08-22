#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex
shutdown -h 180 # auto-shutdown after 3 hours

export TZ=UTC

if [ \
  -z "$DISTRO" \
  -o -z "$VERSION" \
  -o -z "$S3_SOURCE" \
  -o -z "$IS_NIGHTLY" \
]; then
  echo "DISTRO, VERSION, S3_SOURCE, and IS_NIGHTLY must all be set"
  exit 1
fi

CLOUDWATCH_CONFIG_FILE="$(mktemp)"
cat > "${CLOUDWATCH_CONFIG_FILE}" <<EOF
[general]
state_file = /var/awslogs/state/agent-state  

[/var/log/cloud-init-output.log]
file = /var/log/cloud-init-output.log
log_group_name = hhvm-binary-package-builds/cloud-init-output.log
log_stream_name = $(date "+%Y/%m/%d")/hhvm-${VERSION}_${DISTRO}_{instance_id}
EOF
curl -O https://s3.amazonaws.com//aws-cloudwatch/downloads/latest/awslogs-agent-setup.py
python3 awslogs-agent-setup.py -n -r us-west-2 -c "${CLOUDWATCH_CONFIG_FILE}"


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

aws s3 sync "s3://hhvm-nodist/${DISTRO}/" nodist/
bin/make-package-in-throwaway-container "$DISTRO"

rm "out/${SOURCE_BASENAME}"

aws s3 cp --include '*' --recursive out/ s3://hhvm-scratch/${VERSION}/${DISTRO}/
aws s3 sync nodist/ "s3://hhvm-nodist/${DISTRO}/"

shutdown -h now
