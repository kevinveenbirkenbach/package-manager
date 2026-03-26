#!/usr/bin/env bash
set -euo pipefail

git config user.name "github-actions[bot]"
git config user.email "github-actions[bot]@users.noreply.github.com"

echo "Ref: $GITHUB_REF"
echo "SHA: $GITHUB_SHA"

VERSION="${GITHUB_REF#refs/tags/}"
echo "Current version tag: ${VERSION}"

echo "Collecting all version tags..."
ALL_V_TAGS="$(git tag --list 'v*' || true)"

if [[ -z "${ALL_V_TAGS}" ]]; then
  echo "No version tags found. Skipping stable update."
  exit 0
fi

echo "All version tags:"
echo "${ALL_V_TAGS}"

LATEST_TAG="$(printf '%s\n' "${ALL_V_TAGS}" | sort -V | tail -n1)"

echo "Highest version tag: ${LATEST_TAG}"

if [[ "${VERSION}" != "${LATEST_TAG}" ]]; then
  echo "Current version ${VERSION} is NOT the highest version."
  echo "Stable tag will NOT be updated."
  exit 0
fi

echo "Current version ${VERSION} IS the highest version."
echo "Updating 'stable' tag..."

git tag -d stable 2>/dev/null || true
git push origin :refs/tags/stable || true

git tag stable "$GITHUB_SHA"
git push origin stable

echo "Stable tag updated to ${VERSION}."
