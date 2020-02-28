#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

# This runs inside any newly created Docker containers.

set -e

VERSION="$1"
if [ -z "$VERSION" ]; then
  echo "Usage: $0 <HHVM version>"
  exit 1
fi

if [[ "$VERSION" =~ 20[0-9][0-9]\.[01][0-9]\.[0-3][0-9] ]]; then
  DIR_NAME="hhvm-nightly-$VERSION"
  TAG="nightly-$VERSION"
else
  DIR_NAME="hhvm-$VERSION"
  TAG="HHVM-$VERSION"
fi

DIRS=(/tmp/hhvmpkg.*/$DIR_NAME)
if [ ${#DIRS[@]} != 1 ] || [ ! -d "${DIRS[0]}" ]; then
  echo "Unable to find HHVM working directory (${DIRS[*]})."
  echo "Try a different Docker image."
  exit 1
fi
BUILD_DIR="${DIRS[0]}"

touch /root/.bashrc
cat >> /root/.bashrc <<ANALBUMCOVER
  PS1='\[\033[01;32m\]\u@\h\[\033[00m\]:\[\033[01;34m\]\W\[\033[00m\]# '
  alias push="git push -f --set-upstream origin \\\$(git name-rev --name-only HEAD)"
  export HHVM_DIR='$BUILD_DIR'
  cd \$HHVM_DIR
  echo
  echo -e "\e[92mYou are now inside the chosen Docker container.\e[39m Enjoy!"
  echo
  echo -e 'HHVM sources are in: \e[1m\$HHVM_DIR\e[0m ($BUILD_DIR)'
  echo -e 'Build output is in: \e[1m\$HHVM_DIR/obj-x86_64-linux-gnu\e[0m'
  echo 'Run \`make -j 8\` from the output directory after any changes.'
  echo
  echo -e "Host machine's home directory is mounted at: \e[1m/home/ubuntu\e[0m"
  echo "You can transfer files into/out of the container by copying them there."
  echo
ANALBUMCOVER

touch /root/.bash_logout
cat >> /root/.bash_logout <<ANALBUMCOVER
  echo
  echo -e "\e[91mYou are now leaving the Docker container.\e[39m"
  echo "Run \\\`enter-container\\\` when you want to return."
  echo
ANALBUMCOVER

cat >> /root/.vimrc <<ANALBUMCOVER
syntax on
set background=dark
set tabstop=2
set softtabstop=2
set expandtab
set backspace=indent,eol,start
set mouse=a
ANALBUMCOVER

cat > /root/.gitignore_global <<ANALBUMCOVER
debian
obj-x86_64-linux-gnu
third-party/boost/build
ANALBUMCOVER

set -x

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y git vim

mkdir -p /root/.ssh
touch /root/.ssh/known_hosts
ssh-keyscan github.com >> /root/.ssh/known_hosts

git config --global core.excludesfile /root/.gitignore_global

if [ ! -e "$BUILD_DIR/.git" ]; then
  TMP_DIR="$(mktemp -d)/hhvm"
  git clone git://github.com/facebook/hhvm.git "$TMP_DIR"
  pushd "$TMP_DIR"
  git fetch --all --tags
  # This may fail if running a test build with a fake version number, in which
  # case using master is probably fine (git status won't be clean though).
  git checkout "tags/$TAG" -b "ondemand_$(date +%Y-%m-%d_%H%M)" \
    || git checkout -b "ondemand_$(date +%Y-%m-%d_%H%M)"
  source /opt/ondemand/config.inc.sh
  git config user.name "$GIT_NAME"
  git config user.email "$GIT_EMAIL"
  git remote set-url origin "git@github.com:$GITHUB_USER/$REPO.git"
  mv .git "$BUILD_DIR/.git"
  rsync -a --ignore-existing hphp/test/ "$BUILD_DIR/hphp/test/"
  popd
  rm -rf "$TMP_DIR"
fi

ln -s "$BUILD_DIR/obj-x86_64-linux-gnu/hphp/hhvm/hhvm" "$BUILD_DIR/hphp/hhvm/hhvm" \
  || true
