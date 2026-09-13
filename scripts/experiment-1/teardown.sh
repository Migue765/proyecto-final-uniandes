#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

[[ "${CONFIRM_TEARDOWN:-}" == "solventa-exp1" ]] \
  || fail "Refusing teardown. Re-run with CONFIRM_TEARDOWN=solventa-exp1"

require_command helm
require_command kubectl
verify_aws_identity
load_tf_outputs
configure_eks_context

if helm status "$RELEASE_NAME" --namespace "$NAMESPACE" >/dev/null 2>&1; then
  helm uninstall "$RELEASE_NAME" --namespace "$NAMESPACE" --wait
else
  info "Helm release ${RELEASE_NAME} is not installed"
fi

if [[ "${DELETE_DB_SECRET:-false}" == "true" ]]; then
  kubectl -n "$NAMESPACE" delete secret \
    "${ADMIN_DB_SECRET_NAME:-solventa-exp1-db-admin}" \
    "${RUNTIME_DB_SECRET_NAME:-solventa-exp1-db-runtime}" \
    "${REDIS_SECRET_NAME:-solventa-exp1-redis-runtime}" \
    --ignore-not-found
fi

if [[ "${DELETE_NAMESPACE:-false}" == "true" ]]; then
  kubectl delete namespace "$NAMESPACE" --ignore-not-found --wait=true
fi

if [[ "${UNINSTALL_METRICS_SERVER:-false}" == "true" ]]; then
  helm uninstall metrics-server --namespace kube-system --wait
fi

info "Application teardown complete. Terraform-managed AWS infrastructure was not destroyed."
