#!/usr/bin/env bash
set -Eeuo pipefail

readonly PLAN=/work/experiment-1.jmx
readonly PROPERTIES=/work/user.properties
readonly RESULTS_ROOT=/work/results

TARGET_URL="${TARGET_URL:-http://127.0.0.1:30080/api/v1/cotizaciones}"
ALLOWED_TARGET_HOSTS="${ALLOWED_TARGET_HOSTS:-127.0.0.1,localhost,host.docker.internal}"
TARGET_RPM="${TARGET_RPM:-500}"
WARMUP_RPM="${WARMUP_RPM:-50}"
PARTNER_THREADS="${PARTNER_THREADS:-50}"
WARMUP_SECONDS="${WARMUP_SECONDS:-60}"
MEASURED_SECONDS="${MEASURED_SECONDS:-480}"
RUNS="${RUNS:-3}"
RUN_START="${RUN_START:-1}"
RUN_END="${RUN_END:-$RUNS}"
RAMP_SECONDS="${RAMP_SECONDS:-5}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-30}"
POST_COOLDOWN_OBSERVATION_SECONDS="${POST_COOLDOWN_OBSERVATION_SECONDS:-30}"
RUN_ID="${RUN_ID:-exp1-$(date -u +%Y%m%dT%H%M%SZ)}"
VALIDATION_MODE="${VALIDATION_MODE:-false}"
EVIDENCE_BUCKET="${EVIDENCE_BUCKET:-}"
S3_PREFIX="${S3_PREFIX:-jtl}"
AUTH_MODE="${AUTH_MODE:-aws_iam}"
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_SERVICE="${AWS_SERVICE:-execute-api}"
RUNNER_IMAGE_REF="${RUNNER_IMAGE_REF:-unknown}"
RUNNER_SOURCE_REVISION="${RUNNER_SOURCE_REVISION:-unknown}"

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

is_positive_integer() {
  [[ "$1" =~ ^[1-9][0-9]*$ ]]
}

