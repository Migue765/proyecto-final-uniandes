#!/usr/bin/env bash

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/../.." && pwd)"

AWS_PROFILE="${AWS_PROFILE:-solventa-lab}"
AWS_REGION="${AWS_REGION:-us-east-1}"
EXPECTED_AWS_ACCOUNT_ID="${EXPECTED_AWS_ACCOUNT_ID:-969325258550}"
NAMESPACE="${NAMESPACE:-solventa-exp1}"
RELEASE_NAME="${RELEASE_NAME:-solventa-exp1}"
TF_DIR="${TF_DIR:-${REPO_ROOT}/infra/terraform/exp1}"
CHART_DIR="${CHART_DIR:-${REPO_ROOT}/deploy/helm/solventa-exp1}"
RESULTS_DIR="${RESULTS_DIR:-${REPO_ROOT}/load-tests/results}"
TF_OUTPUTS_JSON=""

if [[ -z "${AWS_BIN:-}" ]]; then
  if [[ -x /opt/homebrew/bin/aws ]]; then
    AWS_BIN=/opt/homebrew/bin/aws
  else
    AWS_BIN="$(command -v aws || true)"
  fi
fi

# kubectl's EKS exec credential entry invokes the command name `aws`. Ensure it
# resolves to the same AWS CLI binary whose login session is validated below.
if [[ -n "$AWS_BIN" && -x "$AWS_BIN" ]]; then
  AWS_BIN_DIR="$(cd -- "$(dirname -- "$AWS_BIN")" && pwd)"
  export PATH="${AWS_BIN_DIR}:${PATH}"
fi

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

info() {
  printf '==> %s\n' "$*"
}

