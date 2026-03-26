#!/usr/bin/env bash
set -euo pipefail

TARGET_SHA="${TARGET_SHA:-${GITHUB_SHA:?GITHUB_SHA must be set}}"

git fetch --no-tags origin main

if git merge-base --is-ancestor "${TARGET_SHA}" "origin/main"; then
  echo "is_on_main=true" >> "$GITHUB_OUTPUT"
  echo "Target commit ${TARGET_SHA} is contained in origin/main."
else
  echo "is_on_main=false" >> "$GITHUB_OUTPUT"
  echo "Target commit ${TARGET_SHA} is not contained in origin/main. Skipping main-only action."
fi
