#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

if [ -z "$VERSION" -o -z "$S3_BUCKET" -o -z "$S3_PATH" -o -z "$IS_NIGHTLY" ]; then
  echo "Must set VERSION, S3_BUCKET, S3_PATH, and IS_NIGHTLY"
  exit 1
fi

set -ex

export TZ=UTC
export VERSION
export IS_NIGHTLY
export IS_AWS=true

apt-get update -y
apt-get install -y curl wget git awscli

aws configure set default.region us-west-2

git clone https://github.com/hhvm/packaging hhvm-packaging
ln -s $(pwd)/hhvm-packaging /opt/hhvm-packaging

cd /opt/hhvm-packaging

bin/make-source-tarball

cd out

FILE=$(basename "$S3_PATH")
aws s3 cp "$FILE" "s3://${S3_BUCKET}/${S3_PATH}"

aws kms decrypt --ciphertext-blob "fileb:///opt/hhvm-packaging/aws/gpg-key.kms-ciphertext" --query Plaintext --output text | base64 --decode | gpg --import

gpg --sign --armor --detach --local-user 0xD386EB94 \
  -o "$FILE".sig "$FILE"
aws s3 cp "${FILE}.sig" "s3://${S3_BUCKET}/${S3_PATH}.sig"
