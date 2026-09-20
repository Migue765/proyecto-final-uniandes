#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command kubectl
ADMIN_DB_SECRET_NAME="${ADMIN_DB_SECRET_NAME:-solventa-exp1-db-admin}"
RUNTIME_DB_SECRET_NAME="${RUNTIME_DB_SECRET_NAME:-solventa-exp1-db-runtime}"
REDIS_SECRET_NAME="${REDIS_SECRET_NAME:-solventa-exp1-redis-runtime}"
SEED_JOB_NAME="${SEED_JOB_NAME:-${RELEASE_NAME}-database-seed}"
readonly DB_SECRET_KEY=database-url
readonly REDIS_SECRET_KEY=redis-url
validate_namespace "$NAMESPACE"
for secret_name in "$ADMIN_DB_SECRET_NAME" "$RUNTIME_DB_SECRET_NAME" "$REDIS_SECRET_NAME"; do
  validate_safe_id "$secret_name"
done
validate_safe_id "$SEED_JOB_NAME"

CLEANUP_CONTEXT_READY=false
cleanup_sensitive_seed_material() {
  local exit_code=$?
  trap - EXIT INT TERM
  set +e

  if [[ "$CLEANUP_CONTEXT_READY" == "true" ]] \
    && delete_sensitive_seed_material "$NAMESPACE" "$SEED_JOB_NAME" "$ADMIN_DB_SECRET_NAME"; then
    info "Removed short-lived database seed credentials"
  fi

  exit "$exit_code"
}

# Register cleanup before any fallible deployment validation. It becomes active
# only after this script has selected and verified the intended EKS context.
trap cleanup_sensitive_seed_material EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

require_command helm
require_command jq
verify_aws_identity
load_tf_outputs
configure_eks_context
ensure_namespace
CLEANUP_CONTEXT_READY=true

# Remove residue from an interrupted prior attempt before doing any new work.
delete_sensitive_seed_material "$NAMESPACE" "$SEED_JOB_NAME" "$ADMIN_DB_SECRET_NAME" \
  || fail "Unable to remove stale database seed material"

IMAGE_TAG="${IMAGE_TAG:-}"
[[ "$IMAGE_TAG" =~ ^[0-9a-f]{12,40}$ ]] || fail "Set IMAGE_TAG to the immutable Git SHA tag already pushed to ECR"

quotation_repository="${QUOTATION_IMAGE_REPOSITORY:-$(tf_map_text ecr_repository_urls quotation quotation-service quote 2>/dev/null || true)}"
profile_repository="${PROFILE_IMAGE_REPOSITORY:-$(tf_map_text ecr_repository_urls profile profile-service 2>/dev/null || true)}"
rds_endpoint="${RDS_ENDPOINT:-$(tf_text_first rds_endpoint database_endpoint 2>/dev/null || true)}"
redis_endpoint="${REDIS_ENDPOINT:-$(tf_text_first redis_primary_endpoint redis_endpoint elasticache_endpoint 2>/dev/null || true)}"

[[ -n "$quotation_repository" ]] || fail "Missing quotation ECR repository output"
[[ -n "$profile_repository" ]] || fail "Missing profile ECR repository output"
[[ -n "$rds_endpoint" ]] || fail "Missing RDS endpoint output"
[[ -n "$redis_endpoint" ]] || fail "Missing Redis endpoint output"

rds_host="${rds_endpoint%%:*}"
redis_host="${redis_endpoint%%:*}"
[[ "$rds_host" =~ ^[A-Za-z0-9.-]+$ ]] || fail "Invalid RDS endpoint"
[[ "$redis_host" =~ ^[A-Za-z0-9.-]+$ ]] || fail "Invalid Redis endpoint"

nlb_source_cidrs_json="$(tf_json_first internal_nlb_source_cidrs 2>/dev/null || true)"
jq -e 'type == "array" and length > 0 and all(.[]; test("^[0-9]{1,3}(\\.[0-9]{1,3}){3}/32$"))' \
  <<<"$nlb_source_cidrs_json" >/dev/null || fail "Invalid internal_nlb_source_cidrs output"

