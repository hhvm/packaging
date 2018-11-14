Next Generation HHVM Binary Packaging
=====================================

All linux builds will be in Docker containers, on AWS.

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
 - `bin/make-all-packages-on-aws VERSION`

If you just need to rebuild for one distribution, with no code changes:

 - edit `DISTRO/PKGVER` if needed (e.g. if a previouis package was pushed for this HHVM version and distribution) and push to github
 - `bin/make-package-on-aws VERSION DISTRO`

Building source tarballs and linux packages for multiple new releases
-----------------------------------------------------------

The common case is fixing a bug in multiple releases - for example, the current
release and all active LTS releases - simultaneously.

 - tag all the releases on the `hhvm-staging repo`
 - `bin/make-multiple-releases-on-aws VERSION1 [VERSION2 [...]]`

How it works
------------

There are 3 kinds of jobs used here:

- AWS lambdas: code that can be written in stateless javascript
- jobs that run on EC2 instances: any other code. For example, building HHVM, or updating apt repositories
- AWS step functions: these are state machines, which coordinate the previous steps

Step functions can not directly run other step functions, or wait for an EC2 instance. When we want that, what we do is:

1. invoke a lambda to start the sub-job, whatever it is
1. wait a while
1. invoke a different lambda to check if it's finished
1. repeat if neccessary

There are 2 main step functions:

- `hhvm-build`: build a specific version of HHVM - source tarball, and binaries for multiple distributions. Multiple instances can run in parrallel.
- `hhvm-publish-release`: take the output of `hhvm-build` for a specific verison (but multiple distributions). Multilpe instances must run sequentially. This will:
  - update the apt repostiories
  - publish source to the public github repository if it wasnt already there

These aren't usually directly invoked - instead, two wrappers are used:

- `hhvm-build-and-publish`: build and publish a single tagged release. Usually used for feature releases and nightly builds. It will execute an instance of `hhvm-build`, then an instance of `hhvm-publish-release`
- `hhvm-build-and-publish-multi`: build and publish multiple tagged releases. It will spin up parrallel instances of `hhvm-build`, then sequential instances of `hhvm-publish-release`. This is used when we want multiple near-simultaenous releases, for example, when publishing security updates.

For more details, look at the definitions either in AWS console, or `aws/step-functions/`

S3 Buckets
----------

- `hhvm-downloads`: public. This is `dl.hhvm.com`
- `hhvm-scratch`: private. build artifacts and release source tarballs before public

EC2 Jobs
--------

Each kind of EC2 job has distinct 'userdata'; this is a shell script that AWS will invoke when imaged. You can see these in `aws/userdata/`.
Some of them depend on environment variables being set - this is accomplished by using lambdas to spawn them, which prepend variable initialization
to the userdata script before passing it to the EC2 API.

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

Currently, these are:

- `create-s3-index-html`: takes an S3 bucket ID, and automatically generates `index.html` files
- `get-instances-state`: takes multiple EC2 instance IDs, and returns per-instance state, and a flag indicating if any are still running
- `get-state-machine-executions-state`: same, but for AWS step function execution IDs
- `hhvm-build-binary-packages`: takes a version number and multiple distribution names, spins up worker EC2 instances. Usually followed by a wait then `get-instances-state`
- `hhvm-build-source-tarball`: takes version number, branch info, etc, and spins up a worker EC2 instance. Usually followed by a wait then `hhvm-have-source-tarball`
- `hhvm-get-build-version`: takes an optional version number (none for nightlies), and returns branch information, source tarball S3 location, and a flag for if it's a nightly.
  Usually followed by `hhvm-build-source-tarball`.
- `hhvm-have-source-tarball`: takes the output of `hhvm-get-build-version`, and returns true if the source tarball is in the expected place in S3
- `hhvm-invalidate-repository-metadata-on-cloudfront`: optionally takes a version number, but it's unused except for a job ID. It purges all `apt` metadata from the CDN caches.
  This is usually a final step in the build process.
- `hhvm-publish-release-source`: takes `hhvm-get-build-version` output, and:
  - if a nightly build, does nothing
  - otherwise, starts an EC2 job to publish the source code
- `hhvm-publish-single-release`: takes a version number, and starts the `hhvm-publish-release` step function. Usually called by the `hhvm-build-and-publish` step function, followed by a wait then `get-state-machine-executions-state`.
- `hhvm-start-multiple-builds`: takes mutiple version numbers, and starts multiple instances of the `hhvm-build` step function. Usually called by the `hhvm-build-and-publish-multi` step function, followed by a wait then `get-state-machine-executions-state`.
- `hhvm-start-single-builds`: takes a version number, and starts the `hhvm-build` step function. Usually called by the `hhvm-build-and-publish` step function, followed by a wait then `get-state-machine-executions-state`.
- `hhvm-update-repositories`: takes a version number, and starts an EC2 instance to update the apt repositories
- `shift-version`: takes a `versions` value, and returns `{ version: version[0] ?? null, versions: versions.slice(1) }`. Used by `hhvm-build-and-publish-multi` to iterate over versions when sequentially publishing releaes
- `terminate-instances`: takes multiple EC2 instance IDs, and terminates them (shutdown with storage deletion)

Resuming Failed Step Functions
------------------------------

This isn't supported by AWS; if you need to do this, you have two options:
- 1. cancel the parent step function (if any)
  1. delete any artifacts produced by the step function, its parent, or its siblings
  1. restart the process
- run the neccessary commands by hand: find the produced output of the previous step in the AWS step functions console, and directly invoke the the next lambda as above. Repeat for the next step until you've traversed the state machine.

Debugging Issues With Lambdas
-----------------------------

The step function output includes an 'Exception' tab. If it's not useful, follow the links to 'cloudwatch logs' on the info tab.
