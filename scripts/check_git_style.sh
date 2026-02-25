#!/usr/bin/env bash

GREP_BRANCH_PATTERN="(KC)(\s|-)[0-9]+"
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
PARENT_BRANCH=$(git log --pretty=format:'%D' HEAD^ | grep 'origin/' | head -n1 | sed 's@origin/@@' | sed 's@,.*@@')

case $CURRENT_BRANCH in
    master| staging |production)
        exit 0;;  # skip
    *)
        :;;
esac
# check branch name
BRANCH_CONTAINS_TICKET=$(echo $CURRENT_BRANCH | grep -iE $GREP_BRANCH_PATTERN | sort | wc -l)

if [ $BRANCH_CONTAINS_TICKET == "1" ];
then
    :
else
    echo "Branch name does not contain ticket number"
    echo $CURRENT_BRANCH
fi

BRANCH_COMMITS_COUNT=$(git log $CURRENT_BRANCH ^origin/$PARENT_BRANCH --no-merges --pretty=format:%s | sort | wc -l)
GOOD_COMMITS_COUNT=$(git log $CURRENT_BRANCH ^origin/$PARENT_BRANCH --no-merges --pretty=format:%s | grep -iE $GREP_BRANCH_PATTERN | sort | wc -l)

if [ $BRANCH_COMMITS_COUNT == $GOOD_COMMITS_COUNT ];
then
    :
else
    echo "Commit messages do not have ticket number"
    git log $CURRENT_BRANCH ^origin/$PARENT_BRANCH --no-merges --pretty=format:%s | grep -viE $GREP_BRANCH_PATTERN | sort
fi
