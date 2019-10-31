#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -e

ARN="arn:aws:states:us-west-2:223121549624:stateMachine:one-state-machine-to-rule-them-all"

DEFINITION="$($(dirname $0)/generate.hack)"

aws stepfunctions update-state-machine \
  --state-machine-arn "$ARN" \
  --definition "$DEFINITION"
