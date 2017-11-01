Next Generation HHVM Binary Packaging
=====================================

All linux builds will be in Docker containers, on AWS.

Configuration
=============

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
all required build dependencies.

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

Docker base images
==================

Required for:
 - Debian Wheezy

Some distributions do not have a recent enough GCC, so we use a custom base image and lie about build-depends. To build these:

```
docker build --tag debian-7-wheezy:hhvm \
  -f ./dockerfiles/debian-7-wheezy.Dockerfile \
  ./dockerfiles
```

This must be done before following the instructions above.

AWS
===

As we want to execute docker commands, we run directly on EC2, not ECS. AWS
supports running commands on EC2 instance startup - EC2 calls this
'user data' - a file or script-as-text in 'user data' will be executed.

The scripts we use are in the `aws/` subdirectory, and expect to be ran on
Ubuntu 16.04 hosts.

Manually triggering a package build on AWS
------------------------------------------

Assuming the `hhvm-downloads` S3 bucket contains the relevant source
tarball and you have the AWS CLI configured:

```
DISTRO=debian-8-jessie VERSION=2017.10.30 bin/make-package-on-aws
```

This will put the packages into the private `hhvm-scratch` S3 bucket.
