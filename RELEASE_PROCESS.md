Prerequisites:
- AWS credentials
- Write access to the HHVM staging repository
- Write access to the hhvm.com repository
- Write access to the hhvm-docker repository
- access to HHVM FB page and Twitter accounts

Overview of the repositories
============================

* fbcode: the source of truth for HHVM and Hack
* https://github.com/facebook/hhvm - the public repository for HHVM and Hack. The master is automatically synced from fbcode by fbshipit

* https://github.com/hhvm/hhvm-staging - a private fork of facebook/hhvm. This is the source of truth for tags and release branches. This allows us to prepare security updates in private in a repository accessible by AWS and Azure
* https://github.com/hhvm/hhvm.com - public repository containing the hhvm.com (http://hhvm.com/) website and all blog posts
* https://github.com/hhvm/packaging - public repository containing the overall public CI infrastructure, and the public linux build configurations/scripts
* https://github.com/hhvm/hhvm-docker - public repository containing the templates for our docker (container) images. This could be merged. It is a separate repository as it is self-contained and comparatively straightforward, but there is no need for it to be.

**Security releases**: nothing should be done in any public repository - and no build steps should be ran that operate in/write to public repositories - until the planned disclosure date.

Version numbers
===============

In the master branch, hphp/runtime/version.h always sets version to something like 4.x.0-dev - the “-dev” is always present, and is desired in manual and nightly builds. 4.x is the next release, not the latest. For example, if we have just released 4.155.0, version.h in master should be 4.156.0-dev


* x can be incremented by manually editing the file (for master, this should be in fbcode, for releases, directly in the branches on GitHub), or, for master, by running `hphp/facebook/update_version_header.sh`
    * if done manually or by the script in fbcode, a diff must be created and reviewed manually, like any other fbcode diff
    * this should be done soon after the .0 release is tagged, both when following this procedure, and for regular .0 releases so that e.g . when 4.155.0 is tagged, the next nightly build is 4.156.0-dev, not 4.155.0-dev
* CodemodConfigUpdateHHVMVersionHeader creates a diff once a week to update the version header, removing the need for this manual work. If there are test failures, a Meta employee must take ownership of the diff in order to land it.
* Codemods are usually disabled during code freezes; when this is the case, the version number must be updated manually, or via the script.
* The "-dev" needs to be removed from version.h in the release branch
* nightly builds have a distinct YYYY.MM.DD package version number (e.g. .deb), but this is not part of version.h or the included executables; hhvm --version will report the 4.x.0-dev string, no YYYY.MM.DD
    * nightly-YYYY.MM.DD tags are automatically created and pushed to both facebook/hhvm and hhvm/staging, which makes it easy to identify the specific github commit used for a nightly build


Creating a regular, unpatched .0 release
========================================

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
     https://fburl.com/hhvm_oss_ci)
1. Create the tags and start the builds:
   `bin/promote-nightly-to-release YYYY.MM.DD 4.x` - note that it's `4.x`, not
   `4.x.0`. For example, `bin/promote-nightly-to-release 2019.07.22 4.15`
   - Note: The version number in `version.h` in the nightly build you're
     promoting must match the `4.x` tag you're promoting it to. This should
     happen automatically (see last step below) but it can occasionally fail, so
     it is worth double-checking here. If the version number doesn't match,
     update it and wait for the next nightly build.
1. You can track progress in the AWS step functions dashboard. MacOS build
   output is available in the Azure web interface (see below). Output of
   finished (successful or failed) builds can also be fetched using
   `bin/aws-build-status`.
