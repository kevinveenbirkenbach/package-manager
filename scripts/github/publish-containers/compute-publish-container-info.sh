#!/usr/bin/env bash
set -euo pipefail

SHA="$(git rev-parse HEAD)"

V_TAG="$(git tag --points-at "${SHA}" --list 'v*' | sort -V | tail -n1)"
if [[ -z "${V_TAG}" ]]; then
  echo "No version tag found for ${SHA}. Skipping publish."
  echo "should_publish=false" >> "$GITHUB_OUTPUT"
  exit 0
fi

VERSION="${V_TAG#v}"

STABLE_SHA="$(git rev-parse -q --verify 'refs/tags/stable^{commit}' 2>/dev/null || true)"
IS_STABLE=false
[[ -n "${STABLE_SHA}" && "${STABLE_SHA}" == "${SHA}" ]] && IS_STABLE=true

{
  echo "should_publish=true"
  echo "version=${VERSION}"
  echo "is_stable=${IS_STABLE}"
} >> "$GITHUB_OUTPUT"
