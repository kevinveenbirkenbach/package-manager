#!/usr/bin/env bash
set -euo pipefail

: "${OWNER:?OWNER must be set}"
: "${VERSION:?VERSION must be set}"
: "${IS_STABLE:?IS_STABLE must be set}"

bash scripts/build/publish.sh
