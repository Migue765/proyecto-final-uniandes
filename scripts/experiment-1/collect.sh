#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command kubectl
require_command tar
require_command git
require_command helm
require_command jq
require_command python3
verify_aws_identity
load_tf_outputs
configure_eks_context

SOURCE_RUN_ID="${SOURCE_RUN_ID:-}"
if [[ -n "$SOURCE_RUN_ID" ]]; then
  validate_safe_id "$SOURCE_RUN_ID"
  [[ -d "${RESULTS_DIR}/${SOURCE_RUN_ID}" ]] || fail "Unknown local run: ${SOURCE_RUN_ID}"
fi

collection_id="collection-$(date -u +%Y%m%dT%H%M%SZ)"
collection_dir="${RESULTS_DIR}/${collection_id}"
mkdir -p "$collection_dir"

git -C "$REPO_ROOT" rev-parse HEAD >"${collection_dir}/git-revision.txt"
git -C "$REPO_ROOT" status --short >"${collection_dir}/git-status.txt"
helm get values "$RELEASE_NAME" --namespace "$NAMESPACE" --all --output yaml >"${collection_dir}/helm-values.yaml"
helm get manifest "$RELEASE_NAME" --namespace "$NAMESPACE" >"${collection_dir}/helm-manifest.yaml"
jq 'with_entries(select(.value.sensitive != true))' <<<"$TF_OUTPUTS_JSON" >"${collection_dir}/terraform-outputs-nonsensitive.json"

kubectl -n "$NAMESPACE" get deployments,replicasets,pods,services,hpa -o wide >"${collection_dir}/kubernetes-resources.txt"
kubectl -n "$NAMESPACE" describe hpa >"${collection_dir}/hpa-describe.txt"
kubectl -n "$NAMESPACE" get events --sort-by=.metadata.creationTimestamp >"${collection_dir}/events.txt"
kubectl -n "$NAMESPACE" top pods --containers >"${collection_dir}/pod-usage.txt" 2>&1 || true
kubectl -n "$NAMESPACE" get pods -o json \
  | jq '[.items[] | {
      pod:.metadata.name,
      requestedImages:[.spec.containers[] | {name,image}],
      resolvedImages:[.status.containerStatuses[]? | {name,image,imageID}]
    }]' >"${collection_dir}/pod-images.json"

api_log_group="$(tf_text_first api_gateway_log_group_name)"
aws_cli logs tail "$api_log_group" --since 3h --format short >"${collection_dir}/api-gateway-access.log" 2>&1 || true

api_name="$(tf_text_first api_gateway_name)"
api_stage="$(tf_text_first api_gateway_stage_name)"
rds_identifier="$(tf_text_first rds_instance_identifier)"
redis_members_json="$(tf_json_first redis_member_cluster_ids)"
validate_safe_id "$api_name"
validate_safe_id "$api_stage"
validate_safe_id "$rds_identifier"
jq -e 'type == "array" and length == 1 and all(.[]; type == "string" and test("^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$"))' \
  <<<"$redis_members_json" >/dev/null || fail "Expected exactly one safe Redis member cluster identifier"
redis_cluster_identifier="$(jq -er '.[0]' <<<"$redis_members_json")"

cloudwatch_queries_file="${collection_dir}/managed-cloudwatch-queries.json"
jq -n \
  --arg api "$api_name" \
  --arg stage "$api_stage" \
  --arg rds "$rds_identifier" \
  --arg redis "$redis_cluster_identifier" '
  def query($id; $label; $namespace; $metric; $dimensions; $stat):
    {
      Id: $id,
      Label: $label,
      ReturnData: true,
      MetricStat: {
        Metric: {Namespace: $namespace, MetricName: $metric, Dimensions: $dimensions},
        Period: 60,
        Stat: $stat
      }
    };
  [
    query("api_count"; "API requests"; "AWS/ApiGateway"; "Count"; [{Name:"ApiName",Value:$api},{Name:"Stage",Value:$stage}]; "Sum"),
    query("api_4xx"; "API 4XX"; "AWS/ApiGateway"; "4XXError"; [{Name:"ApiName",Value:$api},{Name:"Stage",Value:$stage}]; "Sum"),
    query("api_5xx"; "API 5XX"; "AWS/ApiGateway"; "5XXError"; [{Name:"ApiName",Value:$api},{Name:"Stage",Value:$stage}]; "Sum"),
    query("api_latency_p95"; "API latency p95 ms"; "AWS/ApiGateway"; "Latency"; [{Name:"ApiName",Value:$api},{Name:"Stage",Value:$stage}]; "p95"),
    query("api_latency_p99"; "API latency p99 ms"; "AWS/ApiGateway"; "Latency"; [{Name:"ApiName",Value:$api},{Name:"Stage",Value:$stage}]; "p99"),
    query("api_integration_p95"; "API integration latency p95 ms"; "AWS/ApiGateway"; "IntegrationLatency"; [{Name:"ApiName",Value:$api},{Name:"Stage",Value:$stage}]; "p95"),
    query("rds_cpu_avg"; "RDS CPU average percent"; "AWS/RDS"; "CPUUtilization"; [{Name:"DBInstanceIdentifier",Value:$rds}]; "Average"),
    query("rds_connections_max"; "RDS connections maximum"; "AWS/RDS"; "DatabaseConnections"; [{Name:"DBInstanceIdentifier",Value:$rds}]; "Maximum"),
    query("rds_memory_min"; "RDS free memory minimum bytes"; "AWS/RDS"; "FreeableMemory"; [{Name:"DBInstanceIdentifier",Value:$rds}]; "Minimum"),
    query("rds_storage_min"; "RDS free storage minimum bytes"; "AWS/RDS"; "FreeStorageSpace"; [{Name:"DBInstanceIdentifier",Value:$rds}]; "Minimum"),
    query("rds_read_p95"; "RDS read latency p95 seconds"; "AWS/RDS"; "ReadLatency"; [{Name:"DBInstanceIdentifier",Value:$rds}]; "p95"),
    query("rds_write_p95"; "RDS write latency p95 seconds"; "AWS/RDS"; "WriteLatency"; [{Name:"DBInstanceIdentifier",Value:$rds}]; "p95"),
    query("redis_cpu_avg"; "Redis engine CPU average percent"; "AWS/ElastiCache"; "EngineCPUUtilization"; [{Name:"CacheClusterId",Value:$redis}]; "Average"),
    query("redis_connections_max"; "Redis connections maximum"; "AWS/ElastiCache"; "CurrConnections"; [{Name:"CacheClusterId",Value:$redis}]; "Maximum"),
    query("redis_evictions"; "Redis evictions"; "AWS/ElastiCache"; "Evictions"; [{Name:"CacheClusterId",Value:$redis}]; "Sum"),
    query("redis_hits"; "Redis cache hits"; "AWS/ElastiCache"; "CacheHits"; [{Name:"CacheClusterId",Value:$redis}]; "Sum"),
    query("redis_misses"; "Redis cache misses"; "AWS/ElastiCache"; "CacheMisses"; [{Name:"CacheClusterId",Value:$redis}]; "Sum"),
    query("redis_memory_min"; "Redis free memory minimum bytes"; "AWS/ElastiCache"; "FreeableMemory"; [{Name:"CacheClusterId",Value:$redis}]; "Minimum")
  ]' >"$cloudwatch_queries_file"

