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

DOCKER_TAG="hhvm-trusty-pkg/$HHVM_VERSION"

if docker images | grep -q "$DOCKER_TAG"; then
  docker rmi -f "$DOCKER_TAG"
fi

docker build \
  --build-arg "HHVM_VERSION=$HHVM_VERSION" \
  -t "$DOCKER_TAG" \
  -f $DOCKERFILE \
  $(pwd)

rm -rf output/ubuntu-14.04-trusty/
mkdir -p output/ubuntu-14.04-trusty/{hhvm,hhvm-dev}

docker run \
  -v $(pwd)/output/ubuntu-14.04-trusty:/var/hhvm-packages \
  $DOCKER_TAG \
  hhvm/deb/package \
  ubuntu \
  trusty \
  "${HHVM_VERSION}-1" \
  "/source/scratch/dir" \
  /var/hhvm-packages/hhvm \
  /var/hhvm-packages/hhvm-dev

ls -l output/ubuntu-14.04-trusty/
