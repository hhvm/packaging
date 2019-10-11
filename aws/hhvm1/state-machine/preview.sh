#!/bin/bash
$(dirname $0)/generate.hack | jq -C . | less -R
