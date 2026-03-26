#!/usr/bin/env bash
set -euo pipefail

WORKFLOW_RUN_SHA="${WORKFLOW_RUN_SHA:?WORKFLOW_RUN_SHA must be set}"

git checkout -f "${WORKFLOW_RUN_SHA}"
git fetch --tags --force
git tag --list 'stable' 'v*' --sort=version:refname | tail -n 20
