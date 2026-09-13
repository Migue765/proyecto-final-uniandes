#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command kubectl
require_command jq
RUN_ID="${RUN_ID:-monitor-$(date -u +%Y%m%dT%H%M%SZ)}"
MONITOR_INTERVAL_SECONDS="${MONITOR_INTERVAL_SECONDS:-15}"
MONITOR_DURATION_SECONDS="${MONITOR_DURATION_SECONDS:-7500}"
PROMETHEUS_INTERVAL_SECONDS="${PROMETHEUS_INTERVAL_SECONDS:-60}"
validate_safe_id "$RUN_ID"
[[ "$MONITOR_INTERVAL_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "MONITOR_INTERVAL_SECONDS must be positive"
[[ "$MONITOR_DURATION_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "MONITOR_DURATION_SECONDS must be positive"
[[ "$PROMETHEUS_INTERVAL_SECONDS" =~ ^[1-9][0-9]*$ ]] || fail "PROMETHEUS_INTERVAL_SECONDS must be positive"

monitor_dir="${RESULTS_DIR}/${RUN_ID}/k8s"
prometheus_dir="${monitor_dir}/prometheus"
mkdir -p "$monitor_dir"
mkdir -p "$prometheus_dir"
samples_file="${monitor_dir}/autoscaling.log"
structured_file="${monitor_dir}/autoscaling.jsonl"
resource_usage_file="${monitor_dir}/resource-usage.jsonl"
monitor_errors_file="${monitor_dir}/monitor-errors.log"
deadline=$((SECONDS + MONITOR_DURATION_SECONDS))
next_prometheus_sample=0

capture_application_metrics() {
  local timestamp="$1" component pods_json pod metrics_file
  for component in quotation profile; do
    if ! pods_json="$(kubectl -n "$NAMESPACE" get pods \
      -l "app.kubernetes.io/component=${component}" -o json 2>>"$monitor_errors_file")"; then
      continue
    fi
    while IFS= read -r pod; do
      [[ "$pod" =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]] || continue
      metrics_file="${prometheus_dir}/${timestamp}-${pod}.prom"
      if ! kubectl -n "$NAMESPACE" exec "$pod" -c "$component" -- python -c \
        'import sys, urllib.request; data = urllib.request.urlopen("http://127.0.0.1:8080/metrics", timeout=2).read(1048577); len(data) <= 1048576 or (_ for _ in ()).throw(ValueError("metrics response too large")); sys.stdout.buffer.write(data)' \
        >"$metrics_file" 2>>"$monitor_errors_file"; then
        rm -f -- "$metrics_file"
      fi
    done < <(jq -r --arg component "$component" \
      '.items[] | select(any(.status.containerStatuses[]?; .name == $component and .ready == true)) | .metadata.name' \
      <<<"$pods_json")
  done
}

while (( SECONDS < deadline )); do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  timestamp_iso="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  {
    printf '\n===== %s =====\n' "$timestamp_iso"
    kubectl -n "$NAMESPACE" get hpa,deploy,pods -o wide
    kubectl -n "$NAMESPACE" top pods --containers
  } >>"$samples_file" 2>&1 || true

  if resources_json="$(kubectl -n "$NAMESPACE" get hpa,deploy,pods -o json 2>>"$monitor_errors_file")"; then
    jq -c --arg timestamp "$timestamp_iso" '
      {
        timestamp: $timestamp,
        hpa: [.items[] | select(.kind == "HorizontalPodAutoscaler") | {
          name: .metadata.name,
          target_kind: .spec.scaleTargetRef.kind,
          target_name: .spec.scaleTargetRef.name,
          min_replicas: (.spec.minReplicas // 1),
          max_replicas: .spec.maxReplicas,
          current_replicas: (.status.currentReplicas // 0),
          desired_replicas: (.status.desiredReplicas // 0),
          current_cpu_percent: ([.status.currentMetrics[]? | select(.type == "Resource" and .resource.name == "cpu") | .resource.current.averageUtilization][0] // null),
          conditions: [.status.conditions[]? | {type, status, reason}]
        }],
        deployments: [.items[] | select(.kind == "Deployment") | {
          name: .metadata.name,
          desired_replicas: (.spec.replicas // 0),
          ready_replicas: (.status.readyReplicas // 0),
          available_replicas: (.status.availableReplicas // 0),
          unavailable_replicas: (.status.unavailableReplicas // 0)
        }],
        pods: [.items[] | select(.kind == "Pod") | {
          name: .metadata.name,
          phase: .status.phase,
          ready: ([.status.containerStatuses[]?.ready] | length > 0 and all(.[]; . == true)),
          containers: [.status.containerStatuses[]? | {name, ready, restart_count: .restartCount}]
        }]
      }' <<<"$resources_json" >>"$structured_file" \
      || printf '%s unable to encode Kubernetes resource snapshot\n' "$timestamp_iso" >>"$monitor_errors_file"
  fi

  if usage_json="$(kubectl get --raw "/apis/metrics.k8s.io/v1beta1/namespaces/${NAMESPACE}/pods" 2>>"$monitor_errors_file")"; then
    jq -c --arg timestamp "$timestamp_iso" \
      '{timestamp: $timestamp, pods: [.items[] | {name: .metadata.name, containers: [.containers[] | {name, usage}]}]}' \
      <<<"$usage_json" >>"$resource_usage_file" \
      || printf '%s unable to encode Metrics Server snapshot\n' "$timestamp_iso" >>"$monitor_errors_file"
  fi

  if (( SECONDS >= next_prometheus_sample )); then
    capture_application_metrics "$timestamp"
    next_prometheus_sample=$((SECONDS + PROMETHEUS_INTERVAL_SECONDS))
  fi
  sleep "$MONITOR_INTERVAL_SECONDS"
done

info "Kubernetes, resource, and application metric samples written to ${monitor_dir}"
