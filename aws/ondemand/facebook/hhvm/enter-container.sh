#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# This runs on each login to the EC2 instance, but can also be run manually.

retry() {
  "$@" 2>/dev/null && return 0
  sleep 1
  "$@" 2>/dev/null && return 0
  sleep 5
  "$@"
}

SRC_DIR=~/.ondemand
WORK_DIR=~/.od-hhvm
LOCK_FILE="$WORK_DIR/lock.pid"
DOCKER_CONFIG="$WORK_DIR/docker.conf"

mkdir -p "$WORK_DIR"

# Prevent race conditions and other bad states.
if ! (groups | grep docker >/dev/null); then
  echo "Current user is not in the 'docker' group."
  echo "Please verify if OnDemand initialization has finished successfully."
  echo "You'll need to log out and log back in after initialization is finished."
  exit 1
fi

LOCK_PID=$(cat "$LOCK_FILE" 2>/dev/null)
if [ -n "$LOCK_PID" ]; then
  if ps -p "$LOCK_PID" >/dev/null; then
    echo "A previous instance of \`enter-container\` is still running."
    echo "Please wait for it to finish or kill it."
    exit 1
  else
    # Previous instance didn't finish cleanly and possibly left things in a bad
    # state. Clean up and start from scratch.
    rm -f "$DOCKER_CONFIG" "$LOCK_FILE"
  fi
fi
echo $$ > $LOCK_FILE

# Select a Docker image to use.
echo "Looking up available Docker container images..."
echo
echo "If you don't want to open a Docker container, you can ^C at any point;"
echo "then run \`enter-container\` if you change your mind."
echo

aws configure set default.region us-west-2

if [ -e $DOCKER_CONFIG ]; then
  source $DOCKER_CONFIG
fi

if [ -z "$IMAGE" ]; then
  FAILED=($(
    retry aws ecr list-images --query "imageIds[*].imageTag" --output text \
      --repository-name hhvm-failed-builds
  ))
  SUCCESSFUL=($(
    retry aws ecr list-images --query "imageIds[*].imageTag" --output text \
      --repository-name hhvm-successful-builds
  ))
  echo "================================"
  echo "Choose a Docker container image."
  echo "--------------------------------"
  echo
  echo "Failed builds:"
  printf '  %s\n' "${FAILED[@]}" | grep -v :backup | sort -r
  echo
  echo "Successful builds:"
  printf '  %s\n' "${SUCCESSFUL[@]}" | grep -v :backup | sort -r
  echo
  echo "OnDemand backups:"
  printf '  %s\n' "${FAILED[@]}" | grep :backup | sort -r
  printf '  %s\n' "${SUCCESSFUL[@]}" | grep :backup | sort -r
  echo
fi

while [ -z "$IMAGE" ]; do
  REPO=""
  read -rp "Your choice: " CHOICE
  echo
  printf '%s\n' "${FAILED[@]}" | grep -Fx "$CHOICE" >/dev/null \
    && REPO=hhvm-failed-builds
  printf '%s\n' "${SUCCESSFUL[@]}" | grep -Fx "$CHOICE" >/dev/null \
    && REPO=hhvm-successful-builds
  if [ -n "$REPO" ]; then
    IMAGE="$REPO:$CHOICE" # setting IMAGE exits the loop
    CONTAINER=""
    rm -f $DOCKER_CONFIG 2>/dev/null
    echo "IMAGE=$IMAGE" > $DOCKER_CONFIG
  else
    echo "Invalid choice."
  fi
done

echo "Using Docker image: $IMAGE"
echo
echo "To choose a new image, exit any open containers and run:"
echo "  rm $DOCKER_CONFIG"
echo "  enter-container"
echo

VERSION=$(echo "$IMAGE" | grep -Po '(?<=:)[0-9]+\.[0-9]+\.[0-9]+(?=_)')
IMAGE="223121549624.dkr.ecr.us-west-2.amazonaws.com/$IMAGE"

# Fetch a new/existing Docker container ID.
if [ -z "$CONTAINER" ]; then
  $(retry aws ecr get-login --no-include-email) > $WORK_DIR/docker-login.log 2>&1

  echo -e "Creating Docker container from image:\e[2m" # dim text color
  docker pull "$IMAGE"
  CONTAINER="$(
    docker run -dt \
      -v "$SRC_DIR:/opt/ondemand:ro" \
      -v "/:/mnt/parent" \
      -v "/home/ubuntu:/home/ubuntu" \
      --security-opt "seccomp=$SRC_DIR/facebook/hhvm/seccomp.json" \
      "$IMAGE" /bin/bash -l
  )"
  echo -e '\e[22m' # reset text color

  if echo "$IMAGE" | grep backup > /dev/null; then
    # Backup images don't need the init script.
    echo "CONTAINER=$CONTAINER" >> $DOCKER_CONFIG
  else
    echo -e "Running initialization script inside the container:\e[2m"
    if docker exec -it \
        -e "SSH_AUTH_SOCK=/mnt/parent$SSH_AUTH_SOCK" \
        "$CONTAINER" \
        /opt/ondemand/facebook/hhvm/init-container.sh "$VERSION"; then
      # only persist the container ID if init-container.sh succeeds
      echo "CONTAINER=$CONTAINER" >> $DOCKER_CONFIG
    else
      CONTAINER=""
    fi
    echo -e '\e[22m'
  fi
fi

# We're out of the critical section (it is OK to have multiple terminals
# attached to the same container).
rm -f "$LOCK_FILE"

if [ -z "$CONTAINER" ]; then
  echo "Failed to create a Docker container."
  echo "Please try again later or choose a different Docker image."
  rm -f "$DOCKER_CONFIG"
  exit 1
fi

# Restart the container if it died somehow.
docker start "$CONTAINER" >/dev/null

docker exec -it \
  -e "SSH_AUTH_SOCK=/mnt/parent$SSH_AUTH_SOCK" \
  "$CONTAINER" /bin/bash -l