[[ "$TARGET_URL" =~ ^https?://[^/?#[:space:]]+(/[^[:space:]]*)?$ ]] || fail "TARGET_URL must be an absolute HTTP(S) URL without whitespace"
[[ "$RUN_ID" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$ ]] || fail "RUN_ID contains unsupported characters"
[[ "$S3_PREFIX" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ ]] || fail "S3_PREFIX contains unsupported characters"
[[ "$AUTH_MODE" =~ ^(aws_iam|none)$ ]] || fail "AUTH_MODE must be aws_iam or none"
[[ "$AWS_REGION" =~ ^[a-z]{2}(-gov)?-[a-z]+-[0-9]+$ ]] || fail "AWS_REGION is invalid"
[[ "$AWS_SERVICE" == "execute-api" ]] || fail "AWS_SERVICE must be execute-api"
[[ "$RUNNER_SOURCE_REVISION" == "unknown" || "$RUNNER_SOURCE_REVISION" =~ ^[0-9a-f]{12,40}$ ]] \
  || fail "RUNNER_SOURCE_REVISION must be a Git SHA or unknown"
[[ "$RUNNER_IMAGE_REF" != *[[:space:]]* ]] || fail "RUNNER_IMAGE_REF cannot contain whitespace"

for numeric_value in "$TARGET_RPM" "$WARMUP_RPM" "$PARTNER_THREADS" "$WARMUP_SECONDS" "$MEASURED_SECONDS" "$RUNS" "$RUN_START" "$RUN_END" "$RAMP_SECONDS" "$COOLDOWN_SECONDS" "$POST_COOLDOWN_OBSERVATION_SECONDS"; do
  is_positive_integer "$numeric_value" || fail "Load parameters must be positive integers"
done
(( RUN_START <= RUN_END && RUN_END <= RUNS )) || fail "RUN_START/RUN_END must select an ordered subset of 1..RUNS"

if [[ "$VALIDATION_MODE" != "true" ]]; then
  [[ "$TARGET_RPM" == "500" ]] || fail "Experiment 1 baseline is fixed at 500 aggregate RPM"
  [[ "$WARMUP_RPM" == "50" ]] || fail "Experiment 1 warm-up is fixed at 50 aggregate RPM"
  [[ "$PARTNER_THREADS" == "50" ]] || fail "Experiment 1 is fixed at 50 synthetic partners"
  [[ "$WARMUP_SECONDS" == "60" ]] || fail "Experiment 1 warm-up is fixed at 60 seconds"
  [[ "$MEASURED_SECONDS" == "480" ]] || fail "Experiment 1 measured window is fixed at 480 seconds"
  [[ "$RUNS" == "3" ]] || fail "Experiment 1 requires exactly three complete runs"
  [[ "$COOLDOWN_SECONDS" == "30" ]] || fail "Experiment 1 requires a 30-second low-load cooldown after every run"
  [[ "$POST_COOLDOWN_OBSERVATION_SECONDS" == "30" ]] || fail "Experiment 1 requires a 30-second post-cooldown observation"
  (( RAMP_SECONDS <= 5 )) || fail "Experiment 1 ramp must be at most 5 seconds"
fi

target_authority="${TARGET_URL#*://}"
target_authority="${target_authority%%/*}"
target_host="${target_authority%%:*}"
[[ ",${ALLOWED_TARGET_HOSTS}," == *",${target_host},"* ]] || fail "Target host is not present in ALLOWED_TARGET_HOSTS"

if [[ "$AUTH_MODE" == "aws_iam" ]]; then
  [[ "$TARGET_URL" == https://* ]] || fail "AWS IAM load targets must use HTTPS"
  [[ "$target_host" == *.execute-api."${AWS_REGION}".amazonaws.com ]] \
    || fail "AWS IAM load target must be API Gateway in ${AWS_REGION}"
  [[ "$TARGET_URL" != *\?* && "$TARGET_URL" != *\#* ]] || fail "SigV4 target cannot include query or fragment"
  command -v aws >/dev/null 2>&1 || fail "AWS CLI is required for temporary credential resolution"
  command -v jq >/dev/null 2>&1 || fail "jq is required for temporary credential resolution"
else
  [[ "$VALIDATION_MODE" == "true" ]] || fail "AUTH_MODE=none is allowed only in VALIDATION_MODE"
  [[ "$target_host" == "127.0.0.1" || "$target_host" == "localhost" || "$target_host" == "host.docker.internal" ]] \
    || fail "Unsigned validation is restricted to a local host"
fi

refresh_aws_credentials() {
  [[ "$AUTH_MODE" == "aws_iam" ]] || return 0
  local credential_json access_key secret_key session_token
  set +x
  if [[ -n "${AWS_CONTAINER_CREDENTIALS_RELATIVE_URI:-}${AWS_CONTAINER_CREDENTIALS_FULL_URI:-}" ]]; then
    credential_json="$(env -u AWS_ACCESS_KEY_ID -u AWS_SECRET_ACCESS_KEY -u AWS_SESSION_TOKEN \
      aws configure export-credentials --format process)"
  else
    credential_json="$(aws configure export-credentials --format process)"
  fi
  access_key="$(jq -er '.AccessKeyId | select(type == "string" and length > 0)' <<<"$credential_json")"
  secret_key="$(jq -er '.SecretAccessKey | select(type == "string" and length > 0)' <<<"$credential_json")"
  session_token="$(jq -er '.SessionToken | select(type == "string" and length > 0)' <<<"$credential_json")"
  export AWS_ACCESS_KEY_ID="$access_key"
  export AWS_SECRET_ACCESS_KEY="$secret_key"
  export AWS_SESSION_TOKEN="$session_token"
  unset credential_json
}

if [[ -n "$EVIDENCE_BUCKET" ]]; then
  [[ "$EVIDENCE_BUCKET" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]] || fail "EVIDENCE_BUCKET is not a valid S3 bucket name"
  command -v aws >/dev/null 2>&1 || fail "AWS CLI is required when EVIDENCE_BUCKET is set"
fi

run_root="${RESULTS_ROOT}/${RUN_ID}"
[[ ! -L "$run_root" ]] || fail "Result directory must not be a symbolic link"
if (( RUN_START == 1 )); then
  [[ ! -e "${run_root}/manifest.json" ]] || fail "Result directory was already used: ${run_root}"
  mkdir -p "$run_root"
  jq -cn \
    --arg run_id "$RUN_ID" \
    --arg auth_mode "$AUTH_MODE" \
    --arg runner_image "$RUNNER_IMAGE_REF" \
    --arg source_revision "$RUNNER_SOURCE_REVISION" \
    --arg started_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    --argjson warmup_rpm "$WARMUP_RPM" \
    --argjson target_rpm "$TARGET_RPM" \
    --argjson partners "$PARTNER_THREADS" \
    --argjson warmup_seconds "$WARMUP_SECONDS" \
    --argjson measured_seconds "$MEASURED_SECONDS" \
    --argjson cooldown_seconds "$COOLDOWN_SECONDS" \
    --argjson post_cooldown_observation_seconds "$POST_COOLDOWN_OBSERVATION_SECONDS" \
    --argjson runs "$RUNS" \
    '{run_id:$run_id,auth_mode:$auth_mode,runner_image:$runner_image,source_revision:$source_revision,warmup_rpm:$warmup_rpm,target_rpm:$target_rpm,partners:$partners,profiles_per_partner:20,warmup_seconds:$warmup_seconds,measured_seconds:$measured_seconds,cooldown_seconds:$cooldown_seconds,post_cooldown_observation_seconds:$post_cooldown_observation_seconds,runs:$runs,started_at:$started_at}' \
    >"${run_root}/manifest.json"
else
  [[ -f "${run_root}/manifest.json" ]] || fail "Missing manifest from the first orchestrated run"
  jq -e \
    --arg run_id "$RUN_ID" \
    --arg auth_mode "$AUTH_MODE" \
    --argjson runs "$RUNS" \
    --argjson warmup_rpm "$WARMUP_RPM" \
    --argjson target_rpm "$TARGET_RPM" \
    --argjson partners "$PARTNER_THREADS" \
    --argjson warmup_seconds "$WARMUP_SECONDS" \
    --argjson measured_seconds "$MEASURED_SECONDS" \
    --argjson cooldown_seconds "$COOLDOWN_SECONDS" \
    --argjson observation_seconds "$POST_COOLDOWN_OBSERVATION_SECONDS" \
    '.run_id == $run_id and .auth_mode == $auth_mode and .runs == $runs and
     .warmup_rpm == $warmup_rpm and .target_rpm == $target_rpm and .partners == $partners and
     .warmup_seconds == $warmup_seconds and .measured_seconds == $measured_seconds and
     .cooldown_seconds == $cooldown_seconds and .post_cooldown_observation_seconds == $observation_seconds' \
    "${run_root}/manifest.json" >/dev/null \
    || fail "Existing manifest does not match the orchestrated run protocol"
  [[ -f "${run_root}/run-$((RUN_START - 1))/completed.json" ]] \
    || fail "Previous orchestrated run is not complete"
fi

for run_number in $(seq "$RUN_START" "$RUN_END"); do
  run_dir="${run_root}/run-${run_number}"
  profile_offset=$(((run_number - 1) * 20))
  measured_delay_seconds="$WARMUP_SECONDS"
  cooldown_delay_seconds=$((WARMUP_SECONDS + MEASURED_SECONDS))
  [[ ! -e "$run_dir" ]] || fail "Run directory already exists: ${run_dir}"
  mkdir -p "$run_dir"
  printf '{"run":%s,"profile_start":%s,"profile_end":%s,"profiles_per_partner":20}\n' \
    "$run_number" "$((profile_offset + 1))" "$((profile_offset + 20))" >"${run_dir}/protocol.json"

  printf 'Run %s/%s: one JVM, %s RPM warm-up (%ss) -> %s RPM measured (%ss) -> %s RPM cooldown (%ss)\n' \
    "$run_number" "$RUNS" "$WARMUP_RPM" "$WARMUP_SECONDS" "$TARGET_RPM" "$MEASURED_SECONDS" "$WARMUP_RPM" "$COOLDOWN_SECONDS"
  refresh_aws_credentials
  jmeter -n -j "${run_dir}/jmeter.log" -q "$PROPERTIES" -t "$PLAN" \
    -Jtarget_url="$TARGET_URL" \
    -Jwarmup_rpm="$WARMUP_RPM" \
    -Jtarget_rpm="$TARGET_RPM" \
    -Jpartner_threads="$PARTNER_THREADS" \
    -Jprofile_offset="$profile_offset" \
    -Jauth_mode="$AUTH_MODE" \
    -Jaws_region="$AWS_REGION" \
    -Jaws_service="$AWS_SERVICE" \
    -Jramp_seconds="$RAMP_SECONDS" \
    -Jwarmup_seconds="$WARMUP_SECONDS" \
    -Jmeasured_seconds="$MEASURED_SECONDS" \
    -Jcooldown_seconds="$COOLDOWN_SECONDS" \
    -Jmeasured_delay_seconds="$measured_delay_seconds" \
    -Jcooldown_delay_seconds="$cooldown_delay_seconds" \
    -Jjmeter.reportgenerator.temp_dir="/tmp/jmeter-report-${run_number}" \
    -l "${run_dir}/measured.jtl" \
    -e -o "${run_dir}/report"

  [[ -s "${run_dir}/measured.jtl" && -s "${run_dir}/report/index.html" && -s "${run_dir}/report/statistics.json" ]] \
    || fail "Measured evidence or HTML report is missing for run ${run_number}"
  if grep -Eq 'warmup -|cooldown -' "${run_dir}/measured.jtl"; then
    fail "Non-measured samples leaked into the JTL for run ${run_number}"
  fi
  sample_count="$(jq -er '.Total.sampleCount | select(type == "number" and . > 0)' "${run_dir}/report/statistics.json")" \
    || fail "The measured JTL has no samples for run ${run_number}"
  error_count="$(jq -er '.Total.errorCount | select(type == "number" and . >= 0)' "${run_dir}/report/statistics.json")"
  error_pct="$(jq -er '.Total.errorPct | select(type == "number" and . >= 0)' "${run_dir}/report/statistics.json")"
  measured_throughput="$(jq -er '.Total.throughput | select(type == "number" and . >= 0)' "${run_dir}/report/statistics.json")"

  printf 'Run %s/%s: observing HPA for %ss after cooldown\n' "$run_number" "$RUNS" "$POST_COOLDOWN_OBSERVATION_SECONDS"
  sleep "$POST_COOLDOWN_OBSERVATION_SECONDS"
  jq -cn \
    --argjson run "$run_number" \
    --argjson samples "$sample_count" \
    --argjson errors "$error_count" \
    --argjson error_pct "$error_pct" \
    --argjson throughput "$measured_throughput" \
    --arg completed_at "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
    '{run:$run,samples:$samples,errors:$errors,error_pct:$error_pct,measured_throughput_rps:$throughput,completed_at:$completed_at}' \
    >"${run_dir}/completed.json"
  printf 'Run %s/%s measured summary: %s samples, %s errors (%s%%), %.3f RPS observed\n' \
    "$run_number" "$RUNS" "$sample_count" "$error_count" "$error_pct" "$measured_throughput"
done

if (( RUN_END == RUNS )); then
  archive="/tmp/${RUN_ID}.tar.gz"
  tar --exclude="${RUN_ID}/k8s" -czf "$archive" -C "$RESULTS_ROOT" "$RUN_ID"
  cp "$archive" "${run_root}/${RUN_ID}.tar.gz"

  if [[ -n "$EVIDENCE_BUCKET" ]]; then
    aws s3 cp "$archive" "s3://${EVIDENCE_BUCKET}/${S3_PREFIX}/${RUN_ID}/${RUN_ID}.tar.gz" \
      --only-show-errors \
      --sse AES256
    printf 'Evidence uploaded to s3://%s/%s/%s/\n' "$EVIDENCE_BUCKET" "$S3_PREFIX" "$RUN_ID"
  fi

  rm "$archive"
  printf 'Experiment complete. Local evidence: %s\n' "$run_root"
else
  printf 'Run segment %s-%s complete; evidence remains in %s\n' "$RUN_START" "$RUN_END" "$run_root"
fi
