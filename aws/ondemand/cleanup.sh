#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

FILE=/home/ubuntu/.touchme
if [ ! -f "$FILE" ]; then
  echo "Missing $FILE"
  exit 1
fi

Y=$(stat -c %Y "$FILE")
Z=$(stat -c %Z "$FILE")
LAST_ACCESS=$(( Y > Z ? Y : Z ))
NOW=$(date +%s)
SEC_SINCE=$(( NOW - LAST_ACCESS ))
if [ "$SEC_SINCE" -lt 259200 ]; then
  echo "Less than 3 days since last access, not cleaning up."
  exit
fi

source /home/ubuntu/.ondemand/config.inc.sh
BACKUP_NAME="${GITHUB_USER}_$(date +%Y-%m-%d_%H-%M-%S)"

# backup home directory
tar cz /home/ubuntu | aws s3 cp - "s3://ondemand-backup/$BACKUP_NAME.tar.gz"

# backup Docker container(s)
if which docker; then
  $(aws ecr get-login --no-include-email)
  for CONTAINER in $(docker ps -aq); do
    REPO=$(docker inspect --format='{{.Config.Image}}' "$CONTAINER" | cut -d : -f 1)
    IMAGE="${REPO}:backup_${BACKUP_NAME}_${CONTAINER}"
    docker stop "$CONTAINER"
    docker commit "$CONTAINER" "$IMAGE"
    docker push "$IMAGE"
    # there may not be enough disk space for multiple images
    docker rmi "$IMAGE"
  done
fi

# backup was successful, kill the instance
shutdown -h now
