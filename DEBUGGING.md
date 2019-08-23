# Build Logs

Build logs are in the `hhvm-binary-package-builds/cloud-init-output.log`
CloudWatch log group, and are available via the CloudWatch web UI.

## Listing available logs via CLI

Log stream names are `BUILD_DATE/hhvm-VERSION_DISTRO_EC2-INSTANCE-ID`;

```
$ bin/list-build-logs
2019/08/22/hhvm-2019.08.22_debian-8-jessie_i-0441d0e0f080021fd
2019/08/22/hhvm-2019.08.22_debian-8-jessie_i-08a53d39a3c2ae539
2019/08/22/hhvm-2019.08.22_debian-8-jessie_i-0ca36208f86e6a198
2019/08/23/hhvm-2019.08.23_debian-8-jessie_i-0e79e0b5c07530107
2019/08/23/hhvm-2019.08.23_debian-9-stretch_i-0fb0b6fded99c16da
2019/08/23/hhvm-2019.08.23_ubuntu-16.04-xenial_i-097efd02691fbc546
2019/08/23/hhvm-2019.08.23_ubuntu-18.04-bionic_i-090752a6c30ed87dd
2019/08/23/hhvm-2019.08.23_ubuntu-18.10-cosmic_i-0464e77ca4066150f
2019/08/23/hhvm-2019.08.23_ubuntu-19.04-disco_i-0332fc4967f5d763b
```

## Fetching a log via CLI

To fetch an entire log:

```
$ bin/fetch-build-log 2019/08/23/hhvm-2019.08.23_ubuntu-19.04-disco_i-0332fc4967f5d763b
```

To fetch the last 20 entries:

```
$ bin/tail-build-log 2019/08/23/hhvm-2019.08.23_debian-8-jessie_i-0e79e0b5c07530107 20
```

If the number of entries is omitted, it defaults to 100.

# Docker images for failed builds

Docker images allow you to quickly get a copy of the failed build.


## Listing available images

```
$ bin/list-build-images
Failed builds:
- 2019.08.23_debian-8-jessie_i-0e79e0b5c07530107
- 2019.08.22_debian-8-jessie_i-0441d0e0f080021fd
- 2019.08.22_debian-8-jessie_i-08a53d39a3c2ae539
```

## Logging into Elastic Container Registry (ECR)

First, install Docker; then:

```
$ $(aws ecr get-login | sed 's/ -e none / /')
WARNING! Using --password via the CLI is insecure. Use --password-stdin.
Login Succeeded
```

## Starting a container (instance) from an image

First, check the memory limits in your Docker configuration; the default is
2GB, which will be insufficient.

```
$ IMAGE_NAME=$(aws ecr describe-repositories --repository-name hhvm-failed-builds --query 'repositories[*].repositoryUri' --output text)
$ IMAGE_TAG=2019.08.22_debian-8-jessie_i-08a53d39a3c2ae539 # from above
$ docker run -it --rm ${IMAGE_NAME}:${IMAGE_TAG} /bin/bash -l
```

- `-i`: interactive
- `-t`: use a TTY
- `--rm`: delete container when process (`/bin/bash -l`) exits

## Attaching another terminal to the container

- find the container ID or name from `docker ps`
- `docker exec -it $CONTAINER_NAME_OR_ID /bin/bash -l`

## Debugging debian builds in the container

- Debian builds are created in a directory matching the pattern
`/tmp/hhvmpkg.XXXXXX`
- within this directory, there will be a source directory called
  `hhvm-VERSION` or `hhvm-nightly-VERSION`
- Debian does not build packages directly in the source directory; instead,
  they will be inside the `obj-x86_64-linux-gnu` subdirectory

For example, one build of 2019.08.22 was made in
`/tmp/hhvmpkg.URugWYaQ/hhvm-nightly-2019.08.22/obj-x86_64-linux-gnu`.

Within the build directory:

- if `cmake` completed, you can run `make`
- if `cmake` did not complete, you can run `cmake ..`
