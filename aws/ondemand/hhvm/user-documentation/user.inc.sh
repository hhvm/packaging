# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

cd /home/ubuntu/$REPO

log "Building hhvm/user-documentation (this may take 2 to 3 minutes)..."
hhvm bin/build.php
ok

log "Starting web server (HHVM)..."
cd public
hhvm -m daemon -p 8080 -c ../hhvm.dev.ini -d hhvm.log.file=/home/ubuntu/hhvm.log
ok
