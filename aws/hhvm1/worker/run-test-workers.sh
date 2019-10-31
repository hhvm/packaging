#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

if [ -t 1 ]; then
  echo "Pro-tip: You can run: pushd \$($0); and then later: popd" 1>&2
fi

SRC_DIR="$(realpath $(dirname $0))"
TMP_DIR="$(mktemp -dt hhvm1-test-XXX)"
mkdir -p "$TMP_DIR/logs"

# override some commands that shouldn't run during local testing
snap() {
  echo skipping snap $@
}

shutdown() {
  echo skipping shutdown $@
}

ACTIVITIES=(
  "arn:aws:states:us-west-2:223121549624:activity:hhvm-make-source-tarball"
  "arn:aws:states:us-west-2:223121549624:activity:hhvm-make-binary-package"
  "arn:aws:states:us-west-2:223121549624:activity:hhvm-publish-binary-packages"
  "arn:aws:states:us-west-2:223121549624:activity:hhvm-publish-source-tarball"
  "arn:aws:states:us-west-2:223121549624:activity:hhvm-publish-docker-images"
)

for ARN in "${ACTIVITIES[@]}"; do
  (
    cd "$TMP_DIR"
    ACTIVITY_ARN="$ARN"
    SCRIPT_URL="file://$SRC_DIR/dummy-task.sh"
    INIT_URL=""
    SKIP_CLOUDWATCH=1
    source "$SRC_DIR/worker.sh"
  ) &> "$TMP_DIR/logs/${ARN##*:}.log" &
done

echo "$TMP_DIR/logs"
