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

The CPU calibration is `1200` synthetic hash iterations in quotation and `800`
in profile, matching the service config defaults. It is configurable from 1 to
1,000,000 through `quotation.cpuIterations` and `profile.cpuIterations`. Never
change it between the three evidence runs.

The previous default of `150000` was an uncalibrated placeholder. Measured on
2026-09-14 at roughly 850 ns per iteration in quotation and 1020 ns in profile,
it cost 281 ms of CPU per quotation. Because a request's hash chain is serial, a
single request against a 500m container limit could not finish in under 562 ms,
so p95 <= 250 ms was unreachable at any replica count — adding pods raises
throughput, never per-request speed. At `1200`/`800` the synthetic cost is about
1.8 ms per request, below the framework overhead itself.

One consequence to state in the verdict: at these values a 500-RPM step will not
move the HPA, because total demand is roughly 15 millicores. The honest reading
is "500 RPM fits within the initial capacity", not "elasticity was demonstrated".
Scaling appears in the phases that approach 50,506 offered RPM, where demand
reaches about 1.5 cores and the HPA needs more than the current `maxReplicas: 4`.

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
