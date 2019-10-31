#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

SEC=$((RANDOM % 30 + 10))

echo "Pretending to do work for $SEC seconds..."
sleep $SEC
