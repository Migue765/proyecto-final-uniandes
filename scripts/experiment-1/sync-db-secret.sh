#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command kubectl
ADMIN_DB_SECRET_NAME="${ADMIN_DB_SECRET_NAME:-solventa-exp1-db-admin}"
RUNTIME_DB_SECRET_NAME="${RUNTIME_DB_SECRET_NAME:-solventa-exp1-db-runtime}"
REDIS_SECRET_NAME="${REDIS_SECRET_NAME:-solventa-exp1-redis-runtime}"
SEED_JOB_NAME="${SEED_JOB_NAME:-${RELEASE_NAME}-database-seed}"
PRESERVE_ADMIN_DB_SECRET="${PRESERVE_ADMIN_DB_SECRET:-false}"
readonly DB_SECRET_KEY=database-url
readonly REDIS_SECRET_KEY=redis-url
readonly RUNTIME_DB_USER=solventa_runtime
readonly DB_TLS_QUERY='sslmode=verify-full&sslrootcert=%2Fetc%2Fssl%2Fcerts%2Faws-rds-global-bundle.pem'
validate_namespace "$NAMESPACE"
for secret_name in "$ADMIN_DB_SECRET_NAME" "$RUNTIME_DB_SECRET_NAME" "$REDIS_SECRET_NAME"; do
  validate_safe_id "$secret_name"
done
validate_safe_id "$SEED_JOB_NAME"
validate_safe_id "$DB_SECRET_KEY"
validate_safe_id "$REDIS_SECRET_KEY"
[[ "$PRESERVE_ADMIN_DB_SECRET" == "true" || "$PRESERVE_ADMIN_DB_SECRET" == "false" ]] \
  || fail "PRESERVE_ADMIN_DB_SECRET must be true or false"

CLEANUP_CONTEXT_READY=false
cleanup_failed_secret_sync() {
  local exit_code=$?
  trap - EXIT INT TERM
  set +e
  if [[ "$CLEANUP_CONTEXT_READY" == "true" ]]; then
    delete_sensitive_seed_material "$NAMESPACE" "$SEED_JOB_NAME" "$ADMIN_DB_SECRET_NAME" || true
  fi
  exit "$exit_code"
}

# A partially completed sync must never leave the RDS master credential behind.
trap cleanup_failed_secret_sync EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

require_command base64
require_command jq
require_command openssl
verify_aws_identity
load_tf_outputs
configure_eks_context
ensure_namespace
CLEANUP_CONTEXT_READY=true

# Start from a known state if a previous local process was interrupted.
delete_sensitive_seed_material "$NAMESPACE" "$SEED_JOB_NAME" "$ADMIN_DB_SECRET_NAME" \
  || fail "Unable to remove stale database seed material"

DB_NAME="${DB_NAME:-$(tf_text_first rds_database_name 2>/dev/null || printf 'solventa')}"
[[ "$DB_NAME" =~ ^[A-Za-z0-9_-]{1,63}$ ]] || fail "DB_NAME contains unsupported characters"

rds_secret_arn="${RDS_SECRET_ARN:-$(tf_text_first rds_master_secret_arn 2>/dev/null || true)}"
redis_secret_arn="${REDIS_AUTH_SECRET_ARN:-$(tf_text_first redis_auth_secret_arn 2>/dev/null || true)}"
rds_endpoint="${RDS_ENDPOINT:-$(tf_text_first rds_endpoint 2>/dev/null || true)}"
redis_endpoint="${REDIS_ENDPOINT:-$(tf_text_first redis_primary_endpoint 2>/dev/null || true)}"
[[ "$rds_secret_arn" == arn:aws:secretsmanager:* ]] || fail "Missing or invalid rds_master_secret_arn"
[[ "$redis_secret_arn" == arn:aws:secretsmanager:* ]] || fail "Missing or invalid redis_auth_secret_arn"
[[ -n "$rds_endpoint" && -n "$redis_endpoint" ]] || fail "Missing RDS or Redis endpoint output"

rds_host="${rds_endpoint%%:*}"
redis_host="${redis_endpoint%%:*}"
rds_port="${RDS_PORT:-$(tf_text_first rds_port 2>/dev/null || printf '5432')}"
redis_port="${REDIS_PORT:-$(tf_text_first redis_port 2>/dev/null || printf '6379')}"
[[ "$rds_host" =~ ^[A-Za-z0-9.-]+$ && "$redis_host" =~ ^[A-Za-z0-9.-]+$ ]] || fail "Database/cache endpoint host is invalid"
[[ "$rds_port" =~ ^[0-9]{1,5}$ && "$redis_port" =~ ^[0-9]{1,5}$ ]] || fail "Database/cache port is invalid"

# Secret material remains only in process memory and stdin pipes to the
# Kubernetes API. It is never passed in command arguments, printed, or saved.
set +x
rds_secret_json="$(aws_cli secretsmanager get-secret-value \
  --secret-id "$rds_secret_arn" \
  --query SecretString \
  --output text)"
