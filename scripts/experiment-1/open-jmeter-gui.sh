#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command jmeter
require_command env
verify_aws_identity
load_tf_outputs

terraform_invoke_url="$(tf_text_first api_gateway_invoke_url 2>/dev/null || true)"
[[ -n "$terraform_invoke_url" ]] || fail "Missing Terraform output api_gateway_invoke_url"
validate_http_url "$terraform_invoke_url"

if [[ "$terraform_invoke_url" == */api/v1/cotizaciones ]]; then
  target_url="$terraform_invoke_url"
else
  target_url="${terraform_invoke_url%/}/api/v1/cotizaciones"
fi
[[ "$target_url" == https://* ]] || fail "The GUI diagnostic target must use HTTPS"

allowed_host="$(url_host "$terraform_invoke_url")"
[[ "$allowed_host" == *.execute-api."${AWS_REGION}".amazonaws.com ]] \
  || fail "Unexpected API Gateway host for region ${AWS_REGION}: ${allowed_host}"
require_allowed_target "$target_url" "$allowed_host"

gui_plan="${REPO_ROOT}/load-tests/jmeter/gui-500rpm.jmx"
sigv4_script="${REPO_ROOT}/load-tests/jmeter/sigv4.groovy"
credential_refresh_script="${REPO_ROOT}/load-tests/jmeter/refresh-aws-credentials.groovy"
user_properties="${REPO_ROOT}/load-tests/jmeter/user.properties"

for required_file in "$gui_plan" "$sigv4_script" "$credential_refresh_script" "$user_properties"; do
  [[ -f "$required_file" && ! -L "$required_file" ]] || fail "Missing or unsafe JMeter file: ${required_file}"
done

info "Opening JMeter GUI for 500 aggregate RPM during 10 minutes against ${target_url}"
info "Global Play refreshes solventa-lab credentials immediately before traffic starts"
info "Use Aggregate Report for throughput and response-time percentiles"
info "Do not use Start Selected; it bypasses the credential setup group"

cd "${REPO_ROOT}/load-tests/jmeter"
env \
  -u AWS_ACCESS_KEY_ID \
  -u AWS_SECRET_ACCESS_KEY \
  -u AWS_SESSION_TOKEN \
  -u AWS_CREDENTIAL_EXPIRATION_EPOCH \
  jmeter \
  -j "/private/tmp/solventa-jmeter-gui-500rpm.log" \
  -q "$user_properties" \
  -t "$gui_plan" \
  "-Jtarget_url=${target_url}" \
  "-Jsigv4_script_path=${sigv4_script}" \
  "-Jcredential_refresh_script_path=${credential_refresh_script}" \
  "-Jaws_cli_path=${AWS_BIN}" \
  "-Jaws_profile=${AWS_PROFILE}" \
  "-Jexpected_aws_account_id=${EXPECTED_AWS_ACCOUNT_ID}" \
  "-Jexpected_aws_principal_arn=arn:aws:iam::${EXPECTED_AWS_ACCOUNT_ID}:user/solventa-terraform-operator" \
  "-Jcredential_ttl_margin_seconds=60" \
  "-Jauth_mode=aws_iam" \
  "-Jaws_region=${AWS_REGION}" \
  "-Jaws_service=execute-api" \
  "-Jtarget_rpm=500" \
  "-Jgui_threads=50" \
  "-Jgui_ramp_seconds=5" \
  "-Jgui_duration_seconds=600"
