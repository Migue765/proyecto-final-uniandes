# Metrics Server values

These values are consumed by `scripts/experiment-1/deploy.sh` with the official
`metrics-server/metrics-server` chart version `3.14.0`. Two replicas keep HPA
metrics available during a pod disruption. The configuration intentionally does
not disable kubelet certificate verification.