admin_database_url="$(jq -er \
  --arg host "$rds_host" \
  --arg port "$rds_port" \
  --arg database "$DB_NAME" \
  --arg tls_query "$DB_TLS_QUERY" \
  '(.username // error("missing username")) as $username |
   (.password // error("missing password")) as $password |
   "postgresql://\($username | @uri):\($password | @uri)@\($host):\($port)/\($database)?\($tls_query)"' \
  <<<"$rds_secret_json")"
unset rds_secret_json

printf '%s' "$admin_database_url" \
  | kubectl -n "$NAMESPACE" create secret generic "$ADMIN_DB_SECRET_NAME" \
      --from-file="${DB_SECRET_KEY}=/dev/stdin" \
      --dry-run=client \
      --output yaml \
  | kubectl apply -f - >/dev/null
unset admin_database_url

if runtime_secret_json="$(kubectl -n "$NAMESPACE" get secret "$RUNTIME_DB_SECRET_NAME" -o json 2>/dev/null)"; then
  jq -e '.data["database-url"] and .data.username and .data.password' <<<"$runtime_secret_json" >/dev/null \
    || fail "Existing runtime DB Secret is incomplete; refusing implicit rotation"
  runtime_username="$(jq -er '.data.username | @base64d' <<<"$runtime_secret_json")"
  runtime_password="$(jq -er '.data.password | @base64d' <<<"$runtime_secret_json")"
  unset runtime_secret_json
  [[ "$runtime_username" == "$RUNTIME_DB_USER" ]] || fail "Existing runtime DB username is not ${RUNTIME_DB_USER}"
else
  runtime_username="$RUNTIME_DB_USER"
  runtime_password="$(openssl rand -base64 36 | tr -d '\n')"
fi

runtime_database_url="$(printf '{"username":"%s","password":"%s"}\n' "$runtime_username" "$runtime_password" \
  | jq -er \
      --arg host "$rds_host" \
      --arg port "$rds_port" \
      --arg database "$DB_NAME" \
      --arg tls_query "$DB_TLS_QUERY" \
      '"postgresql://\(.username | @uri):\(.password | @uri)@\($host):\($port)/\($database)?\($tls_query)"')"
runtime_username_b64="$(printf '%s' "$runtime_username" | base64 | tr -d '\n')"
runtime_password_b64="$(printf '%s' "$runtime_password" | base64 | tr -d '\n')"
runtime_url_b64="$(printf '%s' "$runtime_database_url" | base64 | tr -d '\n')"
printf '{"apiVersion":"v1","kind":"Secret","metadata":{"name":"%s","namespace":"%s"},"type":"Opaque","data":{"database-url":"%s","username":"%s","password":"%s"}}\n' \
  "$RUNTIME_DB_SECRET_NAME" "$NAMESPACE" "$runtime_url_b64" "$runtime_username_b64" "$runtime_password_b64" \
  | kubectl apply -f - >/dev/null
unset runtime_password runtime_database_url runtime_password_b64 runtime_url_b64

redis_secret_json="$(aws_cli secretsmanager get-secret-value \
  --secret-id "$redis_secret_arn" \
  --query SecretString \
  --output text)"
redis_url="$(jq -er \
  --arg host "$redis_host" \
  --arg port "$redis_port" \
  '(.auth_token // error("missing auth_token")) as $token |
   "rediss://:\($token | @uri)@\($host):\($port)/0"' \
  <<<"$redis_secret_json")"
unset redis_secret_json
printf '%s' "$redis_url" \
  | kubectl -n "$NAMESPACE" create secret generic "$REDIS_SECRET_NAME" \
      --from-file="${REDIS_SECRET_KEY}=/dev/stdin" \
      --dry-run=client \
      --output yaml \
  | kubectl apply -f - >/dev/null
unset redis_url

for secret_name in "$ADMIN_DB_SECRET_NAME" "$RUNTIME_DB_SECRET_NAME" "$REDIS_SECRET_NAME"; do
  kubectl -n "$NAMESPACE" label secret "$secret_name" \
    app.kubernetes.io/part-of=solventa-exp1 \
    app.kubernetes.io/managed-by=experiment-script \
    --overwrite >/dev/null
done

if [[ "$PRESERVE_ADMIN_DB_SECRET" == "true" ]]; then
  # deploy.sh owns cleanup from this point onward.
  CLEANUP_CONTEXT_READY=false
  trap - EXIT INT TERM
  info "Runtime credentials and short-lived seed credentials synchronized without persisting values"
else
  delete_sensitive_seed_material "$NAMESPACE" "$SEED_JOB_NAME" "$ADMIN_DB_SECRET_NAME" \
    || fail "Unable to remove short-lived database seed credentials"
  CLEANUP_CONTEXT_READY=false
  trap - EXIT INT TERM
  info "Runtime credentials synchronized; short-lived database seed credentials removed"
fi
