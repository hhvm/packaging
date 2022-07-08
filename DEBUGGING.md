# Build Status

```
$ ./bin/aws-build-status 4.164.0-wilfred-2022-07-08-11-38

Execution '4.164.0-wilfred-2022-07-08-11-38' RUNNING.

Finished tasks:
  ParseInput (0:00:00.581)
  MakeSourceTarball 4.164.0 (0:04:38.608)
  GetPlatformsForVersion 4.164.0 (0:00:00.981)
  MakeBinaryPackage 4.164.0 debian-11-bullseye (1:01:52.717)
  MakeBinaryPackage 4.164.0 ubuntu-18.04-bionic (1:03:54.473)
  MakeBinaryPackage 4.164.0 ubuntu-20.04-focal (1:10:25.165)
  MakeBinaryPackage 4.164.0 ubuntu-21.04-hirsute (1:11:33.412)
  MakeBinaryPackage 4.164.0 ubuntu-21.10-impish (1:12:32.22)
  MakeBinaryPackage 4.164.0 debian-10-buster (1:25:24.975)
  PublishBinaryPackages 4.164.0 (0:13:10.525)
  PublishSourceTarball 4.164.0 (0:04:11.258)
  PublishDockerImages 4.164.0 (0:05:15.277)

Unfinished tasks:
  BuildAndPublishMacOS 4.164.0

Use -v (--verbose) to see full build output.
```

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

You can also run `aws ecr get-login` on a computer with AWS access tokens, then
run the produced `docker login` command on another computer - for example, an
EC2 instance you're using for debugging.

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
