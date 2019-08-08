# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

source /etc/lsb-release

HHVM_VERSION=$(grep -oP '"hhvm": "\K[0-9]+\.[0-9]+' /home/ubuntu/$REPO/composer.json || echo "")

if [ "$HHVM_VERSION" ]
then
  HHVM_REPO=$DISTRIB_CODENAME-$HHVM_VERSION
else
  HHVM_REPO=$DISTRIB_CODENAME
fi

echo deb https://dl.hhvm.com/ubuntu $HHVM_REPO main > /etc/apt/sources.list.d/hhvm.list
apt-key adv --recv-keys --keyserver hkp://keyserver.ubuntu.com:80 0xB4112585D386EB94

PACKAGES="hhvm php-cli unzip"
