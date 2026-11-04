#!/usr/bin/env bash
# Param: WORKFLOW_RUN_SHA  commit the "Mark stable commit" run tagged; empty on a scheduled or
#                          manual rebuild, which publishes the newest vX.Y.Z release on origin/main
#                          and the release the git tag stable marks
# Output: releases=<JSON list of {"sha", "version", "aliases"}> in GITHUB_OUTPUT; aliases are the
#         moving tags a release takes besides <version> and <version>.<unix-ts>
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# shellcheck source=scripts/build/base.sh
source "${SCRIPT_DIR}/../../build/base.sh"

: "${WORKFLOW_RUN_SHA?WORKFLOW_RUN_SHA must be set, empty for a rebuild}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT must be set}"

RELEASE_TAG='^v[0-9]+\.[0-9]+\.[0-9]+$'

release_at() {
  local listed tag
  listed="$(git tag --points-at "$1" --sort=-v:refname)"
  tag="$(grep -m1 -E "${RELEASE_TAG}" <<< "${listed}" || true)"
  echo "${tag#v}"
}

newest_of() {
  local prefix="$1" version
  for version in "${RELEASES[@]}"; do
    if [[ "${version}." == "${prefix}."* ]]; then
      echo "${version}"
      return 0
    fi
  done
}

aliases_of() {
  local version="$1" prefix
  local -a aliases=()
  if [[ "${version}" == "${RELEASES[0]}" ]]; then
    aliases+=(latest)
  fi
  while read -r prefix; do
    if [[ "${prefix}" != "${version}" && "$(newest_of "${prefix}")" == "${version}" ]]; then
      aliases+=("${prefix}")
    fi
  done < <(version_prefixes "${version}")
  if [[ "${version}" == "${STABLE}" ]]; then
    aliases+=(stable)
  fi
  echo "${aliases[*]}"
}

listed="$(git tag --merged origin/main --sort=-v:refname)"
mapfile -t tags < <(grep -E "${RELEASE_TAG}" <<< "${listed}")
RELEASES=("${tags[@]#v}")

STABLE=""
stable_sha="$(git rev-parse -q --verify 'refs/tags/stable^{commit}' || true)"
if [[ -n "${stable_sha}" ]]; then
  STABLE="$(release_at "${stable_sha}")"
fi

targets=()
if [[ -n "${WORKFLOW_RUN_SHA}" ]]; then
  version="$(release_at "${WORKFLOW_RUN_SHA}")"
  if ! git merge-base --is-ancestor "${WORKFLOW_RUN_SHA}" origin/main; then
    echo "${WORKFLOW_RUN_SHA} is not on origin/main. Skipping publish."
  elif [[ -z "${version}" ]]; then
    echo "No vX.Y.Z tag found for ${WORKFLOW_RUN_SHA}. Skipping publish."
  else
    targets+=("${version}")
  fi
else
  ((${#RELEASES[@]} > 0)) || { echo "No vX.Y.Z tag is reachable from origin/main." >&2; exit 1; }
  targets+=("${RELEASES[0]}")
  if [[ -z "${STABLE}" ]]; then
    echo "The git tag stable marks no vX.Y.Z release; the stable image stays where it is."
  elif [[ "${STABLE}" != "${RELEASES[0]}" ]]; then
    targets+=("${STABLE}")
  fi
fi

json=""
for version in "${targets[@]}"; do
  sha="$(git rev-parse "v${version}^{commit}")"
  moving="$(aliases_of "${version}")"
  echo "Publishing ${version} at ${sha}, moving: ${moving}"
  json+="${json:+,}{\"sha\":\"${sha}\",\"version\":\"${version}\",\"aliases\":\"${moving}\"}"
done

echo "releases=[${json}]" >> "${GITHUB_OUTPUT}"
