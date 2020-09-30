# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# prevents "Too many open files" when running tests
echo "ulimit -n 1000000" >> /home/ubuntu/.bashrc

cd /home/ubuntu/$REPO

log "Building hhvm/user-documentation (this may take 2 to 3 minutes)..."
hhvm bin/build.php
ok

log "Starting web server (HHVM)..."
$DIR/$TEAM/$REPO/hhvm-daemon.sh /home/ubuntu/$REPO
ok
