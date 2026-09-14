#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command jq
verify_aws_identity
load_tf_outputs

RUN_ID="${RUN_ID:-exp1-ecs-$(date -u +%Y%m%dT%H%M%SZ)}"
ECS_CONTAINER_NAME="${ECS_CONTAINER_NAME:-load-runner}"
S3_PREFIX="${S3_PREFIX:-jtl}"
validate_safe_id "$RUN_ID"
validate_safe_id "$ECS_CONTAINER_NAME"
[[ "$S3_PREFIX" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ ]] || fail "Invalid S3_PREFIX"

ecs_cluster="${ECS_CLUSTER_NAME:-$(tf_text_first load_runner_cluster_name ecs_load_runner_cluster_name 2>/dev/null || true)}"
task_definition="${ECS_TASK_DEFINITION_ARN:-$(tf_text_first load_runner_task_definition_arn ecs_load_runner_task_definition_arn 2>/dev/null || true)}"
security_group="${LOAD_RUNNER_SECURITY_GROUP_ID:-$(tf_text_first load_runner_security_group_id 2>/dev/null || true)}"
subnets_json="${PRIVATE_SUBNET_IDS_JSON:-$(tf_json_first private_subnet_ids 2>/dev/null || true)}"
evidence_bucket="${EVIDENCE_BUCKET:-$(tf_text_first evidence_bucket_name results_bucket_name 2>/dev/null || true)}"
api_base_url="${API_BASE_URL:-$(tf_text_first api_gateway_invoke_url api_gateway_url api_invoke_url quotation_api_url 2>/dev/null || true)}"

[[ -n "$ecs_cluster" ]] || fail "Missing ecs_load_runner_cluster_name"
[[ -n "$task_definition" ]] || fail "Missing ecs_load_runner_task_definition_arn"
[[ "$security_group" =~ ^sg-[a-zA-Z0-9]+$ ]] || fail "Invalid load runner security group"
jq -e 'type == "array" and length > 0 and all(.[]; type == "string" and startswith("subnet-"))' <<<"$subnets_json" >/dev/null \
  || fail "private_subnet_ids is not a non-empty subnet list"
[[ "$evidence_bucket" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]] || fail "Missing or invalid evidence bucket"
validate_http_url "$api_base_url"

runner_image_ref="$(aws_cli ecs describe-task-definition \
  --task-definition "$task_definition" \
  --query "taskDefinition.containerDefinitions[?name=='${ECS_CONTAINER_NAME}'].image | [0]" \
  --output text)"
[[ -n "$runner_image_ref" && "$runner_image_ref" != "None" && "$runner_image_ref" != *[[:space:]]* ]] \
  || fail "Unable to determine the immutable load-runner image"
[[ "$runner_image_ref" =~ (@sha256:[0-9a-f]{64}|:[0-9a-f]{12,40})$ ]] \
  || fail "Fargate load-runner image must use an immutable SHA tag or digest"

if [[ "$api_base_url" == */api/v1/cotizaciones ]]; then
  target_url="$api_base_url"
else
  target_url="${api_base_url%/}/api/v1/cotizaciones"
fi
target_host="$(url_host "$target_url")"

network_configuration="$(jq -cn \
  --argjson subnets "$subnets_json" \
  --arg security_group "$security_group" \
  '{awsvpcConfiguration:{subnets:$subnets,securityGroups:[$security_group],assignPublicIp:"DISABLED"}}')"

overrides="$(jq -cn \
  --arg container "$ECS_CONTAINER_NAME" \
  --arg target_url "$target_url" \
  --arg target_host "$target_host" \
  --arg run_id "$RUN_ID" \
  --arg evidence_bucket "$evidence_bucket" \
  --arg s3_prefix "$S3_PREFIX" \
  --arg aws_region "$AWS_REGION" \
  --arg runner_image_ref "$runner_image_ref" \
  '{containerOverrides:[{name:$container,environment:[
    {name:"TARGET_URL",value:$target_url},
    {name:"ALLOWED_TARGET_HOSTS",value:$target_host},
    {name:"RUN_ID",value:$run_id},
    {name:"EVIDENCE_BUCKET",value:$evidence_bucket},
    {name:"S3_PREFIX",value:$s3_prefix},
    {name:"AUTH_MODE",value:"aws_iam"},
    {name:"AWS_REGION",value:$aws_region},
    {name:"AWS_SERVICE",value:"execute-api"},
    {name:"RUNNER_IMAGE_REF",value:$runner_image_ref}
  ]}]}')"

task_arn="$(aws_cli ecs run-task \
  --cluster "$ecs_cluster" \
  --task-definition "$task_definition" \
  --launch-type FARGATE \
  --network-configuration "$network_configuration" \
  --overrides "$overrides" \
  --query 'tasks[0].taskArn' \
  --output text)"

[[ "$task_arn" == arn:aws:ecs:* ]] || fail "ECS did not start the load task; inspect the run-task failures response"
info "ECS load task started: ${task_arn}"
info "Expected evidence destination: s3://${evidence_bucket}/${S3_PREFIX}/${RUN_ID}/"

if [[ "${WAIT_FOR_COMPLETION:-false}" == "true" ]]; then
  require_command kubectl
  configure_eks_context
  RUN_ID="$RUN_ID" \
  MONITOR_DURATION_SECONDS=2100 \
  SKIP_CONTEXT_UPDATE=true \
  "${SCRIPT_DIR}/monitor.sh" &
  monitor_pid=$!
  cleanup() {
    kill "$monitor_pid" >/dev/null 2>&1 || true
    wait "$monitor_pid" >/dev/null 2>&1 || true
  }
  trap cleanup EXIT INT TERM

  deadline=$((SECONDS + 3600))
  while (( SECONDS < deadline )); do
    task_status="$(aws_cli ecs describe-tasks \
      --cluster "$ecs_cluster" \
      --tasks "$task_arn" \
      --query 'tasks[0].lastStatus' \
      --output text)"
    [[ "$task_status" != "STOPPED" ]] || break
    sleep 30
  done
  [[ "${task_status:-}" == "STOPPED" ]] || fail "Timed out waiting for ECS load task"
  exit_code="$(aws_cli ecs describe-tasks \
    --cluster "$ecs_cluster" \
    --tasks "$task_arn" \
    --query 'tasks[0].containers[0].exitCode' \
    --output text)"
  [[ "$exit_code" == "0" ]] || fail "ECS load task stopped with exit code ${exit_code}"
  cleanup
  trap - EXIT INT TERM
  info "ECS load task completed successfully"
  if [[ "${UPLOAD_K8S_EVIDENCE:-true}" == "true" ]]; then
    SOURCE_RUN_ID="$RUN_ID" \
    EVIDENCE_BUCKET="$evidence_bucket" \
    S3_PREFIX="$S3_PREFIX" \
    "${SCRIPT_DIR}/collect.sh"
  fi
fi
