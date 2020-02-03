#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -ex

# Import GitHub's public SSH key.
mkdir -p ~/.ssh
touch ~/.ssh/known_hosts
ssh-keyscan github.com >> ~/.ssh/known_hosts

# Decrypt and import private SSH key for pushing.
eval $(ssh-agent -s)

ENCRYPTED_KEY_PATH=$(mktemp)

curl --retry 5 \
  "https://raw.githubusercontent.com/hhvm/packaging/master/aws/homebrew-repo-push-key.kms-ciphertext" \
  > "$ENCRYPTED_KEY_PATH"

aws kms decrypt \
  --region us-west-2 \
  --ciphertext-blob "fileb://$ENCRYPTED_KEY_PATH" \
  --query Plaintext --output text \
  | base64 --decode \
  | ssh-add -

# Push a new commit to trigger the MacOS build.
git clone git@github.com:hhvm/homebrew-hhvm.git
cd homebrew-hhvm
git config user.name "HHVM Homebrew Bot (AWS)"
git config user.email opensource+hhvm-homebrew-bot@fb.com
git checkout build-triggers

# Clean up old build metadata files.
MONTH_BEFORE_LAST=$(date +%Y-%m --date '40 days ago')
find builds/ -name "${MONTH_BEFORE_LAST}-*.sh" | xargs git rm -f || true

# Then add the new metadata file(s).
for PLATFORM in "${PLATFORMS[@]}"; do
  TRIGGER_FILE="builds/$(date +%Y-%m-%d_%H-%M-%S)_$RANDOM.sh"

  echo "
    VERSION='$VERSION'
    PLATFORM='$PLATFORM'
    SKIP_IF_DONE=1
    TASK_TOKEN=$(printf %q "$TASK_TOKEN")
  " > "$TRIGGER_FILE"

  COMMIT_MESSAGE="[aws] build $VERSION"
  if [ -n "$PLATFORM" ]; then
    COMMIT_MESSAGE="$COMMIT_MESSAGE on $PLATFORM"
  fi

  git add "$TRIGGER_FILE"
  git commit -m "$COMMIT_MESSAGE"
done

git pull --rebase  # make race conditions less likely
git push

# Cleanup.
cd ..
rm -rf homebrew-hhvm
ssh-add -D
