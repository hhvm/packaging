#!/bin/sh

# Usage: make-release.sh path-to-hhvm-repo
#
# Makes the "releasing" and "targeting" commits to bump to whatever the next
# patch version of current head of path-to-hhvm-repo is. Does NOT do an
# automatic push so you can spot-check what it did makes sense. Which is good
# because it does basically no error checking.
#
# Only works on versions of HHVM after we moved version info out of IDL and into
# version.h, which was IIRC sometime right before 3.6.

set -e
set -x

cd $1

HEADER="hphp/runtime/version.h"
CMAKE="CMakeLists.txt"

MAJOR=$(grep "#define HHVM_VERSION_MAJOR" "$HEADER" | cut -f 3 -d ' ')
MINOR=$(grep "#define HHVM_VERSION_MINOR" "$HEADER" | cut -f 3 -d ' ')
PATCH=$(grep "#define HHVM_VERSION_PATCH" "$HEADER" | cut -f 3 -d ' ')
TRIPLE="$MAJOR.$MINOR.$PATCH"

sed -i 's/HHVM_VERSION_SUFFIX "-dev"/HHVM_VERSION_SUFFIX ""/' "$HEADER"
sed -i "s/$TRIPLE-dev/$TRIPLE/" "$CMAKE"
git add "$HEADER" "$CMAKE"
git commit -m "Releasing $TRIPLE"
git tag "HHVM-$TRIPLE"

PATCH_NEW=$(expr $PATCH + 1)
TRIPLE_NEW="$MAJOR.$MINOR.$PATCH_NEW"

sed -i "s/HHVM_VERSION_PATCH $PATCH/HHVM_VERSION_PATCH $PATCH_NEW/" "$HEADER"
sed -i 's/HHVM_VERSION_SUFFIX ""/HHVM_VERSION_SUFFIX "-dev"/' "$HEADER"
sed -i "s/$TRIPLE/$TRIPLE_NEW-dev/" "$CMAKE"
git add "$HEADER" "$CMAKE"
git commit -m "Targeting $TRIPLE_NEW"
