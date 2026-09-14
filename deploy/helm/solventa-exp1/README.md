# Solventa experiment 1 Helm chart

This chart deploys the real Kubernetes workload used by experiment 1 into the
`solventa-exp1` namespace:

- `quotation-service`: two initial replicas and fixed NodePort `30080`.
- `profile-service`: two initial replicas and an internal `ClusterIP`.
- deterministic WireMock for `POST /open-finance/v1/profiles`.
- one CPU HPA per application service: target `70%`, minimum `2`, maximum `4`,
  immediate scale-up decisions, and a `300s` scale-down stabilization window.
- an idempotent pre-install/pre-upgrade database seed Job that must complete
  before the application Deployments are created.

WireMock `3.13.2` is pulled by its pinned multi-architecture OCI digest, not by
a mutable tag alone.

Both application deployments request `250m` CPU and `256Mi` memory and are
limited to `500m` CPU and `512Mi` memory. They include readiness/liveness probes,
a read-only root filesystem, dropped Linux capabilities, and no mounted service
account token. Workloads are selected for the EKS `linux/amd64` nodes.

Ingress is default-denied at the namespace workload level. The quotation pod
admits port 8080 only from Terraform's static internal NLB source addresses
(the API Gateway VPC Link path),
Profile admits it only from quotation pods, and WireMock only from Profile pods.
Kubelet-originated health probes remain node traffic. Egress is intentionally
left to VPC security groups because DNS, RDS, Redis, and external AWS endpoints
use dynamic addresses.

The starting CPU calibration is `150000` synthetic hash iterations in each
service. This is deliberately configurable from 1 to 1,000,000 through
`quotation.cpuIterations` and `profile.cpuIterations`; calibrate it before the
recorded runs so the intended 500-RPM step moves the HPA from two to three pods
without violating p95. Never change it between the three evidence runs.

## Configuration boundary

RDS, Redis, image repositories/tags, TLS, and WireMock are configured in
`values.yaml` or injected by `scripts/experiment-1/deploy.sh` from Terraform
outputs. Credentials are deliberately absent. Application pods reference only
`solventa-exp1-db-runtime/database-url`; profile pods also reference
`solventa-exp1-redis-runtime/redis-url`.

`deploy.sh` invokes `scripts/experiment-1/sync-db-secret.sh` immediately before
the Helm operation. It streams the RDS master credential into
`solventa-exp1-db-admin` only for the seed Job, creates or preserves the generated
`solventa_runtime` credential, and creates an authenticated Redis URL from
Secrets Manager. The seed grants the runtime role read-only access; `deploy.sh`
always deletes the admin Secret and seed Job when it exits, including when Helm,
a rollout, or the script itself fails. A standalone secret sync removes the admin
Secret before returning; only the deployment wrapper may preserve it temporarily.

Client TLS terminates at API Gateway; HTTP inside the VPC is constrained by
security groups and NetworkPolicies. The application images do not implement
in-pod TLS, so the chart exposes no misleading TLS toggle. Redis uses
authenticated `rediss://`. PostgreSQL uses
`sslmode=verify-full` with the pinned AWS RDS global CA bundle included in the
application images.

## Metrics and tracing

`deploy.sh` installs the official Metrics Server chart `3.14.0` (Metrics Server
`0.9.x`) without the insecure kubelet TLS option. This makes CPU metrics available
to the HPA on EKS 1.36.

API Gateway X-Ray tracing is managed by Terraform. No in-cluster daemon or ADOT
collector is deployed: the current Flask images do not emit OTLP/X-Ray spans and
no pod identity is provisioned for trace writes. Deploying a collector would
therefore create a misleading, idle component. X-Ray is limited to the API
Gateway segment and is inspected separately in AWS; these scripts collect only
JMeter timings plus Metrics Server and Kubernetes snapshots.

## Static validation

```bash
scripts/experiment-1/validate.sh
```

The validation renders the chart without contacting the cluster.
