# ingreso-service — Adaptador de Ingreso

HTTP ingress for Experiment 2's parametric events. Verifies an HMAC-SHA256
signature and the envelope schema, then publishes durably to
`entrada-parametrica.fifo`. See `experimento-2/PLAN.md` for the full
architecture and `experimento-2/flujo_request_e2.puml` for the request flow.

## Endpoint

`POST /parametricos/v1/eventos`

```json
{
  "external_event_id": "evt-000000000001",
  "timestamp": 1700000000,
  "partition_key": "riesgo-01",
  "signature": "<hex hmac-sha256>",
  "payload": {"tipo_evento_parametrico": "sismo", "magnitud": "6.1", "umbral_activacion": "5.0", "suma_asegurada": "100000"}
}
```

`signature` authenticates `external_event_id|timestamp|<payload as
sort_keys=True, compact-separator JSON>` — see `app/security.py` for the
exact canonicalization. Both `scripts/experiment-2/fire_corpus.py` and the
JMeter plan under `load-tests/jmeter-exp2/` must reproduce this exact
canonical form when signing.

Returns `202` with `{"external_event_id": ..., "status": "accepted"}`, or
`400` (`invalid_request` / `invalid_signature` / `stale_timestamp`). A
repeated `external_event_id` is **not** rejected here on purpose — see the
docstring in `app/security.py`.

## Environment variables

| Variable | Purpose |
|---|---|
| `SQS_ENTRADA_PARAMETRICA_URL` | `https://sqs.us-east-1.amazonaws.com/969325258550/solventa-exp2-entrada-parametrica.fifo` |
| `HMAC_SHARED_SECRET_ARN` | `arn:aws:secretsmanager:us-east-1:969325258550:secret:solventa-exp2/hmac-shared-secret-FuE0Ye` (see `infra/terraform/exp2/hmac-secret.tf`) |
| `AWS_REGION` | Default `us-east-1` |
| `SIGNATURE_MAX_SKEW_SECONDS` | Default `600` — generous on purpose, this is authenticity, not anti-replay |
| `MAX_REQUEST_BYTES` | Default `8192` |

## Known gaps before this can run for real

- **Resolved**: the Secrets Manager secret and the scoped
  `secretsmanager:GetSecretValue` statement (see
  `infra/terraform/exp2/hmac-secret.tf` and the `ReadOnlyHmacSharedSecret`
  statement in `iam.tf`) are applied. The secret value itself was generated
  by an ephemeral resource and never touched Terraform state or any plan
  output — retrieve it only via `aws secretsmanager get-secret-value` with an
  authenticated `solventa-lab` session, never by asking an assistant to print
  it.
- **Kubernetes namespace/Helm chart**: `solventa-exp2` namespace and a
  `deploy/helm/solventa-exp2/` chart (with an `ingreso` ServiceAccount
  annotated with the `solventa-exp2-workload` IRSA role ARN) do not exist yet.
