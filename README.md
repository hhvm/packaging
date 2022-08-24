# HHVM Packaging

This repository contains the source code of the HHVM packaging
scripts.

HHVM is packaged by building insider Docker contains on AWS EC2. These
workers are triggered by AWS Step Functions.

## Usage

You will need Python and the [AWS
CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-welcome.html)
installed on your local machine.

You can then take a nightly build (e.g. the [most
recent](https://hhvm.com/api/build-status/nightly) or a [specific
older version](https://hhvm.com/api/build-status/2022.05.01)) and
promote it.

```
$ bin/promote-nightly-to-release 2019.07.22 4.15
```

See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for more details and
instructions on patch releases. If you encounter issues, see
[DEBUGGING.md](DEBUGGING.md).

### Testing HHVM Changes

If you've made local changes to HHVM and want to see how they affect
the build, we provide a helper script. Make sure you've run
`git submodule update --init --recursive` in the HHVM checkout first.

```
$ bin/test-build-on-all-distros <path to HHVM checkout>
```

Configuration
=============

Distribution subdirectories should be consistently named: `DISTRO-NUMERIC_VERSION[-VERSION_NAME]` - for example, `debian-9-stretch`, or `ubuntu-16.04-xenial`. There are two required files:
 - `make-package`: executable script that creates a package from `/var/out/hhvm-nightly-$VERSION.tar.gz`, and put the output in `/var/out`
 - `DOCKER_BASE`: plain text file containing the name of a public docker image that should be used for the build - for example, `debian:stretch`. It needs to be possible to pass this to `docker run`, for example, `docker run -it debian:stretch /bin/bash -l` should work.

Docker containers will have the following directories bind-mounted:

 - `/var/out`: read-write; build artifacts (e.g. packages) go here.
 - `/opt/hhvm-packaging`: read-only; this directory.
 - `/opt/hhvm-distro-packaging`: read-only; the subdirectory for your
   distribution. This should contain a `make-package` script or symlink

For example, when building for Debian Jessie, the `debian-8-jessie/`
subdirectory is mounted to /opt/hhvm-distro-packaging.

The package building process will execute
`/opt/hhvm-distro-packaging/make-package` in the container, and will
expect that to create packages in `/var/out`. `make-package` should install
all required build dependencies. Use the native package manager's support
for `build-depends` or similar where possible.

Debian-like distributions
-------------------------

You probably want `make-package` to be a symlink to `/opt/hhvm-packaging/bin/make-debianish-package`; this expects:

 - a `DISTRIBUTION` file containing the string name for the distribution - e.g. 'jessie', 'trusty'
 - a `PKGVER` file containing the *package* version - e.g. `1~jessie`
 - a `debian/` subdirectory, containing `control`, `rules`, etc.

If you are able to use an existing distribution's `debian/` directory directly, please make it a symlink to
`/opt/hhvm-packaging/OTHER_DISTRO_HERE/debian`.

Packages will be build with `debbuild`

Local interactive usage
=======================

1. [Install Docker](https://www.docker.com/get-docker)
2. run `bin/make-interactive-container`; you now have a shell in the container
3. within the container, install git (e.g. `apt-get update -y; apt-get install -y git`)
4. run `/opt/hhvm-packaging/bin/make-source-tarball`
5. run `/opt/hhvm-distro-packaging/make-package`

You can specify a distribution at step 2 - for example, `bin/interactive-container debian-9-stretch'

Building packages non-interactively
===================================

1. [Install Docker](https://www.docker.com/get-docker)
2. If you are on MacOS, `brew install gnu-tar`, and `export TAR=gtar`
3. `bin/make-source-tarball` (just once)
4. run `bin/make-package-in-throwaway-container DISTRO_ID` (for each distribution)

`DISTRO_ID` is the name of one of the distribution-specific subdirectories, e.g. `debian-9-stretch`.

AWS
===

As we want to execute docker commands, we run directly on EC2, not ECS. AWS
supports running commands on EC2 instance startup - EC2 calls this
'user data' - a file or script-as-text in 'user data' will be executed.

The scripts we use are in the `aws/` subdirectory, and expect to be ran on
Ubuntu 16.04 hosts.

Building source tarball and linux packages for new releases
-----------------------------------------------------------

 - tag the release on the `hhvm-staging` repo
 - `bin/build-on-aws VERSION`

If you just need to rebuild for one distribution, with no code changes:

 - edit `DISTRO/PKGVER` if needed (e.g. if a previous package was pushed for this HHVM version and distribution) and push to github
 - `bin/build-on-aws VERSION DISTRO`

Building source tarballs and linux packages for multiple new releases
-----------------------------------------------------------

The common case is fixing a bug in multiple releases - for example, the current
release and all active LTS releases - simultaneously.

 - tag all the releases on the `hhvm-staging` repo
 - `bin/build-on-aws VERSION1 [VERSION2 [...]]`

How it works
------------

There are 3 kinds of jobs used here:

- AWS lambdas: code that can be written in stateless javascript/python
- jobs that run on EC2 instances: any other code. For example, building HHVM, or updating apt repositories
- AWS step functions: these are state machines, which coordinate the previous steps

See [aws/hhvm1/README.md](aws/hhvm1/README.md) for more details.

Nightly builds are triggered by a CloudWatch scheduled event rule.

S3 Buckets
----------

- `hhvm-downloads`: public. This is `dl.hhvm.com`
- `hhvm-scratch`: private. build artifacts and release source tarballs before public

EC2 Jobs
--------

Each kind of EC2 job has distinct 'userdata'; this is a shell script that AWS will invoke when imaged. You can see these in `aws/userdata/`.
Some of them depend on environment variables being set - this is accomplished by using lambdas to spawn them, which prepend variable initialization
to the userdata script before passing it to the EC2 API.

Note: The `userdata` scripts are no longer run directly on EC2 startup, they are now passed as "tasks" to "workers".
See [aws/hhvm1/README.md](aws/hhvm1/README.md) for more details.

Currently these are:

1. `make-source-tarball.sh`: creates and signs source tarballs.
   - if this is a nightly build (version like `YYYY.MM.DD`), it will create the tarball from the `master` branch of `facebook/hhvm`, and immediately publish to the `hhvm-downloads` S3 bucket
   - if this is a release build (any other version format), it will create the tarball from the appropriate `HHVM-x.y.z` tag  of `hhvm/hhvm-staging`, and instead upload to the `hhvm-scratch` S3 bucket
1. `make-binary-package.sh`: create a distribution packages (e.g `.deb` for Debian or Ubuntu) for a specific distribution and distribution version - e.g. `Ubuntu 16.04` will be built on a separate instance to `Ubuntu 16.10`. Results are published to the `hhvm-scratch` bucket
1. `update-repos.sh`: update the apt repositories or similar: this moves the binaries from `hhvm-scratch` to `hhvm-downloads`
1. `publish-release-source.sh`:
   - for nightlies, this does nothing
   - for release builds, this copies the source to `s3://hhvm-downloads/source/`, and copies the branch and tag from `hhvm/hhvm-staging` to `facebook/hhvm`

Lambdas
-------

There's a lot of these; the best way to see how these fit together is to look at the step function defintions. They take JSON input, and produce JSON output.
As step functions work like a pipeline, the output usually contains all the input data, but with fields added or modified. If a field isn't relevant to the lambda,
the lambda should return it verbatim.

If you want to invoke them manually:

```
aws lambda invoke --function-name my-func-name --payload "$(pbpaste)" /dev/stdout
```

... assuming the JSON input is in your clipboard, and you're on mac. Otherwise, replace `"$(pbpaste)"` with the JSON payload.

But more likely you just want:

```
bin/build-on-aws StepName ...
```

which starts an AWS state machine that invokes the correct combination of lambdas to perform the specified build step(s).

Currently, these are:

- `hhvm-get-build-status`: this is the code behind https://hhvm.com/api/build-status/VERSION (also used from some scripts and other lambdas)
- `create-s3-index-html`: takes an S3 bucket ID, and automatically generates `index.html` files
- `hhvm-invalidate-repository-metadata-on-cloudfront`: optionally takes a version number, but it's unused except for a job ID. It purges all `apt` metadata from the CDN caches.
  This is usually a final step in the build process.
- see [aws/hhvm1/README.md](aws/hhvm1/README.md) for information about other lambdas
  (meant to be only triggered from the build state machine)

Resuming Failed Step Functions
------------------------------

`bin/build-on-aws` automatically checks which steps need to run and which are
already completed, so re-running it with the same parameters (after fixing the
issue that caused it to fail) should resume where it left off.

Debugging Issues With Lambdas
-----------------------------

The step function output includes an 'Exception' tab. If it's not useful, follow the links to 'cloudwatch logs' on the info tab.

See also [aws/hhvm1/README.md](aws/hhvm1/README.md) for more debugging options.
