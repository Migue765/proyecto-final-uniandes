#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command curl
require_command jq

AUTH_MODE="${AUTH_MODE:-aws_iam}"
[[ "$AUTH_MODE" =~ ^(aws_iam|none)$ ]] || fail "AUTH_MODE must be aws_iam or none"

if [[ "${SKIP_CONTEXT_UPDATE:-false}" != "true" ]]; then
  verify_aws_identity
  load_tf_outputs
fi

response_file="$(mktemp -t solventa-smoke-response)"
cleanup() {
  rm -f "$response_file"
}
trap cleanup EXIT INT TERM

if [[ -n "${TARGET_URL:-}" ]]; then
  ALLOWED_TARGET_HOSTS="${ALLOWED_TARGET_HOSTS:-}"
  [[ -n "$ALLOWED_TARGET_HOSTS" ]] || fail "Set ALLOWED_TARGET_HOSTS when TARGET_URL is provided"
  require_allowed_target "$TARGET_URL" "$ALLOWED_TARGET_HOSTS"
  target_url="$TARGET_URL"
else
  api_base_url="$(tf_text_first api_gateway_invoke_url 2>/dev/null || true)"
  [[ -n "$api_base_url" ]] || fail "Missing Terraform output api_gateway_invoke_url"
  validate_http_url "$api_base_url"
  if [[ "$api_base_url" == */api/v1/cotizaciones ]]; then
    target_url="$api_base_url"
  else
    target_url="${api_base_url%/}/api/v1/cotizaciones"
  fi
fi

request_body="$(jq -cn \
  --arg partner_ref partner-01 \
  --arg profile_ref profile-00000000-0000-4000-8000-000000000101 \
  '{partner_ref: $partner_ref, profile_ref: $profile_ref}')"

target_host="$(url_host "$target_url")"
if [[ "$AUTH_MODE" == "aws_iam" ]]; then
  [[ "$target_url" == https://* ]] || fail "AWS IAM smoke target must use HTTPS"
  [[ "$target_host" == *.execute-api."${AWS_REGION}".amazonaws.com ]] \
    || fail "AWS IAM smoke target must be API Gateway in ${AWS_REGION}"
  curl --help all | grep -q -- '--aws-sigv4' || fail "This curl build does not support --aws-sigv4"
  if [[ -z "${AWS_ACCESS_KEY_ID:-}" || -z "${AWS_SECRET_ACCESS_KEY:-}" || -z "${AWS_SESSION_TOKEN:-}" ]]; then
    export_aws_process_credentials
  fi
  [[ "$AWS_ACCESS_KEY_ID" =~ ^[A-Z0-9]+$ ]] || fail "Temporary AWS access key format is invalid"
  [[ "$AWS_SECRET_ACCESS_KEY" =~ ^[A-Za-z0-9/+=]+$ ]] || fail "Temporary AWS secret key format is invalid"
  [[ "$AWS_SESSION_TOKEN" =~ ^[A-Za-z0-9/+=_.-]+$ ]] || fail "Temporary AWS session token format is invalid"
  set +x
  http_status="$(
    printf 'user = "%s:%s"\nheader = "X-Amz-Security-Token: %s"\n' \
      "$AWS_ACCESS_KEY_ID" "$AWS_SECRET_ACCESS_KEY" "$AWS_SESSION_TOKEN" \
      | curl --config - \
          --aws-sigv4 "aws:amz:${AWS_REGION}:execute-api" \
          --silent \
          --show-error \
          --connect-timeout 2 \
          --max-time 10 \
          --retry 0 \
          --output "$response_file" \
          --write-out '%{http_code}' \
          --request POST \
          --header 'Accept: application/json' \
          --header 'Content-Type: application/json' \
          --data "$request_body" \
          "$target_url"
  )"
else
  [[ "${VALIDATION_MODE:-false}" == "true" ]] || fail "AUTH_MODE=none is allowed only in VALIDATION_MODE"
  [[ "$target_host" == "127.0.0.1" || "$target_host" == "localhost" ]] \
    || fail "Unsigned smoke tests are restricted to localhost"
  http_status="$(curl \
    --silent \
    --show-error \
    --connect-timeout 2 \
    --max-time 10 \
    --retry 0 \
    --output "$response_file" \
    --write-out '%{http_code}' \
    --request POST \
    --header 'Accept: application/json' \
    --header 'Content-Type: application/json' \
    --data "$request_body" \
    "$target_url")"
fi

[[ "$http_status" =~ ^2[0-9][0-9]$ ]] || {
  fail "Quotation smoke test failed with HTTP ${http_status}"
}

jq -e \
  --arg partner_ref partner-01 \
  --arg profile_ref profile-00000000-0000-4000-8000-000000000101 \
  'def uuid_v4: type == "string" and test("^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$");
   def profile_id: type == "string" and test("^profile-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$");
   type == "object" and
   ((keys | sort) == (["quotation_id", "request_id", "partner_ref", "profile_ref", "currency", "monthly_premium", "risk_score", "tariff_version", "calculation_checksum"] | sort)) and
   (.quotation_id | uuid_v4) and
   (.request_id | uuid_v4) and
   (.partner_ref == $partner_ref) and
   ((.profile_ref | profile_id) and .profile_ref == $profile_ref) and
   (.currency == "COP") and
   ((.monthly_premium | type == "string" and test("^[0-9]+\\.[0-9]{2}$") and ((tonumber) > 0))) and
   ((.risk_score | type == "number") and (.risk_score | floor) == .risk_score and .risk_score >= 0 and .risk_score <= 1000) and
   (.tariff_version == "synthetic-v1") and
   (.calculation_checksum | type == "string" and test("^[0-9a-f]{16}$"))' \
  "$response_file" >/dev/null || fail "Quotation response failed the business JSON schema"
info "Smoke test passed with HTTP ${http_status}"
