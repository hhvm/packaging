#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

pkill -f "run-test-workers.sh"
pkill -f "aws stepfunctions get-activity-task"
