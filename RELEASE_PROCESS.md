Prerequisites:
- AWS credentials
- Write access to the HHVM staging repository
- Write access to the hhvm.com repository
- Write access to the hhvm-docker repository
- ssh access to the MacOS build machines
- access to HHVM FB page and Twitter accounts.

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
1. Create the tags and start the linux builds:
   `bin/promote-nightly-to-release YYYY.MM.DD 4.x` - note that it's `4.x`, not
   `4.x.0`. For example, `bin/promote-nightly-to-release 2019.07.22 4.15`
1. Open the AWS step functions dashboard, and wait for the source tarballs to
   be created. `hhvm-build` is the most interesting step function at this stage;
   `hhvm-build-and-publish` runs both `hhvm-build` and `hhvm-publish-release`.
1. Start the MacOS builds
   1. in `screen` or similar, `sudo -i -u hhvmoss`
   1. `cd ~/code/homebrew-hhvm`; this is a clone of the `code/homebrew-hhvm`
      repository
   1. `git fetch; git reset --hard origin/master`
   1. Run `./build-release.sh 4.x.0`
   1. Wait for both to complete; binaries are automatically uploaded, and recipe
      changes are automatically pushed
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
   `fbcode/hphp/facebook/update_version_header.h`. Feel free to skip unit test
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
