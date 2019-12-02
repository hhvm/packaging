#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

export TZ=UTC

if [ \
  -z "$DISTRO" \
  -o -z "$VERSION" \
  -o -z "$S3_SOURCE" \
  -o -z "$IS_NIGHTLY" \
]; then
  echo "DISTRO, VERSION, S3_SOURCE, and IS_NIGHTLY must all be set"
  exit 1
fi

SOURCE_BASENAME="$(basename "$S3_SOURCE")"

export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get clean
apt-get install -y docker.io curl wget git awscli

git clone https://github.com/hhvm/packaging hhvm-packaging
cd hhvm-packaging
git checkout "$PACKAGING_BRANCH"

aws s3 cp "$S3_SOURCE" out/

export VERSION
export IS_NIGHTLY

aws s3 sync "s3://hhvm-nodist/${DISTRO}/" nodist/
if ! bin/make-package-in-throwaway-container "$DISTRO"; then
  IMAGE_NAME=hhvm-failed-builds
  # On modern systems, this should just be:
  #   $(aws ecr get-login --no-include-email --region us-west-2)
  # This is slightly different to support the older versions of the AWS and
  # docker CLIs in our base image (currently Ubuntu 16.04)
  $(aws ecr get-login --region us-west-2 | sed 's/ -e none / /')

  CONTAINER_ID="$(docker ps -aq)"
  EC2_INSTANCE_ID="$(curl --silent http://169.254.169.254/latest/meta-data/instance-id)"

  # Create a Docker image from the container (instance)
  DOCKER_REPOSITORY="223121549624.dkr.ecr.us-west-2.amazonaws.com"
  IMAGE_NAME="${DOCKER_REPOSITORY}/${IMAGE_NAME}:${VERSION}_${DISTRO}_${EC2_INSTANCE_ID}"
  docker commit "${CONTAINER_ID}" "${IMAGE_NAME}"
  # Push to ECR so we can download later
  docker push "${IMAGE_NAME}"
  exit 1
fi

rm "out/${SOURCE_BASENAME}"

aws s3 cp --include '*' --recursive out/ s3://hhvm-scratch/${VERSION}/${DISTRO}/
aws s3 sync nodist/ "s3://hhvm-nodist/${DISTRO}/"
