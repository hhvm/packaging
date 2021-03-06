#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

DIR=/home/ubuntu/.ondemand
source $DIR/common.inc.sh

if ! pgrep -f status-server.py >/dev/null
then
  nohup python3 $DIR/status-server.py $STATUS_FILE </dev/null >~/.status-server.log 2>&1 &
fi
