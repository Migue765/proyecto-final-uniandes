#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command docker
require_command git
require_command kubectl
verify_aws_identity
load_tf_outputs
configure_eks_context

[[ -z "$(git -C "$REPO_ROOT" status --porcelain -- services load-tests)" ]] \
  || fail "Refusing evidence runs while services/ or load-tests/ has uncommitted changes"

RUN_ID="${RUN_ID:-exp1-local-$(date -u +%Y%m%dT%H%M%SZ)}"
RUNNER_IMAGE="${RUNNER_IMAGE:-solventa/jmeter-exp1:5.6.3}"
RUNNER_PLATFORM="${RUNNER_PLATFORM:-linux/amd64}"
CREDENTIAL_MARGIN_SECONDS="${CREDENTIAL_MARGIN_SECONDS:-300}"
WARMUP_SECONDS="${WARMUP_SECONDS:-300}"
MEASURED_SECONDS="${MEASURED_SECONDS:-1800}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-300}"
POST_COOLDOWN_OBSERVATION_SECONDS="${POST_COOLDOWN_OBSERVATION_SECONDS:-30}"
validate_safe_id "$RUN_ID"
[[ "$RUNNER_PLATFORM" == "linux/amd64" ]] || fail "RUNNER_PLATFORM must be linux/amd64"
for duration in "$CREDENTIAL_MARGIN_SECONDS" "$WARMUP_SECONDS" "$MEASURED_SECONDS" "$COOLDOWN_SECONDS" "$POST_COOLDOWN_OBSERVATION_SECONDS"; do
  [[ "$duration" =~ ^[1-9][0-9]*$ ]] || fail "Runner durations and credential margin must be positive integers"
done
required_credential_seconds=$((WARMUP_SECONDS + MEASURED_SECONDS + COOLDOWN_SECONDS + POST_COOLDOWN_OBSERVATION_SECONDS + CREDENTIAL_MARGIN_SECONDS))

api_base_url="${API_BASE_URL:-$(tf_text_first api_gateway_invoke_url 2>/dev/null || true)}"
[[ -n "$api_base_url" ]] || fail "Missing Terraform output api_gateway_invoke_url"
validate_http_url "$api_base_url"
if [[ "$api_base_url" == */api/v1/cotizaciones ]]; then
  target_url="$api_base_url"
else
  target_url="${api_base_url%/}/api/v1/cotizaciones"
fi
target_host="$(url_host "$target_url")"

mkdir -p "$RESULTS_DIR"
monitor_pid=""
cleanup() {
  if [[ -n "$monitor_pid" ]]; then
    kill "$monitor_pid" >/dev/null 2>&1 || true
    wait "$monitor_pid" >/dev/null 2>&1 || true
  fi
  clear_aws_process_credentials
}
trap cleanup EXIT INT TERM

refresh_runner_credentials() {
  local now_epoch remaining_seconds
  clear_aws_process_credentials
  export_aws_process_credentials
  now_epoch="$(date -u +%s)"
  remaining_seconds=$((AWS_CREDENTIAL_EXPIRATION_EPOCH - now_epoch))
  (( remaining_seconds >= required_credential_seconds )) \
    || fail "Temporary AWS credentials expire too soon for one complete run plus the ${CREDENTIAL_MARGIN_SECONDS}s margin; refresh aws login"
}

info "Building the pinned JMeter 5.6.3 runner"
source_revision="$(git -C "$REPO_ROOT" rev-parse --short=12 HEAD)"
docker build \
  --platform "$RUNNER_PLATFORM" \
  --build-arg "SOURCE_REVISION=${source_revision}" \
  --tag "$RUNNER_IMAGE" \
  "${REPO_ROOT}/load-tests/jmeter"

TARGET_URL="$target_url" \
ALLOWED_TARGET_HOSTS="$target_host" \
AUTH_MODE=aws_iam \
SKIP_CONTEXT_UPDATE=true \
"${SCRIPT_DIR}/smoke.sh"

RUN_ID="$RUN_ID" \
MONITOR_DURATION_SECONDS=7500 \
SKIP_CONTEXT_UPDATE=true \
"${SCRIPT_DIR}/monitor.sh" &
monitor_pid=$!

info "Starting three end-to-end API Gateway runs with warm-up, measured step, and cooldown"
for run_number in 1 2 3; do
  refresh_runner_credentials
  info "Starting isolated runner container ${run_number}/3 with freshly exported temporary credentials"
  docker run --rm \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges \
    --user "$(id -u):$(id -g)" \
    --tmpfs /tmp:rw,noexec,nosuid,size=256m \
    --volume "${RESULTS_DIR}:/work/results" \
    --env "RUN_ID=${RUN_ID}" \
    --env RUNS=3 \
    --env "RUN_START=${run_number}" \
    --env "RUN_END=${run_number}" \
    --env "WARMUP_SECONDS=${WARMUP_SECONDS}" \
    --env "MEASURED_SECONDS=${MEASURED_SECONDS}" \
    --env "COOLDOWN_SECONDS=${COOLDOWN_SECONDS}" \
    --env "POST_COOLDOWN_OBSERVATION_SECONDS=${POST_COOLDOWN_OBSERVATION_SECONDS}" \
    --env "TARGET_URL=${target_url}" \
    --env "ALLOWED_TARGET_HOSTS=${target_host}" \
    --env "RUNNER_IMAGE_REF=${RUNNER_IMAGE}" \
    --env AUTH_MODE=aws_iam \
    --env "AWS_REGION=${AWS_REGION}" \
    --env AWS_ACCESS_KEY_ID \
    --env AWS_SECRET_ACCESS_KEY \
    --env AWS_SESSION_TOKEN \
    "$RUNNER_IMAGE"
done

final_snapshot_dir="${RESULTS_DIR}/${RUN_ID}/k8s"
mkdir -p "$final_snapshot_dir"
{
  printf '===== %s final post-cooldown snapshot =====\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  kubectl -n "$NAMESPACE" get hpa,deploy,pods -o wide
  kubectl -n "$NAMESPACE" top pods --containers
} >"${final_snapshot_dir}/final-post-cooldown.txt" 2>&1 || true

kill "$monitor_pid" >/dev/null 2>&1 || true
wait "$monitor_pid" >/dev/null 2>&1 || true
monitor_pid=""

SOURCE_RUN_ID="$RUN_ID" "${SCRIPT_DIR}/analyze.sh"
info "Local load execution complete: ${RESULTS_DIR}/${RUN_ID}"
