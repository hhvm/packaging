# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

cd /home/ubuntu/$REPO

log "Installing Hack (Composer) dependencies..."
composer install
ok

log "Configuring hh_server..."
hh_client || true  # we don't care about errors, just make sure it's running

echo ".vscode" >> /home/ubuntu/.gitignore_global
mkdir -p .vscode
if [ ! -e .vscode/settings.json ]; then
  echo "{}" > .vscode/settings.json
fi
SETTINGS_JSON=$(
  cat .vscode/settings.json |
  jq '."files.associations"."*.php" = "hack" | ."remote.SSH.defaultExtensions" += ["pranayagarwal.vscode-hack"]'
)
echo "$SETTINGS_JSON" > .vscode/settings.json
ok