1. While waiting for the builds (linux and mac), write the blog post:
   1. Use existing posts as a template.
   1. Use `hhast` announcements from the previous week as guide for if codemods
      are available.
   1. Use
      [GitHub UI](https://github.com/facebook/hhvm/compare/HHVM-4.44.0...nightly-2020.02.18)
      (replace version numbers in the URL) or
      `git log --oneline HHVM-4.x.0..HHVM-4.y.0` or
      `HHVM-4.x.0..nightly-YYYY.MM.DD` to find a list of commits for highlights
      and breaking changes.
1. Once all builds are complete, commit and push the blog post
1. If it is an LTS release (or a security update), announce on the [Facebook
   page](https://www.facebook.com/hhvm), sharing to [HHVM and Hack Users
   Group](https://www.facebook.com/groups/hhvm.general), and on Twitter
   [hhvm](https://twitter.com/hiphopvm) and
   [hacklang](https://twitter.com/hacklang). Include link to blog post.
1. Update the `version.h` header in master; use
   `fbcode/hphp/facebook/update_version_header.sh`. Feel free to skip unit test
   runs etc.
   - There should be an automatically generated (FB-internal) diff in
     Phabricator that you can just accept (it's generated weekly, every Sunday
     night). If you do, the diff should land automatically, but make sure to
     check later that this actually happened.

Creating a new .z release
=========================

1. Check out the HHVM-x.y branch (e.g. `HHVM-4.16`)
   of the hhvm-staging repository
1. cherry-pick or otherwise apply your changes
1. make sure there are no uncommitted changes
1. check out the HHVM-x.y branch of this packaging repository
1. from your hhvm-staging checkout, run
  `/path/to/the/worktree/of/packaging/bin/hhvm-tag-and-push`; this will update
  `version.h`, update the branch on github, and create the tag
1. from this repository, run `bin/build-on-aws 4.y.z`, e.g.
  `bin/build-on-aws 4.16.1`
1. The AWS step functions are now running; proceed with release notes and MacOS
   builds as for `.0` releases; do not update `version.h` in master.

What `bin/promote-nightly-to-release YYYY.MM.DD 4.123` does
===========================================================

1. It creates and pushes an HHVM-4.123 branch of the hhvm/packaging repository; this is so that if we create 4.123.99 in a year, we have a reproducible build - e.g. the same debian build scripts as we used for 4.123.0
2. It clones the facebook/hhvm repository
3. It creates an HHVM-4.123 branch from the nightly-YYYY.MM.DD tag
4. It runs bin/hhvm-tag-and-push 4.123.0
    1. It removes the -dev from version.h
    2. This is committed to the new branch as “Releasing 4.123.0” and tagged as HHVM-4.123.0
    3. It changes the .0 and to version.h to .1 and re-adds "-dev"; This is so that if a build is made from this branch before the next release, it is clear that it is not the release build and may have different contents
    4. This is committed to the new branch as “Targetting 4.123.1”
    5. The branch and tag are pushed *to the private hhvm/staging repository* - they are not pushed to the public repository


5. It clones the hhvm/hhvm-docker repository
6. It checks out the HHVM-4.$PREVIOUS_VERSION (e.g. HHVM-4.122) branch
7. it removes latest from the EXTRA_TAGS file of the branch and commits it (docker ‘tags’ are essentially package version numbers/version aliases)
8. It creates a new HHVM-4.123 branch
9. it adds latest and 4.123-latest to the EXTRA_TAGS file; this makes it so that once built, HHVM-4.123 will be installed instead of HHVM-4.122 by docker install hhvm/hhvm - hhvm/hhvm:4.123-latest and hhvm:4.123.0 will also be created
10. it commits this, and pushes both branches
11. it runs bin/build-on-aws 4.123.0 - *this will build _and publish_ the release, source and binaries.* We generally expect that security updates will not be .0 releases.

What `bin/build-on-aws` does
============================

This builds and publishes a release (or multiple releases) for all our supported platforms; it triggers an AWS Step Function (state-machine-as-a-service) to orchestrate the build. The step function will also trigger the MacOS builds on Azure

You can also choose to run just specific steps - for example, if only docker failed, you can pass PublishDockerImages to run just that step. Run build-on-aws with --help or with no arguments for more details.

It is possible to prepare the Linux release builds without publishing them, e.g. for security fixes; specify the MakeSourceTarball and MakeBinaryPackage steps. MacOS currently can not be built without publishing.

Creating a patched `.0` release
===============================

This should be done rarely; we should usually create x.y.0 directly from the previous nightly, and we should aim to have all patches in master; one case for a patched .0 is when you want to create a new release with a security patch that has not yet hit GitHub master. Waiting a day is often a better choice, but if it’s late in the week, that may in effect mean skipping the release.


`bin/promote-nightly-to-release YYYY.MM.DD 4.123` does many things, some of which are undesired for this case; in particular, we need to create the branch and tag by hand. The flow here looks like:

1. Clone the facebook/hhvm repository, or use an existing checkout
2. Create the release branch: git checkout -b HHVM-4.123 nightly-YYYY.MM.DD
3. Apply and commit changes, e.g. with git cherry-pick, patch -p1 ; git commit etc
4. Test changes
5. run bin/hhvm-tag-and-push 4.123.0
6. run bin/promote-nightly-to-release existing-tag 4.123 - this is literally the string ‘existing-tag’, not a placeholder/variable - as this is a .0 release, we still need the automated changes to the hhvm/packaging and hhvm/docker repositories
