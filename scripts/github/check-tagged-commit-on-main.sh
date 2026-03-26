#!/usr/bin/env bash
set -euo pipefail

git fetch --no-tags origin main

if git merge-base --is-ancestor "${GITHUB_SHA}" "origin/main"; then
  echo "is_on_main=true" >> "$GITHUB_OUTPUT"
  echo "Tagged commit ${GITHUB_SHA} is contained in origin/main."
else
  echo "is_on_main=false" >> "$GITHUB_OUTPUT"
  echo "Tagged commit ${GITHUB_SHA} is not contained in origin/main. Skipping stable update."
fi
