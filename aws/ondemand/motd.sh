#!/bin/bash

# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

CAT=cat
if which lolcat >/dev/null 2>&1
then
  CAT=lolcat
fi

$CAT <<'ANALBUMCOVER'

                                        _
                                      (`  ).                   _
                                     (     ).              .:(`  )`. -a:f-
                                    _(       '`.          :(   .    )
                                .=(`(      .   )     .--  `.  (    ) )
                               ((    (..__.:'-'   .+(   )   ` _`  ) )
                               `(       ) )       (   .  )     (   )  ._
                                 ` __.:'   )     (   (   ))     `-'.-(`  )
                                        --'       `- __.'         :(      ))
                                                                  `(    )  ))
                       W e l c o m e   t o   T H E   C L O U D      ` __.:'


ANALBUMCOVER


STATUS_FILE=/home/ubuntu/.ondemand/status.txt
WARNING="\e[1m\e[31mWARNING:\e[0m "

if ! ssh-add -l >/dev/null 2>&1
then
  echo -en "$WARNING"
  echo No SSH keys available. Did you forget to run ssh with the -A flag?
  echo You will probably have trouble authenticating to GitHub.
  echo
  echo
fi


if ! grep "\\[ALL DONE\\]" $STATUS_FILE >/dev/null 2>&1
then
  echo -en "$WARNING"

  if grep "\\[FAILED\\]" $STATUS_FILE >/dev/null 2>&1
  then
    echo Initialization FAILED! You can investigate using:
  else
    echo Initialization has not finished. You can follow along using:
  fi

  echo
  echo "  cat ~/.ondemand/status.txt      # short summary"
  echo "  tail ~/.ondemand/bootstrap.log  # full init script output"
  echo
  echo
fi
