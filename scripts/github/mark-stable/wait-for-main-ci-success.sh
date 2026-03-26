#!/usr/bin/env bash
set -euo pipefail

SHA="${GITHUB_SHA}"
API_URL="https://api.github.com/repos/${GITHUB_REPOSITORY}/actions/workflows/ci.yml/runs?head_sha=${SHA}&event=push&per_page=20"
WAIT_INTERVAL_SECONDS=20
MAX_ATTEMPTS=990 # 5 hours 30 minutes max wait

STATUS=""
CONCLUSION=""

echo "Waiting for CI on main for ${SHA} (up to 5 hours 30 minutes)..."
for attempt in $(seq 1 "${MAX_ATTEMPTS}"); do
  RESPONSE="$(curl -fsSL \
    -H "Authorization: Bearer ${GH_TOKEN}" \
    -H "Accept: application/vnd.github+json" \
    "${API_URL}")"

  STATUS="$(printf '%s' "${RESPONSE}" | jq -r '.workflow_runs[] | select(.head_branch=="main") | .status' | head -n1)"
  CONCLUSION="$(printf '%s' "${RESPONSE}" | jq -r '.workflow_runs[] | select(.head_branch=="main") | .conclusion' | head -n1)"

  if [[ -n "${STATUS}" ]]; then
    echo "CI status=${STATUS} conclusion=${CONCLUSION:-none} (attempt ${attempt}/${MAX_ATTEMPTS})"
  else
    echo "No CI run for main found yet (attempt ${attempt}/${MAX_ATTEMPTS})"
  fi

  if [[ "${STATUS}" == "completed" ]]; then
    if [[ "${CONCLUSION}" == "success" ]]; then
      echo "CI succeeded for ${SHA}."
      break
    fi
    echo "CI failed for ${SHA} (conclusion=${CONCLUSION})."
    exit 1
  fi

  sleep "${WAIT_INTERVAL_SECONDS}"
done

if [[ "${STATUS}" != "completed" || "${CONCLUSION}" != "success" ]]; then
  echo "Timed out waiting for successful CI on main for ${SHA}."
  exit 1
fi
