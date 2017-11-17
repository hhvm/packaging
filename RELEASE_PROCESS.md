Overall Process
===============
1. Remove "-dev" suffix from hphp/runtime/version.h, commit to branch as "Releasing $VERSION"
2. tag it: git tag HHVM-$VERSION
3. push the tag: git push staging HHVM-$VERSION
4. re-add the "-dev" suffix, and bump HHVM_VERSION_PATCH. Commit to branch as "Targeting $NEXT_PATCH_VERSION"
5. push the branch to staging
6. run `bin/make-all-packages-on-aws $VERSION` from the hhvm-packaging repository
7. wait for the step function to build the source tarballs.
8. start the mac builds
9. wait for the step function and mac builds to complete
  This is a good time convert the release notes from quip to markdown for publication. Pay attention to fixed-width text links

  When the step function is finished, you have:
    - published source tar balls
    - published linux binaries
    - published docker images
    - public tags and branch
10. update the hhvm/hhvm:latest and hhvm/hhvm-proxygen:latest docker tags, and any relevant -lts versions
11. publish the release announcement


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
