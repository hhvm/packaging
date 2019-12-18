# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

source $DIR/config.inc.sh

STATUS_FILE=$DIR/status.txt

log() {
  echo STATUS: "$1"
  echo -n "$1" >> $STATUS_FILE
}

ok() {
  echo " [DONE]" >> $STATUS_FILE
}

maybe_source() {
  if [ -e "$1" ]
  then
    source "$1"
  fi
}

# default config options, may be overriden by TEAM/REPO-specific config
CLONE_TO_HOME=true

maybe_source $DIR/$TEAM/config.inc.sh
maybe_source $DIR/$TEAM/$REPO/config.inc.sh
