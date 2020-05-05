# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

alias hh=hh_client

# push current branch, creating it on GitHub if it doesn't exist yet
alias push="git push -f --set-upstream origin \$(git name-rev --name-only HEAD)"

# this file is touched whenever something happens that should prevent this
# instance from being killed (at the time of writing this, only touched on
# logins, but other actions may be added in the future)
touch /home/ubuntu/.touchme
