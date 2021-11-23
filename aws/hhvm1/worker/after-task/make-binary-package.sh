#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

if $SUCCESS; then
  IMAGE_NAME=hhvm-successful-builds
else
  IMAGE_NAME=hhvm-failed-builds
  aws s3 cp /var/log/cloud-init-output.log "s3://hhvm-scratch/build-failure-${VERSION}-${DISTRO}-${EC2_INSTANCE_ID}.cloud-init-output.log"
  aws s3 cp /var/log/kern.log "s3://hhvm-scratch/build-failure-${VERSION}-${DISTRO}-${EC2_INSTANCE_ID}.dmesg.log"
  rm "$DMESG"
fi

set -ex

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
docker rmi "${IMAGE_NAME}"
docker rm "${CONTAINER_ID}"
