#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

DIR=/home/ubuntu/.ondemand
source $DIR/common.inc.sh

log "Configuring Git checkout..."
touch /home/ubuntu/.ssh/known_hosts
ssh-keyscan github.com >> /home/ubuntu/.ssh/known_hosts

update-alternatives --config editor vim
git config --global user.name "$GIT_NAME"
git config --global user.email "$GIT_EMAIL"

cd /home/ubuntu/$REPO
git checkout -b ondemand_$(date +%Y-%m-%d_%H%M) master
git remote set-url origin git@github.com:$GITHUB_USER/$REPO.git
ok

# team and repo-specific init code
maybe_source $DIR/$TEAM/user.inc.sh
maybe_source $DIR/$TEAM/$REPO/user.inc.sh
