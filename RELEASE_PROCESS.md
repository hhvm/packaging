Prerequisites:
- access to hhvm/hhvm-staging
- a checkout of the HHVM release branch from staging
- `staging` added as a remote of that checkout:
  `git remote add staging git@github.com:hhvm/hhvm-staging.git`

The staging repository is the source of truth for release branches; they are
automatically copied to the public repository by the scripts when appropriate.

Creating a .new .0 release
==========================

Before Branch Cut
-----------------

- Finalize what features are in this release
- Make sure they're turned on by default
- Make sure that any changes we pre-announced are included; e.g. if the previous
  release said "this is opt-in now, but will be mandatory in the next release",
  it should be included unless there's a strong reason not to.

At Branch Cut (2 weeks before release)
--------------------------------------

- create a `HHVM-$x.$y` branch of hhvm/hhvm-staging from the corresponding internal branch point
- create a `HHVM-$x.$y` branch of this repository from master

If there are any commits in the internal release branch that should be copied to
the github release branch, on a server with access to FB repositories and an ssh
key that GitHub recognizes:

```
~/fbcode/opensource/shipit/bin$ php run_shipit.php \
  --project=hhvm \
  --destination-github-org=hhvm \
	--destination-github-project=hhvm-staging \
  --destination-branch=HHVM-3.27 \
  --source-branch=releases/hphp/2018-06-04-l \
  --destination-use-ssh
```

Replace the source-branch and destination-branch arguments as appropriate for
this release.


Before Release Date
-------------------

- if there are more internal commits to the branch, re-run the shipit command
  above
- prepare release announcement (hhvm/hhvm.com repository). For review:
  - can create in Quip and export to markdown. Double-check the markdown is valid
  - can create a pure markdown pull request, but don't merge until release day
- build HHVM locally from the branch cut
- get all our active github projects passing tests and typechecker against that
  build; this will usually mean that they pass on nightly builds in CI, but this
  might not be the case depending on what other changes are needed
- tag new releases of any projects that needed changes (updating dependencies
  is a change)

Some projects are special:
- check if recent releases are made from master, or a stable branch; for example,
  hack-codegen currently tags off the 3.x branch. Both the 3.x and master branch
  need to work, and be careful to tag the release from the correct branch
- the HSL likely should be retagged even if the previous release worked fine, to
  ship any feature changes
- HHAST will need new codegen:

```
hhast$ bin/update-codegen \
  --hhvm-path=path/to/checkout/of/release/branch \
  --rebuild-relationships
```

If AST fields have been renamed or removed, some linters/migrations may need
updating after this.

At Release Date
---------------

Wait for it to be deployed to prod. This usually happens on Thursday, then we
ship it externally the monday after if there are no known issues. Delay if
the internal release is delayed.

1. if this is an LTS release, edit the files under `repo-conf/` to add new LTS apt repositories
1. commit to master and push
1. edit `DEBIAN_REPOSITORIES` in existing release branches if changing from an LTS or to an LTS
1. commit and push the branch
1. update `DEBIAN_REPOSITORIES` to remove the main `DISTRO` release from older versions
1. commit and push the branches
1. create a `HHVM-$x.$y` branch of the hhvm-docker repository
1. update `DOCKER_TAGS` to include `latest`, and `$x.$y-lts-latest` if appropriate
1. commit and push the branch
1. update `DOCKER_TAGS` in any other supported branches to remove the `latest` tag
1. commit and push the branches
1. then do everything needed for a `.z` release below


Creating a new .z release
=========================

1. from a checkout of the HHVM release branch, run
  `/path/to/hhvm-packaging/bin/hhvm-tag-and-push`. This updates version.h, makes the tag, and updates
  version.h again, then pushes to the repo again.
1. run `bin/make-all-packages-on-aws $VERSION` from the hhvm-packaging repository
1. wait for the step function to build the source tarballs.
1. start the mac builds
1. wait for the step function and mac builds to complete
    This is a good time convert the release notes from quip to markdown for publication. Pay attention to fixed-width text links
    When the step function is finished, you should have:
      - published source tar balls
      - published linux binaries
      - published docker images
      - public tags and branch
1. check the expected files are available for download:
   `https://hhvm.com/api/build-status/VERSION`
1. publish the release announcement


Mac Builds
========

1. on every builder, `brew unlink hhvm` and `brew unlink hhvm-pmeview` to disable your existing installations
2. on every builder, make sure `Xcode-select -p` doesn't point at an FB bundle - use `sudo Xcode-select -s /Applications/Xcode.app` if it does
3. Get the source:
  If the source is public, get it from https://dl.hhvm.com/source/; if not, `aws s3 cp s3://hhvm-scratch/hhvm-$VERSION.tar.gz ~/`; get the .sig file too and verify it with `gpg --verify hhvm-$VERSION.tar.gz.sig hhvm-$VERSION.tar.gz`
4. Compute the sha256: `openssl sha -sha256 hhvm-$VERSION.tar.gz`
5. In the homebrew-hhvm repository, update the url and sha256 for the new version in hhvm.rb, and incorporate any other changes from hhvm-preview.rb. If the source is not yet public, you can temporarily use a file:/// URL, but remember to change it back before pushing
6. temporarily remove the `bottle` section
7. copy the source (if needed) and hhvm.rb to every builder
8. on every builder, run `brew install --build-bottle ./hhvm.rb`
9. on every builder, `brew bottle '--root-url=https://dl.hhvm.com/homebrew-bottles' --force-core-tap ./hhvm.rb`; This will output some ruby code for the 'bottle' section - merge the one from each builder together (multiple 'sha256' lines, one per targeted MacOS release) into hhvm.rb.
10. upload the bottles: `aws s3 hhvm-$VERSION.$MACOS_VERSION.bottle.tar.gz s3://hhvm-downloads/homebrew-bottles/`
11. update the source URL in hhvm.rb back to the public download URL if you were using file://
12. commit and push once the source is definitely uploaded and public

If you get bogus stuff like `/bin/sh: /bin/sh: cannot execute binary file`, make sure you don't have any cronjobs killing activedirectoryd or parentcontrolsd
