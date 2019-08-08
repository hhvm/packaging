#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -x

DIR=/home/ubuntu/.ondemand

$DIR/main.sh 2>&1 | tee $DIR/bootstrap.log

if ! grep "\\[ALL DONE\\]" $DIR/status.txt
then
  echo " [FAILED]" >> $DIR/status.txt
fi
