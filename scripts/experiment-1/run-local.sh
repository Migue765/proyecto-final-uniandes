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

# Ignore-file housekeeping does not alter the service images or JMeter plan.
[[ -z "$(git -C "$REPO_ROOT" status --porcelain -- services load-tests ':(exclude)services/.gitignore')" ]] \
  || fail "Refusing evidence runs while services/ or load-tests/ has uncommitted changes"

RUN_ID="${RUN_ID:-exp1-local-$(date -u +%Y%m%dT%H%M%SZ)}"
RUNNER_IMAGE="${RUNNER_IMAGE:-solventa/jmeter-exp1:5.6.3}"
RUNNER_PLATFORM="${RUNNER_PLATFORM:-linux/amd64}"
CREDENTIAL_MARGIN_SECONDS="${CREDENTIAL_MARGIN_SECONDS:-120}"
WARMUP_SECONDS="${WARMUP_SECONDS:-60}"
MEASURED_SECONDS="${MEASURED_SECONDS:-480}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-30}"
POST_COOLDOWN_OBSERVATION_SECONDS="${POST_COOLDOWN_OBSERVATION_SECONDS:-30}"
BASELINE_READY_TIMEOUT_SECONDS="${BASELINE_READY_TIMEOUT_SECONDS:-600}"
BASELINE_READY_INTERVAL_SECONDS="${BASELINE_READY_INTERVAL_SECONDS:-15}"
validate_safe_id "$RUN_ID"
[[ "$RUNNER_PLATFORM" == "linux/amd64" ]] || fail "RUNNER_PLATFORM must be linux/amd64"
for duration in "$CREDENTIAL_MARGIN_SECONDS" "$WARMUP_SECONDS" "$MEASURED_SECONDS" "$COOLDOWN_SECONDS" "$POST_COOLDOWN_OBSERVATION_SECONDS" "$BASELINE_READY_TIMEOUT_SECONDS" "$BASELINE_READY_INTERVAL_SECONDS"; do
  [[ "$duration" =~ ^[1-9][0-9]*$ ]] || fail "Runner durations and credential margin must be positive integers"
done
required_credential_seconds=$((WARMUP_SECONDS + MEASURED_SECONDS + COOLDOWN_SECONDS + POST_COOLDOWN_OBSERVATION_SECONDS + CREDENTIAL_MARGIN_SECONDS))
monitor_duration_seconds=$(((WARMUP_SECONDS + MEASURED_SECONDS + COOLDOWN_SECONDS + POST_COOLDOWN_OBSERVATION_SECONDS) * 3 + BASELINE_READY_TIMEOUT_SECONDS * 2 + 300))

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

wait_for_baseline_capacity() {
  local deadline component resource_name ready
  deadline=$((SECONDS + BASELINE_READY_TIMEOUT_SECONDS))
  while (( SECONDS < deadline )); do
    ready=true
    for component in quotation profile; do
      resource_name="${RELEASE_NAME}-${component}"
      if ! kubectl -n "$NAMESPACE" get deployment "$resource_name" -o json 2>/dev/null \
        | jq -e '
          (.spec.replicas // 0) == 2 and
          (.status.readyReplicas // 0) == 2 and
          (.status.availableReplicas // 0) == 2
        ' >/dev/null; then
        ready=false
      fi
      if ! kubectl -n "$NAMESPACE" get hpa "$resource_name" -o json 2>/dev/null \
        | jq -e '
          (.status.currentReplicas // 0) == 2 and
          (.status.desiredReplicas // 0) == 2
        ' >/dev/null; then
        ready=false
      fi
    done
    if [[ "$ready" == "true" ]]; then
      info "Baseline capacity restored: quotation and profile have two Ready replicas"
      return 0
    fi
    sleep "$BASELINE_READY_INTERVAL_SECONDS"
  done
  kubectl -n "$NAMESPACE" get hpa,deploy,pods -o wide >&2 || true
  fail "Baseline capacity was not restored within ${BASELINE_READY_TIMEOUT_SECONDS}s"
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

wait_for_baseline_capacity

RUN_ID="$RUN_ID" \
MONITOR_DURATION_SECONDS="$monitor_duration_seconds" \
SKIP_CONTEXT_UPDATE=true \
"${SCRIPT_DIR}/monitor.sh" &
monitor_pid=$!

info "Starting three end-to-end API Gateway runs with warm-up, measured step, and cooldown"
for run_number in 1 2 3; do
  if (( run_number > 1 )); then
    wait_for_baseline_capacity
  fi
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