if [[ -n "$SOURCE_RUN_ID" && -f "${RESULTS_DIR}/${SOURCE_RUN_ID}/manifest.json" ]]; then
  metric_start_time="$(jq -er '.started_at | select(type == "string" and test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"))' \
    "${RESULTS_DIR}/${SOURCE_RUN_ID}/manifest.json")" || fail "Run manifest has no safe UTC started_at"
else
  metric_start_time="$(python3 -c 'from datetime import datetime, timedelta, timezone; print((datetime.now(timezone.utc) - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%SZ"))')"
fi
metric_end_time="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
managed_metrics_file="${collection_dir}/managed-cloudwatch-metrics.json"
aws_cli cloudwatch get-metric-data \
  --metric-data-queries "file://${cloudwatch_queries_file}" \
  --start-time "$metric_start_time" \
  --end-time "$metric_end_time" \
  --scan-by TimestampAscending \
  --no-paginate \
  --output json >"$managed_metrics_file" \
  || fail "Unable to collect CloudWatch metrics for API Gateway, RDS, and Redis"

if [[ -n "$SOURCE_RUN_ID" ]]; then
  cp "$managed_metrics_file" "${RESULTS_DIR}/${SOURCE_RUN_ID}/managed-cloudwatch-metrics.json"
fi

task_definition="$(tf_text_first load_runner_task_definition_arn 2>/dev/null || true)"
if [[ -n "$task_definition" ]]; then
  aws_cli ecs describe-task-definition \
    --task-definition "$task_definition" \
    --query 'taskDefinition.{revision:revision,runtimePlatform:runtimePlatform,images:containerDefinitions[].{name:name,image:image}}' \
    --output json >"${collection_dir}/load-runner-task-definition.json"
fi

if [[ "${INCLUDE_LOGS:-false}" == "true" ]]; then
  kubectl -n "$NAMESPACE" logs deployment/solventa-exp1-quotation --all-pods=true --since=45m >"${collection_dir}/quotation.log"
  kubectl -n "$NAMESPACE" logs deployment/solventa-exp1-profile --all-pods=true --since=45m >"${collection_dir}/profile.log"
fi

archive="${RESULTS_DIR}/${collection_id}.tar.gz"
if [[ -n "$SOURCE_RUN_ID" ]]; then
  tar -czf "$archive" -C "$RESULTS_DIR" "$SOURCE_RUN_ID" "$collection_id"
else
  tar -czf "$archive" -C "$RESULTS_DIR" "$collection_id"
fi

evidence_bucket="${EVIDENCE_BUCKET:-$(tf_text_first evidence_bucket_name results_bucket_name 2>/dev/null || true)}"
S3_PREFIX="${S3_PREFIX:-jtl}"
[[ "$S3_PREFIX" =~ ^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$ ]] || fail "Invalid S3_PREFIX"
if [[ -n "$evidence_bucket" ]]; then
  [[ "$evidence_bucket" =~ ^[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]$ ]] || fail "Invalid evidence bucket"
  if [[ -n "$SOURCE_RUN_ID" ]]; then
    evidence_key="${S3_PREFIX}/${SOURCE_RUN_ID}/${collection_id}.tar.gz"
  else
    evidence_key="${S3_PREFIX}/${collection_id}.tar.gz"
  fi
  aws_cli s3 cp "$archive" "s3://${evidence_bucket}/${evidence_key}" \
    --only-show-errors \
    --sse AES256
  info "Collection uploaded to s3://${evidence_bucket}/${evidence_key}"
fi

info "Evidence archive created: ${archive}"
