# ONE STATE MACHINE TO RULE THEM ALL

This set of scripts, AWS lambda functions and a single AWS state machine are
designed to replace our existing build infrastructure.

The single state machine can do any combination of building, publishing and
other steps, either automatically (it will check and not do anything that's
already done) or manually (it accepts any combination of versions, distros and
step names as input).

See `bin/qaz` for usage instructions.


## Architecture overview

We use
[AWS activities](https://docs.aws.amazon.com/en_pv/step-functions/latest/dg/concepts-activities.html)
as the basic building block. The state machine publishes "tasks" associated with
each "activity" (a "task" is a single instance of an "activity"), which are
consumed by "workers". A worker is an EC2 instance specifically initialized to
process tasks for one of the activities.

The standard Amazon flow seems to assume that workers are constantly available,
which doesn't quite work for us (we don't want ~70 beefy EC2 instances running
constantly). We therefore start workers "on demand", by a state in the state
machine that directly preceeds the state that publishes each task.

However, the system is intentionally designed to **not** rely on this being 100%
accurate. Any worker can process any task belonging to the same activity, so
if some worker EC2 instance fails to initialize, or shuts down because of a
failure, or any other unpredictable thing happens, we don't care. Another worker
will pick up the task later.

To make sure we're never left with pending tasks for an activity with no
workers, there is a "health check" state in the state machine which runs every
5 minutes and starts new workers for any such activities.

In summary: If everything goes well, the state machine will initialize the
optimal number of workers to process all required tasks. But even if everything
doesn't go well, the machine can recover thanks to workers being interchangeable
(within each activity) and a periodic "health check".

### Retries

AWS state machines make it very convenient to specify retry policies for
everything. Generally we use:

- AWS lambda functions get 5 retries with 5, 10, 20, 40, 80 second delay; this
  is fairly aggressive but that's OK as these are cheap and can fail for random
  reasons (e.g. we get rate-limited when doing a lot of AWS API calls at once)
- activities get 2 retries with 1, then 5 minute delay; we're intentionally less
  aggressive here as these take a long time and can reasonably fail for
  legitimate reasons (e.g. compilation error)


## Monitoring

### CloudWatch logs

There is one CloudWatch log stream for each worker, named `w_{ec2_instance_id}`.
EC2 instance IDs are returned in the output for both successes and failures (see
below), which makes it easy to fetch the correct log stream.

If the same worker processes multiple tasks, searching for the task name (e.g.
"PublishBinaryPackage-4.28.2-ubuntu-18.04-bionic") in the log stream is an easy
way to find the relevant part of the log.

### EC2 instance names

Each "worker" EC2 instance updates its name whenever its state changes, so that
looking at the EC2 instance list in the AWS console gives a good overview of
what's currently going on.

- all names start with "w" for "worker"
- followed by "w" for "waiting" or "a" for "active"
- followed by the number of received tasks so far (0 for a fresh instance)
- followed by current (for active) or last processed (for waiting) task name
  (for fresh instances, name of the activity)
- in summary: "ww-X-..." indicates an idle worker after X successfully
  completed tasks (X may be 0); "wa-X-..." indicates an active worker that
  previously successfully completed X-1 tasks (note that a worker never picks up
  new tasks after a failure)
- pro-tip: for a terminated instance, "ww-..." indicates that it terminated out
  of boredom, while "wa-..." indicates it terminated due to a failure
- note: we don't retry the EC2 name change on failures as it's not a critical
  part of the flow, so this might not be 100% reliable (I've never seen it fail
  so far though)

### State machine output

- The AWS state machine doesn't return failures from individual states. All
  exceptions etc. are caught and stored in the JSON data. This is because any
  failing state would kill the whole state machine execution, including all
  other non-failing branches, which we don't want.
- The final step, `CheckForFailures`, iterates over the JSON data and returns
  a failure if any step failed during any part of the execution. The execution
  is therefore correctly shown as "succeeded" or "failed" in the AWS console,
  eventually.
- The returned failure message contains a list of every step that failed
  (including the failed version or distro if applicable). For each failure it
  lists the EC2 instance ID, which can be used to fetch the relevant logs (see
  above).
- The output of the state machine is a JSON that lists all steps, and for each
  it indicates whether it was skipped, succeeded or failed + any related
  information (EC2 instance ID for worker successes/failures; exception data for
  AWS lambdas that throw an exception).


## Making changes and testing

### Workers

Everything is in `worker.sh`, the full content of this file gets passed in to
any new "worker" EC2 instance as "userdata". These environment variable
assignments are prepended to the userdata:

- `ACTIVITY_ARN` -- identifier that will be passed to
  `aws stepfunctions get-activity-task` (ensures that each worker only receives
  tasks of one type, e.g. a worker for making binary packages shouldn't receive
  a task to publish a source file, etc.)
- `SCRIPT_URL` -- this script will be downloaded at the beginning and then
  executed for every received task; it may depend on any of the standard
  environment variables that are passed in with each task (`VERSION`, `S3_PATH`,
  `PACKAGING_BRANCH`, etc. -- see `env_for_version` in `lambdas/common.py`)
- `INIT_URL` (optional) -- will be downloaded and executed once, while the
  worker is being initialized, before receiving any tasks (useful to do any
  work that can be reused between tasks, e.g. mounting the shared EBS volume);
  the script may declare a `cleanup()` function which will be executed before
  shutting down (both on success and on failure)

Note that this setup implies that each worker only handles one type of tasks
(e.g. building binary packages, publishing source packages, building Docker
images, etc.), there are no generic workers. This makes things like `INIT_URL`
possible, but also allows different EC2 instance parameters for different tasks
(e.g. more CPUs and memory for building binary packages).

### Lambda functions

All the Python files get deployed to all the AWS lambda functions. This is OK
because each lambda is configured to run a different Python function. It also
makes it really easy to share code between the lambdas.

Code in `common.py` and `activities.py` is reused from multiple lambdas. Other
files contain code for a specific lambda.

After any changes:

- run `python3 test.py` to run some test cases (fairly rudimentary, don't rely
  on 100% test coverage here, and feel free to add more test cases -- it's
  probably easier than anything else you could do to manually test your changes,
  and will prevent regressions on top of that)
- run `deploy.sh` to deploy the Python code to all the AWS lambdas without
  having to click on things

### State machine

The state machine JSON is generated by `generate.hack`, instead of being written
manually. This makes it really easy to have consistent retry policies, reuse
some common patterns, etc. See comments in the Hack code for more details.

After any changes:

- run `preview.sh` to see the JSON output pretty-printed and with highlighted
  syntax
- run `deploy.sh` to update the AWS state machine without having to click on
  things

### End-to-end testing

These debug options can be passed to the state machine:

- `--fake-ec2` is the closest thing to an end-to-end test without actually
  building a release; it will do almost everything as in a normal run but pass
  `dummy-task.sh` as the `SCRIPT_URL` to each worker (this also skips all the
  `activity.should_run()` checks -- to test those, use
  `python3 test.py Test.test_should_run`)
- `--skip-ec2` is a cheaper/faster option but less end-to-end: it will not start
  any EC2 instances at all; you will need to process any triggered tasks
  manually, for which you can use `run-test-workers.sh` and
  `kill-test-workers.sh` (looking at the log files produced by these test
  workers can be very useful for debugging)
- the ability to specify specific activities to run is particularly useful for
  testing (e.g. you can run a real build, just not publish anything)
