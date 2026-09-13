#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=common.sh
source "${SCRIPT_DIR}/common.sh"

require_command docker
require_command git
require_command jq
verify_aws_identity
load_tf_outputs

[[ -z "$(git -C "$REPO_ROOT" status --porcelain -- services load-tests)" ]] \
  || fail "Refusing SHA-tagged builds while services/ or load-tests/ has uncommitted changes"

IMAGE_TAG="${IMAGE_TAG:-$(git -C "$REPO_ROOT" rev-parse --short=12 HEAD)}"
[[ "$IMAGE_TAG" =~ ^[0-9a-f]{12,40}$ ]] \
  || fail "IMAGE_TAG must be an immutable 12-40 character lowercase Git SHA"

quotation_repository="${QUOTATION_IMAGE_REPOSITORY:-$(tf_map_text ecr_repository_urls quote quotation quotation-service 2>/dev/null || true)}"
profile_repository="${PROFILE_IMAGE_REPOSITORY:-$(tf_map_text ecr_repository_urls profile profile-service 2>/dev/null || true)}"
runner_repository="${RUNNER_IMAGE_REPOSITORY:-$(tf_map_text ecr_repository_urls load-runner runner 2>/dev/null || true)}"
[[ -n "$quotation_repository" ]] || fail "Missing quote repository in ecr_repository_urls"
[[ -n "$profile_repository" ]] || fail "Missing profile repository in ecr_repository_urls"

ecr_registry="${quotation_repository%%/*}"
[[ "$ecr_registry" =~ ^[0-9]{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com$ ]] \
  || fail "Unexpected ECR registry: ${ecr_registry}"
[[ "${profile_repository%%/*}" == "$ecr_registry" ]] || fail "Application repositories must use the same ECR registry"

set +x
aws_cli ecr get-login-password \
  | docker login --username AWS --password-stdin "$ecr_registry" >/dev/null

info "Building and pushing quotation-service for EKS linux/amd64"
docker buildx build \
  --platform linux/amd64 \
  --pull \
  --label "org.opencontainers.image.revision=${IMAGE_TAG}" \
  --tag "${quotation_repository}:${IMAGE_TAG}" \
  --push \
  "${REPO_ROOT}/services/quotation-service"

info "Building and pushing profile-service for EKS linux/amd64"
docker buildx build \
  --platform linux/amd64 \
  --pull \
  --label "org.opencontainers.image.revision=${IMAGE_TAG}" \
  --tag "${profile_repository}:${IMAGE_TAG}" \
  --push \
  "${REPO_ROOT}/services/profile-service"

push_runner="${PUSH_RUNNER:-auto}"
[[ "$push_runner" =~ ^(auto|true|false)$ ]] || fail "PUSH_RUNNER must be auto, true, or false"
if [[ "$push_runner" == "auto" ]]; then
  if tf_text_first load_runner_task_definition_arn >/dev/null 2>&1; then
    push_runner=true
  else
    push_runner=false
  fi
fi

if [[ "$push_runner" == "true" ]]; then
  [[ -n "$runner_repository" ]] || fail "Fargate is enabled but ecr_repository_urls lacks load-runner"
  [[ "${runner_repository%%/*}" == "$ecr_registry" ]] || fail "Runner repository must use the same ECR registry"
  info "Building and pushing JMeter runner for Fargate linux/amd64"
  docker buildx build \
    --platform linux/amd64 \
    --pull \
    --build-arg "SOURCE_REVISION=${IMAGE_TAG}" \
    --label "org.opencontainers.image.revision=${IMAGE_TAG}" \
    --tag "${runner_repository}:${IMAGE_TAG}" \
    --push \
    "${REPO_ROOT}/load-tests/jmeter"
fi

quotation_digest="$(aws_cli ecr describe-images \
  --repository-name "${quotation_repository#*/}" \
  --image-ids "imageTag=${IMAGE_TAG}" \
  --query 'imageDetails[0].imageDigest' \
  --output text)"
profile_digest="$(aws_cli ecr describe-images \
  --repository-name "${profile_repository#*/}" \
  --image-ids "imageTag=${IMAGE_TAG}" \
  --query 'imageDetails[0].imageDigest' \
  --output text)"
[[ "$quotation_digest" =~ ^sha256:[0-9a-f]{64}$ && "$profile_digest" =~ ^sha256:[0-9a-f]{64}$ ]] \
  || fail "Unable to resolve pushed application image digests"

printf 'IMAGE_TAG=%s\n' "$IMAGE_TAG"
printf 'QUOTATION_IMAGE=%s:%s\n' "$quotation_repository" "$IMAGE_TAG"
printf 'PROFILE_IMAGE=%s:%s\n' "$profile_repository" "$IMAGE_TAG"
printf 'QUOTATION_IMAGE_DIGEST=%s@%s\n' "$quotation_repository" "$quotation_digest"
printf 'PROFILE_IMAGE_DIGEST=%s@%s\n' "$profile_repository" "$profile_digest"
if [[ "$push_runner" == "true" ]]; then
  runner_digest="$(aws_cli ecr describe-images \
    --repository-name "${runner_repository#*/}" \
    --image-ids "imageTag=${IMAGE_TAG}" \
    --query 'imageDetails[0].imageDigest' \
    --output text)"
  [[ "$runner_digest" =~ ^sha256:[0-9a-f]{64}$ ]] || fail "Unable to resolve pushed runner image digest"
  printf 'RUNNER_IMAGE=%s:%s\n' "$runner_repository" "$IMAGE_TAG"
  printf 'RUNNER_IMAGE_DIGEST=%s@%s\n' "$runner_repository" "$runner_digest"
fi
