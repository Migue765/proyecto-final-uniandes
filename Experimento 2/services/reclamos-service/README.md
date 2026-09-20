# reclamos-service — Reclamos (Evaluación y Liquidación)

Consumes `entrada-parametrica.fifo`, applies the Inbox pattern (unique
constraint on `external_event_id`) to evaluate and settle each parametric
event exactly once, and publishes `SiniestroAprobado` to `ordenes-pagos.fifo`
via a Transactional Outbox. It also owns the read-only DLQ inspection
endpoints for both experiment 2 DLQs.

## Environment variables

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host/reclamos?sslmode=verify-full&sslrootcert=/etc/ssl/certs/aws-rds-global-bundle.pem` |
| `SQS_ENTRADA_PARAMETRICA_URL` | Source queue this service consumes |
| `SQS_ENTRADA_PARAMETRICA_DLQ_URL` | For `/internal/v1/dlq/*` |
| `SQS_ORDENES_PAGOS_URL` | Destination queue for the outbox publisher |
| `SQS_ORDENES_PAGOS_DLQ_URL` | For `/internal/v1/dlq/*` |
| `AWS_REGION` | Default `us-east-1` |
| `ENABLE_CONSUMER_THREAD` / `ENABLE_OUTBOX_PUBLISHER_THREAD` | Default `true`; set `false` to run a pure API replica (not needed today, but useful for isolating a bug) |
| `SQS_WAIT_TIME_SECONDS`, `SQS_VISIBILITY_TIMEOUT_SECONDS`, `OUTBOX_POLL_INTERVAL_SECONDS`, `OUTBOX_BATCH_SIZE`, `DLQ_PEEK_MAX_MESSAGES` | Tuning knobs, see `app/config.py` for bounds |

## Idempotency

`app/repository.py`'s `process_event` does one atomic
`INSERT ... ON CONFLICT (external_event_id) DO NOTHING RETURNING ...`: a win
means a genuinely new event (evaluate, settle, write the siniestro and the
outbox row); a loss means a duplicate or late redelivery, and the *original*
stored result is returned unchanged. No new siniestro or outbox row is ever
created on the duplicate path.

## Where the DLQ-bound "invalid" events come from

`app/models.ReceivedParametricEvent` nests `ParametricEventPayload`, which is
strict (`tipo_evento_parametrico` is a closed enum, all amounts are bounded
Decimals). A message that passed the Adaptador de Ingreso's HMAC/schema check
can still fail this stricter business schema. `app/consumer.py` treats that
`ValidationError` as non-transient: it does **not** delete the SQS message and
does **not** retry it itself — it just returns, and SQS's own
`maxReceiveCount`-based redrive (configured in `infra/terraform/exp2/sqs.tf`)
moves the message to the DLQ after enough redeliveries.

## Known gaps before this can run for real

- **Database not provisioned**: this service expects a `reclamos` database
  (plus a role with privileges on it) to already exist in the shared RDS
  instance `solventa-exp1-postgres`. `infra/terraform/exp2/` does not create
  it yet — needs a follow-up Terraform/psql pass.
- **Kubernetes namespace/Helm chart**: `solventa-exp2` namespace and a
  `deploy/helm/solventa-exp2/` chart (with a `reclamos` ServiceAccount
  annotated with the `solventa-exp2-workload` IRSA role ARN) do not exist yet.
- The DLQ inspection endpoints have no authentication of their own — they are
  only meant to be reachable from inside the cluster/namespace for now. Do not
  expose them through a public Ingress or API Gateway route without adding
  authentication first.

## Scaling

Both background threads (`ConsumerLoop`, `OutboxPublisher`) run once per pod,
started from `create_app()` — `gunicorn.conf.py` pins `workers = 1` so a
multi-worker pod never runs duplicate consumers. KEDA scaling this
Deployment's replica count therefore scales the consumer and the publisher
together, proportionally to the same pod count.
