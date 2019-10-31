#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

# This is source'd (not executed) from worker.sh so we can declare this function
# here for worker.sh to use when it shuts down itself.
cleanup() {
  umount /mnt/dl.hhvm.com
}

INSTANCE_ID=$(curl --retry 5 http://169.254.169.254/latest/meta-data/instance-id)

# We keep a shared XFS volume as the source of truth to avoid having to
# redownload from S3 every day, which can take a *really* long time.
VOLUME_ID="vol-096d2c45d13d3a865"

# Note: We can use try_really_hard from worker.sh because this is source'd, not
# executed.
try_really_hard aws ec2 attach-volume \
  --device /dev/sdf \
  --instance-id "$INSTANCE_ID" \
  --volume-id "$VOLUME_ID"

sleep 10 # wait for EC2 to attach

mkdir -p /mnt/dl.hhvm.com
try_really_hard mount /dev/xvdf /mnt/dl.hhvm.com
