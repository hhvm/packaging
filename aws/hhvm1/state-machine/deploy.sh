#!/bin/bash

set -e

ARN="arn:aws:states:us-west-2:223121549624:stateMachine:one-state-machine-to-rule-them-all"

DEFINITION="$($(dirname $0)/generate.hack)"

aws stepfunctions update-state-machine \
  --state-machine-arn "$ARN" \
  --definition "$DEFINITION"
