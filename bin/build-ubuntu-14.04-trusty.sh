#!/bin/bash
set -e

HHVM_VERSION="$1"

if [ -z "$1" ]; then
  echo "Usage: $0 hhvm-version"
  exit 1
fi

if [ -e "./$(basename $0)" ]; then
  cd ..
fi

DOCKERFILE=$(pwd)/dockerfiles/ubuntu-14.04-trusty

if [ ! -e $DOCKERFILE ]; then
  echo "Run from root of hhvm-packaging repo"
  exit 1
fi

DOCKER_TAG="hhvm-trusty-pkg/$(md5sum "$DOCKERFILE" | awk '{print $1}')"

if ! docker images | grep -q "$DOCKER_TAG"; then
  docker build \
    -t "$DOCKER_TAG" \
    -f $DOCKERFILE \
    $(pwd)
fi

rm -rf output/ubuntu-14.04-trusty/
mkdir -p output/ubuntu-14.04-trusty/{hhvm,hhvm-dev}

docker run \
  -v $(pwd)/output/ubuntu-14.04-trusty:/var/hhvm-packages \
  -v $(pwd)/hhvm:/var/hhvm \
  $DOCKER_TAG \
  /var/hhvm/deb/package \
  ubuntu \
  trusty \
  "${HHVM_VERSION}-1" \
  "/bogus-source-dir/dir" \
  /var/hhvm-packages/hhvm \
  "/bogus-build-dir/dir" \
  /var/hhvm-packages/hhvm-dev

ls -lR output/ubuntu-14.04-trusty/
