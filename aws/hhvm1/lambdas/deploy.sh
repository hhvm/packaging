#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -e

cd "$(dirname $0)"

if ! ./test.py; then
  echo
  read -p "Tests failed. Deploy anyway? " -n 1 -r
  echo
  if ! [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Wise choice."
    exit 1
  fi
fi

ZIP="$(mktemp --dry-run --suffix=.zip)"
zip "$ZIP" $(ls *.py | grep -v test.py)

# Each AWS lambda is configured to run a different Python function, so we just
# deploy all Python files to each lambda, to make things simpler.

NAMES=(
  hhvm1-parse-input
  hhvm1-get-platforms-for-version
  hhvm1-prepare-activity
  hhvm1-check-for-failures
  hhvm1-check-if-repos-changed
  hhvm1-health-check
)

for NAME in "${NAMES[@]}"; do
  echo "Deploying $NAME..."
  aws lambda update-function-code \
    --function-name "$NAME" \
    --zip-file "fileb://$ZIP"
done

rm -f "$ZIP"
