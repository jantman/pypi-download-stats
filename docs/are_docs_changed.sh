#!/bin/bash -x
# helper to check and see if there are uncommitted git changes to docs

DOC_SOURCE=$1

function dirty {
    >&2 echo "ERROR: generating documentation results in uncommitted changes; please re-generate and commit docs locally"
    git diff --no-ext-diff --exit-code $DOC_SOURCE
    git diff-index --cached HEAD -- $DOC_SOURCE
    exit 1
}

git diff --no-ext-diff --quiet --exit-code $DOC_SOURCE || dirty
git diff-index --cached --quiet HEAD -- $DOC_SOURCE || dirty
exit 0
