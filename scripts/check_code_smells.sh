#!/usr/bin/env bash

# fail on python pdbs
# exclude venv bc circleci adds the symlink inside our repo, the SOBs
if git ls-files | grep py | xargs grep -r 'pdb.set_trace()'; then
  echo "Found pdb"
  exit 1
fi

# from pre-commit.sample
# figure out what to diff against
if git rev-parse --verify HEAD >/dev/null 2>&1
then
    against=HEAD
else
    # Initial commit: diff against an empty tree object
    against=4b825dc642cb6eb9a060e54bf8d69288fbee4904
fi

# Find files with trailing whitespace
for FILE in `exec git diff-index --check --cached $against -- | sed '/^[+-]/d' | sed -r 's/:[0-9]+:.*//' | uniq` ; do
   # Fix them!
   sed -i 's/[[:space:]]*$//' "$FILE"
   git add "$FILE"
done
exit

# If there are whitespace errors, print the offending file names and fail.
! git diff-index --check --cached $against -- && echo -e  "Whitespace errors! ^^\n=======" && exit 1

echo "No blocking code smells"
