# pagos-service — Pagos (Órdenes Idempotentes)

Consumes `ordenes-pagos.fifo` (published by reclamos-service's Transactional
Outbox), applies the Inbox pattern (unique constraint on `operation_id`) to
confirm each payment order exactly once, and registers a single simulated
ledger effect per order. Terminal service in the pipeline — it does not
publish anywhere else.

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host/pagos?sslmode=verify-full&sslrootcert=/etc/ssl/certs/aws-rds-global-bundle.pem` |
| `SQS_ORDENES_PAGOS_URL` | Source queue this service consumes |
| `AWS_REGION` | Default `us-east-1` |
| `ENABLE_CONSUMER_THREAD` | Default `true` |
| `SQS_WAIT_TIME_SECONDS`, `SQS_VISIBILITY_TIMEOUT_SECONDS` | Tuning knobs, see `app/config.py` |

## Idempotency

`app/repository.PagosRepository.process_order` does the same
`INSERT ... ON CONFLICT (operation_id) DO NOTHING RETURNING ...` pattern as
reclamos-service: a redelivered `operation_id` always returns the original
`orden_id`/`monto` and never creates a second `ledger_simulado` row.

## Known gaps before this can run for real

- **Database not provisioned**: this service expects a `pagos` database (plus
  a role with privileges on it) to already exist in the shared RDS instance
  `solventa-exp1-postgres`. `infra/terraform/exp2/` does not create it yet.
- **Kubernetes namespace/Helm chart**: `solventa-exp2` namespace and a
  `deploy/helm/solventa-exp2/` chart (with a `pagos` ServiceAccount annotated
  with the `solventa-exp2-workload` IRSA role ARN) do not exist yet.

## Scaling

`gunicorn.conf.py` pins `workers = 1` — the consumer thread runs once per pod,
started from `create_app()`. KEDA scaling replica count is how this service
scales, not in-pod worker count.