warn() {
  printf 'WARNING: %s\n' "$*" >&2
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

validate_safe_id() {
  [[ "$1" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || fail "Unsafe identifier: $1"
}

validate_namespace() {
  [[ "$1" =~ ^[a-z0-9]([-a-z0-9]*[a-z0-9])?$ ]] || fail "Invalid Kubernetes namespace: $1"
}

delete_sensitive_seed_material() {
  local namespace="$1"
  local seed_job_name="$2"
  local admin_secret_name="$3"
  local cleanup_failed=false

  validate_namespace "$namespace"
  validate_safe_id "$seed_job_name"
  validate_safe_id "$admin_secret_name"

  # Delete workload objects first so no running container retains the injected
  # master credential after its Kubernetes Secret is removed.
  kubectl -n "$namespace" delete job "$seed_job_name" \
    --ignore-not-found --cascade=foreground --wait=true --timeout=30s >/dev/null 2>&1 \
    || cleanup_failed=true
  kubectl -n "$namespace" delete pod \
    --selector app.kubernetes.io/component=database-seed \
    --ignore-not-found --wait=true --timeout=30s >/dev/null 2>&1 \
    || cleanup_failed=true
  kubectl -n "$namespace" delete secret "$admin_secret_name" \
    --ignore-not-found --wait=true --timeout=30s >/dev/null 2>&1 \
    || cleanup_failed=true

  if [[ "$cleanup_failed" == "true" ]]; then
    warn "Could not fully remove database seed material from namespace ${namespace}"
    return 1
  fi
}

validate_http_url() {
  [[ "$1" =~ ^https?://[^/?#[:space:]]+(/[^[:space:]]*)?$ ]] || fail "Expected an absolute HTTP(S) URL without whitespace"
}

url_host() {
  local authority="${1#*://}"
  authority="${authority%%/*}"
  printf '%s\n' "${authority%%:*}"
}

require_allowed_target() {
  local target_url="$1"
  local allowed_hosts="$2"
  local host
  validate_http_url "$target_url"
  host="$(url_host "$target_url")"
  [[ ",${allowed_hosts}," == *",${host},"* ]] || fail "Target host '${host}' is not in ALLOWED_TARGET_HOSTS"
}

aws_cli() {
  [[ -n "$AWS_BIN" && -x "$AWS_BIN" ]] || fail "AWS CLI not found; set AWS_BIN explicitly"
  "$AWS_BIN" --profile "$AWS_PROFILE" --region "$AWS_REGION" "$@"
}

verify_aws_identity() {
  local account_id arn expected_arn
  account_id="$(aws_cli sts get-caller-identity --query Account --output text)" \
    || fail "AWS session unavailable. Run: /opt/homebrew/bin/aws login --profile ${AWS_PROFILE} --region ${AWS_REGION}"
  arn="$(aws_cli sts get-caller-identity --query Arn --output text)"
  expected_arn="arn:aws:iam::${EXPECTED_AWS_ACCOUNT_ID}:user/solventa-terraform-operator"
  [[ "$account_id" == "$EXPECTED_AWS_ACCOUNT_ID" ]] || fail "AWS account mismatch: expected ${EXPECTED_AWS_ACCOUNT_ID}, got ${account_id}"
  [[ "$arn" == "$expected_arn" ]] \
    || fail "Unexpected AWS principal: expected ${expected_arn}, got ${arn}"
  info "AWS identity verified: ${expected_arn}"
}

export_aws_process_credentials() {
  local credential_json access_key secret_key session_token expiration_epoch
  require_command jq
  set +x
  credential_json="$(aws_cli configure export-credentials --format process)" \
    || fail "Unable to export temporary AWS credentials for ${AWS_PROFILE}"
  access_key="$(jq -er '.AccessKeyId | select(type == "string" and length > 0)' <<<"$credential_json")"
  secret_key="$(jq -er '.SecretAccessKey | select(type == "string" and length > 0)' <<<"$credential_json")"
  session_token="$(jq -er '.SessionToken | select(type == "string" and length > 0)' <<<"$credential_json")"
  expiration_epoch="$(jq -er '.Expiration | select(type == "string") | sub("\\.[0-9]+Z$"; "Z") | fromdateiso8601' <<<"$credential_json")" \
    || fail "Exported AWS credentials do not include a parseable expiration"
  export AWS_ACCESS_KEY_ID="$access_key"
  export AWS_SECRET_ACCESS_KEY="$secret_key"
  export AWS_SESSION_TOKEN="$session_token"
  export AWS_CREDENTIAL_EXPIRATION_EPOCH="$expiration_epoch"
  unset credential_json
}

clear_aws_process_credentials() {
  unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN AWS_CREDENTIAL_EXPIRATION_EPOCH
}

load_tf_outputs() {
  require_command terraform
  require_command jq
  [[ -d "$TF_DIR" ]] || fail "Terraform directory not found: ${TF_DIR}"
  TF_OUTPUTS_JSON="$(terraform -chdir="$TF_DIR" output -json)" \
    || fail "Unable to read Terraform outputs from ${TF_DIR}"
}

tf_text_first() {
  local key value
  for key in "$@"; do
    value="$(jq -er --arg key "$key" '.[$key].value | select(type == "string" and length > 0)' <<<"$TF_OUTPUTS_JSON" 2>/dev/null || true)"
    if [[ -n "$value" ]]; then
      printf '%s\n' "$value"
      return 0
    fi
  done
  return 1
}

tf_json_first() {
  local key value
  for key in "$@"; do
    value="$(jq -cer --arg key "$key" '.[$key].value | select(. != null)' <<<"$TF_OUTPUTS_JSON" 2>/dev/null || true)"
    if [[ -n "$value" ]]; then
      printf '%s\n' "$value"
      return 0
    fi
  done
  return 1
}

tf_map_text() {
  local output_name="$1"
  shift
  local map_key value
  for map_key in "$@"; do
    value="$(jq -er --arg output "$output_name" --arg key "$map_key" '.[$output].value[$key] | select(type == "string" and length > 0)' <<<"$TF_OUTPUTS_JSON" 2>/dev/null || true)"
    if [[ -n "$value" ]]; then
      printf '%s\n' "$value"
      return 0
    fi
  done
  return 1
}

configure_eks_context() {
  local cluster_name
  cluster_name="${EKS_CLUSTER_NAME:-$(tf_text_first eks_cluster_name cluster_name 2>/dev/null || true)}"
  [[ -n "$cluster_name" ]] || fail "Missing EKS cluster output (eks_cluster_name or cluster_name)"
  aws_cli eks update-kubeconfig \
    --name "$cluster_name" \
    --alias "${cluster_name}-${AWS_PROFILE}" >/dev/null
  info "Kubernetes context configured for ${cluster_name}"
}

ensure_namespace() {
  validate_namespace "$NAMESPACE"
  if ! kubectl get namespace "$NAMESPACE" >/dev/null 2>&1; then
    kubectl create namespace "$NAMESPACE" >/dev/null
  fi
}