if [[ "${INSTALL_METRICS_SERVER:-true}" == "true" ]]; then
  info "Installing/upgrading metrics-server 3.14.0"
  helm repo add metrics-server https://kubernetes-sigs.github.io/metrics-server/ --force-update >/dev/null
  helm repo update metrics-server >/dev/null
  helm upgrade --install metrics-server metrics-server/metrics-server \
    --namespace kube-system \
    --version 3.14.0 \
    --values "${REPO_ROOT}/deploy/metrics-server/values.yaml" \
    --atomic \
    --timeout 10m \
    --wait
fi

# Defaults aligned with the service config defaults and with values.yaml. The
# previous 150000 was an uncalibrated placeholder: measured at ~850 ns and
# ~1020 ns per iteration, it cost 281 ms of CPU per quotation and made the
# p95 <= 250 ms target of ASR-ESC-01 unreachable regardless of replica count.
QUOTE_CPU_ITERATIONS="${QUOTE_CPU_ITERATIONS:-1200}"
PROFILE_CPU_ITERATIONS="${PROFILE_CPU_ITERATIONS:-800}"
[[ "$QUOTE_CPU_ITERATIONS" =~ ^[1-9][0-9]{0,6}$ && "$QUOTE_CPU_ITERATIONS" -le 1000000 ]] \
  || fail "QUOTE_CPU_ITERATIONS must be between 1 and 1000000"
[[ "$PROFILE_CPU_ITERATIONS" =~ ^[1-9][0-9]{0,6}$ && "$PROFILE_CPU_ITERATIONS" -le 1000000 ]] \
  || fail "PROFILE_CPU_ITERATIONS must be between 1 and 1000000"

info "Synchronizing runtime credentials and short-lived seed credentials"
PRESERVE_ADMIN_DB_SECRET=true \
ADMIN_DB_SECRET_NAME="$ADMIN_DB_SECRET_NAME" \
RUNTIME_DB_SECRET_NAME="$RUNTIME_DB_SECRET_NAME" \
REDIS_SECRET_NAME="$REDIS_SECRET_NAME" \
SEED_JOB_NAME="$SEED_JOB_NAME" \
  "${SCRIPT_DIR}/sync-db-secret.sh"

for secret_name in "$ADMIN_DB_SECRET_NAME" "$RUNTIME_DB_SECRET_NAME" "$REDIS_SECRET_NAME"; do
  kubectl -n "$NAMESPACE" get secret "$secret_name" >/dev/null 2>&1 \
    || fail "Missing required Secret ${NAMESPACE}/${secret_name}"
done

info "Deploying Solventa experiment services"
helm upgrade --install "$RELEASE_NAME" "$CHART_DIR" \
  --namespace "$NAMESPACE" \
  --set-string "quotation.image.repository=${quotation_repository}" \
  --set-string "quotation.image.tag=${IMAGE_TAG}" \
  --set-string "profile.image.repository=${profile_repository}" \
  --set-string "profile.image.tag=${IMAGE_TAG}" \
  --set-string "database.adminSecret.name=${ADMIN_DB_SECRET_NAME}" \
  --set-string "database.adminSecret.key=${DB_SECRET_KEY}" \
  --set-string "database.runtimeSecret.name=${RUNTIME_DB_SECRET_NAME}" \
  --set-string "database.runtimeSecret.key=${DB_SECRET_KEY}" \
  --set-string "database.host=${rds_host}" \
  --set-string "redis.existingSecret.name=${REDIS_SECRET_NAME}" \
  --set-string "redis.existingSecret.key=${REDIS_SECRET_KEY}" \
  --set-string "redis.host=${redis_host}" \
  --set redis.tlsEnabled=true \
  --set-json "networkPolicy.quotationIngressCidrs=${nlb_source_cidrs_json}" \
  --set "quotation.cpuIterations=${QUOTE_CPU_ITERATIONS}" \
  --set "profile.cpuIterations=${PROFILE_CPU_ITERATIONS}" \
  --atomic \
  --timeout 15m \
  --wait

kubectl -n "$NAMESPACE" rollout status deployment/solventa-exp1-quotation --timeout=5m
kubectl -n "$NAMESPACE" rollout status deployment/solventa-exp1-profile --timeout=5m
kubectl -n "$NAMESPACE" rollout status deployment/solventa-exp1-wiremock --timeout=5m
kubectl -n "$NAMESPACE" get deployments,services,hpa

info "Deployment complete; run scripts/experiment-1/smoke.sh before load generation"
