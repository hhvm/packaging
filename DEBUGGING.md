# Build Logs

Build logs are in the `hhvm-binary-package-builds/cloud-init-output.log`
CloudWatch log group, and are available via the CloudWatch web UI.

## Listing available logs via CLI

Log stream names are `BUILD_DATE/w_EC2-INSTANCE-ID`:

```
$ bin/list-build-logs | head
2021-06-07-12:25:39	2021/06/07/w_i-0f456bda6e984b976
2021-06-07-12:22:59	2021/05/28/w_i-0dad52efaf60c6982
2021-06-07-12:22:53	2021/05/25/w_i-0c7683e5a49b11fea
2021-06-07-12:15:57	2021/06/07/w_i-0ee499aacd2925004
2021-06-06-22:01:01	2021/06/07/w_i-0a0ae840bb4c7f1e2
2021-06-06-21:52:34	2021/06/07/w_i-05e1a1a3ab88fe1ed
2021-06-06-21:50:59	2021/06/07/w_i-0527af8a61949f942
2021-06-06-21:46:21	2021/06/07/w_i-0df5fbf3b91a31622
2021-06-06-21:37:36	2021/06/07/w_i-08361e376625befbe
2021-06-06-21:35:35	2021/06/07/w_i-0d974edb7d50b0583
```

The EC2 instance ID can be found in the AWS console, or from
`bin/aws-build-status` for any failed build steps:

```
$ bin/aws-build-status 2021.06.07-jjergus-2021-06-07-12-28

Execution '2021.06.07-jjergus-2021-06-07-12-28' FAILED.

Finished tasks:
  ParseInput (0:00:00.486)
  GetPlatformsForVersion 2021.06.07 (0:00:00.636)
  FAILED: MakeBinaryPackage 2021.06.07 ubuntu-21.04-hirsute (0:17:53.631)
  VersionNormalizeResults 2021.06.07 (0:00:00.46)
  CheckIfReposChanged (0:00:00.46)
  NormalizeResults (0:00:00.047)

Unfinished tasks:
  CheckForFailures

The following steps have failed:

MakeBinaryPackage 2021.06.07 ubuntu-21.04-hirsute {"ec2":"i-0511cc318a06d72f7","time_sec":"143"}

Use -v (--verbose) to see full build output.
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
