#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command helm
require_command xmllint
require_command python3

info "Checking shell syntax"
for script in "${SCRIPT_DIR}"/*.sh "${REPO_ROOT}/load-tests/jmeter/run.sh"; do
  bash -n "$script"
done

info "Checking JMeter XML"
xmllint --noout "${REPO_ROOT}/load-tests/jmeter/experiment-1.jmx"
xmllint --noout "${REPO_ROOT}/load-tests/jmeter/request-fragment.jmx"
xmllint --noout "${REPO_ROOT}/load-tests/jmeter/gui-500rpm.jmx"

info "Linting and rendering Helm chart"
helm lint "$CHART_DIR"
rendered_file="$(mktemp -t solventa-exp1-rendered).yaml"
trap 'rm -f "$rendered_file"' EXIT
helm template "$RELEASE_NAME" "$CHART_DIR" --namespace "$NAMESPACE" >"$rendered_file"

if command -v kubeconform >/dev/null 2>&1; then
  kubeconform -strict -summary "$rendered_file"
else
  info "kubeconform not installed; skipped offline Kubernetes schema validation"
fi

if command -v shellcheck >/dev/null 2>&1; then
  shellcheck -x -P "$SCRIPT_DIR" "${SCRIPT_DIR}"/*.sh "${REPO_ROOT}/load-tests/jmeter/run.sh"
else
  info "shellcheck not installed; skipped static shell analysis"
fi

info "Checking evidence analyzer"
python3 "${SCRIPT_DIR}/analyze.py" --self-test

info "Static validation completed"
