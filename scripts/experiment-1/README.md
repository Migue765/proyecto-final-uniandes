# Experiment 1 runbook

All commands default to AWS profile `solventa-lab`, region `us-east-1`, namespace
`solventa-exp1`, and Terraform state under `infra/terraform/exp1`. The scripts
verify account `969325258550` before changing AWS or Kubernetes state.

Nothing in this directory runs automatically.

## Prerequisites

- `/opt/homebrew/bin/aws` v2 session established with `aws login`.
- Terraform infrastructure already applied and its outputs available.
- `terraform`, `kubectl`, `helm`, `jq`, `curl`, Docker, and `xmllint` locally.
- Docker Buildx available on the `linux/amd64` Colima builder.
- local and NAT egress CIDRs allowed by the API Gateway resource policy as
  appropriate for the chosen runner.

## Sequence

1. Validate without contacting AWS:

   ```bash
   scripts/experiment-1/validate.sh
   ```

2. Build and push quotation/profile and the enabled Fargate runner as
   `linux/amd64`. The command prints the immutable Git-SHA tag to reuse:

   ```bash
   PUSH_RUNNER=true scripts/experiment-1/build-push.sh
   ```

   Before enabling the optional Fargate runner, copy the printed immutable
   `RUNNER_IMAGE=<repository>:<sha>` into Terraform's `load_runner_image`
   variable and re-plan. Never substitute `latest`.

3. Deploy the services and Metrics Server using the tag printed above. The script
   streams a short-lived RDS admin URL, a preserved generated `solventa_runtime`
   credential, and the authenticated `rediss://` URL directly into Kubernetes;
   no value is written to disk. The Helm pre-install Job runs
   `python -m app.seed`, creates/grants the read-only runtime role, and must
   succeed before workloads. The admin Secret and seed Job are deleted whenever
   the deployment script exits, whether it succeeds or fails:

   ```bash
   IMAGE_TAG=<immutable-tag> scripts/experiment-1/deploy.sh
   ```

4. Execute one non-retried, SigV4-signed smoke request through API Gateway, VPC
   Link, NLB, and EKS. It validates the complete business JSON schema:

   ```bash
   scripts/experiment-1/smoke.sh
   ```

5. Run the baseline locally against the same API Gateway path (approximately
   120 minutes plus startup/reporting):

   ```bash
   scripts/experiment-1/run-local.sh
   ```

   The local script deliberately uses one container per run. It refreshes the
   `solventa-lab` temporary session immediately before each container and rejects
   a session that cannot cover the 40-minute traffic schedule plus the
   five-minute credential margin. Within each container, warm-up, measurement,
   and cooldown remain one uninterrupted JMeter process.

   Or launch the pre-provisioned ECS Fargate task, which uploads evidence to S3:

   ```bash
   scripts/experiment-1/run-ecs.sh
   ```

   Use `WAIT_FOR_COMPLETION=true` to wait, verify the ECS exit code, monitor the
   HPA, and upload the Kubernetes evidence beside the JMeter archive under
   `s3://<evidence-bucket>/jtl/<run-id>/`.

6. Capture Kubernetes/HPA evidence and optionally combine it with a local run:

   ```bash
   SOURCE_RUN_ID=<run-id> scripts/experiment-1/collect.sh
   ```

   The archive includes non-sensitive Terraform outputs, Git revision/status,
   effective Helm values and manifest, requested and resolved pod image digests,
   CPU/HPA snapshots, events, and the last three hours of API Gateway access
   logs. To inspect the same managed log stream directly:

   ```bash
   /opt/homebrew/bin/aws --profile solventa-lab --region us-east-1 logs tail \
     "/aws/apigateway/$(terraform -chdir=infra/terraform/exp1 output -raw cluster_name)" \
     --since 3h --format short
   ```

7. Remove only the Helm release after evidence is safe:

   ```bash
   CONFIRM_TEARDOWN=solventa-exp1 scripts/experiment-1/teardown.sh
   ```

   Terraform-managed AWS resources are never destroyed by this script. Namespace,
   runtime Secrets, and shared Metrics Server removal are separate opt-in flags.

## Safety controls

- Load targets must be explicitly allowlisted by hostname.
- API Gateway traffic is always SigV4 signed. Unsigned mode is rejected unless
  `VALIDATION_MODE=true` and the target is localhost.
- Production protocol parameters are fixed at a 50-RPM warm-up, immediate 500-RPM
  aggregate step, 50 partners, 20 reused profiles per partner/run, 300 seconds
  warm-up, 1,800 seconds measured, 300 seconds cooldown after every run, and
  a 30-second post-cooldown HPA observation before each of the three runs ends.
- Calibrate `QUOTE_CPU_ITERATIONS` and `PROFILE_CPU_ITERATIONS` before recording
  evidence. The initial `150000` is a hypothesis, not a measured constant. Freeze
  both values for all three runs; the intended signal is HPA `2 -> 3` while p95
  remains within the experiment threshold.
- Database/cache credentials and temporary AWS credentials are never printed,
  logged, persisted in JTL, or committed. Application pods receive only the
  read-only runtime DB URL and the authenticated Redis URL.
- `teardown.sh` requires an exact confirmation value and leaves AWS infrastructure
  intact.
