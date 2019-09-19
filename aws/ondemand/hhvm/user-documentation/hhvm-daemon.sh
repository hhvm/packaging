#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

if ! pgrep -f "hhvm -m daemon" >/dev/null
then
  cd $1/public
  hhvm -m daemon -p 8080 -c ../hhvm.dev.ini -d hhvm.log.file=/home/ubuntu/hhvm.log
fi
