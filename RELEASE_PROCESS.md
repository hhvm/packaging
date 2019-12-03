Prerequisites:
- AWS credentials
- Write access to the HHVM staging repository
- Write access to the hhvm.com repository
- Write access to the hhvm-docker repository
- correctly configured Azure DevOps CLI client (optional, to track progress or
  deal with issues)
- access to HHVM FB page and Twitter accounts

Creating a new .0 release
==========================

Releases are generally on Mondays, from Sunday's nightly builds.

1. Find a suitable nightly build.
   - This should be Friday-Sunday evening. If there is no suitable build, or they
    seem too close together (e.g. Tuesday v4.x, Thursday v4.(x+1)), consider
    delaying until Tuesday and using Monday's nightly build, fixing any
    outstanding blockers. This may mean changes to Hack, HHVM, or the
    tools/libraries.
   - Builds should have succeeded for all
     supported platforms (e.g. see https://hhvm.com/api/build-status/2019.07.22)
   - Tools and libraries should be passing on the nightlies (see
     https://travis-ci.org/hhvm)
1. Create the tags and start the builds:
   `bin/promote-nightly-to-release YYYY.MM.DD 4.x` - note that it's `4.x`, not
   `4.x.0`. For example, `bin/promote-nightly-to-release 2019.07.22 4.15`
1. You can track progress in the AWS step functions dashboard. MacOS build
   output is available in the Azure web interface (see below). Output of
   finished (successful or failed) builds can also be fetched using
   `bin/aws-build-status`.
1. While waiting for the builds (linux and mac), write the blog post:
   1. Use existing posts as a template.
   1. Use `hhast` announcements from the previous week as guide for if codemods
      are available.
   1. Fetch the staging repository with `git fetch --tags`; use
      `git log --oneline HHVM-4.x.0..HHVM-4.y.0` or
      `HHVM-4.x.0..nightly-YYYY.MM.DD` to find a list of commits for highlights
      and breaking changes. The `nightly-YYYY.MM.DD` tags are only pushed to
      the staging repository to avoid spamming the main one.
1. Once all builds are complete, commit and push the blog post
1. Announce on Facebook page, sharing to HHVM and Hack Users Group, and from
   Twitter. Include link to blog post.
1. Update the `version.h` header in master; use
   `fbcode/hphp/facebook/update_version_header.sh`. Feel free to skip unit test
   runs etc.

Creating a new .z release
=========================

1. Check out the HHVM-x.y branch (e.g. `HHVM-4.16)
   of the hhvm-staging repository
1. cherry-pick or otherwise apply your changes
1. make sure there are no uncommitted changes
1. check out the HHVM-x.y branch of this packaging repository
1. from your hhvm checkout, run
  `/path/to/packaging/checkout/bin/hhvm-tag-and-push`; this will update
  `version.h`, update the branch on github, and create the tag
1. from this repository, run `bin/make-all-packages-on-aws 4.y.z`, e.g.
  `bin/make-all-packages-on-aws 4.16.1`
1. The AWS step functions are now running; proceed with release notes and MacOS
   builds as for `.0` releases; do not update `version.h` in master.

Building A MacOS Release On Azure
=================================

This lets us build many in parallel, instead of restricting us to our
permanent worker machines.

Initial Setup
-------------

1. [Install the Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
2. `az login --allow-no-subscriptions`
3. Add the 'devops' extension to get CLI access to Azure pipelines:
   `az extension add --name azure-devops`
4. Configure the Azure Devops extension to use the correct organization and project:
    `az devops configure --defaults organization=https://dev.azure.com/hhvm-oss/ project=hhvm-oss-builds` - alternatively, add `--organization` and
    `--project` options to all following commands

General Use
-----------

Builds are triggered automatically from the AWS step function, so the commands
below should only be needed in case of issues.

Starting a job:

```
$ az pipelines build queue --variables hhvm.version=4.15.1 --definition-name hhvm-oss-builds-CI -o table
```

Listing jobs:

```
$ az pipelines build list --top 20 -o table
ID    Number    Status      Result    Definition ID    Definition Name     Source Branch    Queued Time                 Reason
----  --------  ----------  --------  ---------------  ------------------  ---------------  --------------------------  --------
12    12        inProgress            1                hhvm-oss-builds-CI  master           2019-08-09 10:03:13.818939  manual
11    11        completed   failed    1                hhvm-oss-builds-CI  master           2019-08-09 09:52:02.412387  manual
10    10        completed   failed    1                hhvm-oss-builds-CI  master           2019-08-09 09:21:10.523309  manual
9     9         completed   failed    1                hhvm-oss-builds-CI  master           2019-08-09 09:08:00.526379  manual
5     5         completed   failed    1                hhvm-oss-builds-CI  master           2019-08-08 15:34:21.857854  manual
8     8         completed   canceled  1                hhvm-oss-builds-CI  master           2019-08-08 15:43:00.310012  manual
7     7         completed   canceled  1                hhvm-oss-builds-CI  master           2019-08-08 15:42:10.073800  manual
6     6         completed   canceled  1                hhvm-oss-builds-CI  master           2019-08-08 15:41:19.357546  manual
4     4         completed   failed    1                hhvm-oss-builds-CI  master           2019-08-08 15:31:09.347933  manual
3     3         completed   failed    1                hhvm-oss-builds-CI  master           2019-08-08 15:19:30.592465  manual
2     2         completed   failed    1                hhvm-oss-builds-CI  master           2019-08-08 15:10:51.677154  manual
1     1         completed   failed    1                hhvm-oss-builds-CI  master           2019-08-08 15:07:30.406701  manual
```

For status of just one job:

```
$ az pipelines build show --id 12 -o table
ID    Number    Status      Result    Definition ID    Definition Name     Source Branch    Queued Time                 Reason
----  --------  ----------  --------  ---------------  ------------------  ---------------  --------------------------  --------
12    12        inProgress            1                hhvm-oss-builds-CI  master           2019-08-09 10:03:13.818939  manual
```

Use the [Azure web interface](https://dev.azure.com/hhvm-oss/hhvm-oss-builds/_build?definitionId=1) to see detailed
build status, including stdout/stderr.

# Manual Fixups of Formula

If a bottle is built, but the recipe update fails (e.g. git issues):

- download with s3 or wget, e.g.
  `aws s3 cp s3://hhvm-downloads/homebrew-bottles/hhvm@3.30-lts-3.30.8_1.high_sierra.bottle.tar.gz ./` , or
  `wget https://dl.hhvm.com/homebrew-bottles/hhvm@3.30-lts-3.30.8_1.high_sierra.bottle.tar.gz'
- generate sha, e.g. `openssl dgst -sha256 hhvm@3.30*sierra*`
- manually add the sha to the bottle section
