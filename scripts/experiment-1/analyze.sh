#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command python3
SOURCE_RUN_ID="${SOURCE_RUN_ID:-}"
[[ -n "$SOURCE_RUN_ID" ]] || fail "Set SOURCE_RUN_ID to the completed local evidence run"
validate_safe_id "$SOURCE_RUN_ID"
[[ -d "${RESULTS_DIR}/${SOURCE_RUN_ID}" ]] || fail "Unknown local run: ${SOURCE_RUN_ID}"

python3 "${SCRIPT_DIR}/analyze.py" \
  --results-root "$RESULTS_DIR" \
  --run-id "$SOURCE_RUN_ID"
