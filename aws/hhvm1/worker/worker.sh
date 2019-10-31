#!/bin/bash
#
# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

set -x

echo "alias t='tail -n 100 -f /var/log/cloud-init-output.log'" \
  >> /home/ubuntu/.bashrc

# Shut down if we don't reach the main loop in 10 minutes.
shutdown -h +10

fail() {
  cleanup
  shutdown -h +1
  exit 1
}

if [ -z "$ACTIVITY_ARN" -o -z "$SCRIPT_URL" ]; then
  echo "Must set ACTIVITY_ARN and SCRIPT_URL"
  fail
fi

# This script needs to be as robust as possible, so we retry just about
# everything important that could reasonably fail.
try_really_hard() {
  for I in $(seq 5); do
    "$@" && return 0
    sleep 10
  done
  fail
}

# Using snap because apt-get's version of aws-cli is too old.
try_really_hard snap install jq
try_really_hard snap install aws-cli --classic

export PATH="$PATH:/snap/bin"

aws configure set default.region us-west-2
EC2_INSTANCE_ID=$(curl http://169.254.169.254/latest/meta-data/instance-id)

if [ -z "$SKIP_CLOUDWATCH" ]; then
  CLOUDWATCH_CONFIG_FILE="$(mktemp)"
  cat > "${CLOUDWATCH_CONFIG_FILE}" <<EOF
[general]
state_file = /var/awslogs/state/agent-state

[/var/log/cloud-init-output.log]
file = /var/log/cloud-init-output.log
log_group_name = hhvm-binary-package-builds/cloud-init-output.log
log_stream_name = $(date "+%Y/%m/%d")/w_$EC2_INSTANCE_ID
EOF
  curl --retry 5 -O \
    https://s3.amazonaws.com//aws-cloudwatch/downloads/latest/awslogs-agent-setup.py
  python3 awslogs-agent-setup.py -n -r us-west-2 -c "${CLOUDWATCH_CONFIG_FILE}"
fi

curl --retry 5 "$SCRIPT_URL" > process-task.sh || fail

if [ -n "$INIT_URL" ]; then
  curl --retry 5 "$INIT_URL" > init.sh || fail
  source init.sh
fi

PROCESSED_COUNT=0

# Each poll is ~1 minute, so this is the approximate number of minutes we'll
# wait for the next task before shutting down.
MAX_POLLS=10

# Cancel the hardcoded shutdown (the main loop below has more nuanced shutdown
# logic of its own).
shutdown -c

while true; do
  for I in $(seq $MAX_POLLS); do
    echo "Waiting for the next task ($I/$MAX_POLLS)..."

    TASK_JSON=$(
      aws stepfunctions get-activity-task \
        --activity-arn "$ACTIVITY_ARN" \
        --worker-name "ec2_$EC2_INSTANCE_ID" \
        --cli-read-timeout 70 \
        --output json
    )
    TASK_TOKEN=$(echo "$TASK_JSON" | jq -r '.taskToken // ""')

    if [ -n "$TASK_TOKEN" ]; then
      SECONDS=0  # magic bash variable
      PROCESSED_COUNT=$((PROCESSED_COUNT + 1))

      # We got a task, run it!
      INPUT_JSON=$(echo "$TASK_JSON" | jq -r '.input // {}')
      TASK_NAME=$(echo "$INPUT_JSON" | jq -r '.name // ""')
      TASK_ENV=$(echo "$INPUT_JSON" | jq -r '.env // ""')

      # Update EC2 instance name to reflect the name of the current task (for
      # nicer view in the AWS console).
      if [ -n "$EC2_INSTANCE_ID" -a -n "$TASK_NAME" ]; then
        aws ec2 create-tags --resources "$EC2_INSTANCE_ID" \
          --tags "Key=Name,Value=wa-$PROCESSED_COUNT-$TASK_NAME"
      fi

      # Heartbeats are not used right now but could be useful at some point.
      # echo "*/5 * * * * aws stepfunctions send-task-heartbeat '$TASK_TOKEN'" \
      #   | crontab -

      WRAPPER_SCRIPT="./task_${TASK_NAME}_$(date +%Y-%m-%d_%H-%M-%S).sh"
      echo "#!/bin/bash
        shutdown() {
          echo skipping shutdown \$@
        }
        SKIP_CLOUDWATCH=1
        $TASK_ENV
        source process-task.sh" > $WRAPPER_SCRIPT
      chmod a+x $WRAPPER_SCRIPT

      if $WRAPPER_SCRIPT; then
        try_really_hard aws stepfunctions send-task-success \
          --task-token "$TASK_TOKEN" \
          --task-output "{\"ec2\":\"$EC2_INSTANCE_ID\",\"time_sec\":\"$SECONDS\"}"
      else
        try_really_hard aws stepfunctions send-task-failure \
          --task-token "$TASK_TOKEN" \
          --cause "{\"ec2\":\"$EC2_INSTANCE_ID\",\"time_sec\":\"$SECONDS\"}"
        # We don't know if the problem was with the task or with this worker,
        # so it's safer not to reuse the worker. Shut down and let any retries
        # be picked by different workers.
        fail
      fi

      if [ -n "$EC2_INSTANCE_ID" -a -n "$TASK_NAME" ]; then
        aws ec2 create-tags --resources "$EC2_INSTANCE_ID" \
          --tags "Key=Name,Value=ww-$PROCESSED_COUNT-$TASK_NAME"
      fi

      # Clean up anything that the task script may have created. TODO: Reusing
      # some of these may actually save time if we can do it safely.
      rm -rf hhvm* ~/hhvm* /hhvm* /opt/hhvm* /tmp/hhvm* ~/.gnupg /var/out

      # Go wait for the next task (outer while loop).
      continue 2
    fi

    # We didn't get a task, poll again or quit (after 10 seconds).
    sleep 10
  done

  # No task was received in $MAX_POLLS attempts.
  echo "No more tasks for me, good bye."
  cleanup  # init script may declare this
  shutdown -h +1
  exit 0
done
