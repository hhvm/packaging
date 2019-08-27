#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

DIR=/home/ubuntu/.ondemand
source $DIR/common.inc.sh

# do this first so even if everything else fails, at least the user can log in and investigate
echo -e "$SSH_KEYS" >> /home/ubuntu/.ssh/authorized_keys

echo "Instance started." > $STATUS_FILE
chmod 666 $STATUS_FILE

log "Starting status monitoring server..."
sudo -i -u ubuntu $DIR/status-server.sh
ok

log "Initial system configuration..."
chmod a-x /etc/update-motd.d/*
mkdir -p /home/ubuntu/.cache
touch /home/ubuntu/.cache/motd.legal-displayed
touch /home/ubuntu/.sudo_as_admin_successful

cat $DIR/bashrc.inc.sh >> /home/ubuntu/.bashrc
cat >> /home/ubuntu/.bashrc <<ANALBUMCOVER
  cd $REPO 2>/dev/null
  $DIR/motd.sh
ANALBUMCOVER

update-alternatives --set editor /usr/bin/vim.basic

# required for remote IDE support
echo "fs.inotify.max_user_watches=524288" >> /etc/sysctl.conf
sysctl -p
ok

log "Cloning Git repository..."
sudo -i -u ubuntu git clone git://github.com/$TEAM/$REPO.git
ok

log "Installing required .deb packages..."
ALL_PACKAGES="lolcat"

maybe_source $DIR/$TEAM/packages.inc.sh
ALL_PACKAGES="$ALL_PACKAGES $PACKAGES"

maybe_source $DIR/$TEAM/$REPO/packages.inc.sh
ALL_PACKAGES="$ALL_PACKAGES $PACKAGES"

apt-get update
apt-get install -y $ALL_PACKAGES
ok

# team and repo-specific init code
maybe_source $DIR/$TEAM/root.inc.sh
maybe_source $DIR/$TEAM/$REPO/root.inc.sh

# the rest of the bootstrap code should not run as root
sudo -i -u ubuntu $DIR/user.sh

echo "[ALL DONE]" >> $STATUS_FILE
