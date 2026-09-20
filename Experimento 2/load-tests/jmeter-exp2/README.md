# Experimento 2 — JMeter plans

**Scope boundary — read this first**: `smoke-ingreso.jmx` is an
exploratory/smoke tool for the Adaptador de Ingreso HTTP endpoint only. It is
**not** the official 250.000-request corpus test for the hypothesis in
`experimento-2/PLAN.md` — that test's evidence (throughput/latency under a
paced 10-minute window) is owned by `scripts/experiment-2/generate_corpus.py`
+ `scripts/experiment-2/fire_corpus.py`, which JMeter's threading model
doesn't control precisely enough to replicate. Use `smoke-ingreso.jmx` to
sanity check the Adaptador de Ingreso is reachable, signs/validates
correctly, and holds up under a quick exploratory burst.

`corpus-run.jmx` is different: it drives the *actual* 250.000-request corpus
(the same `corpus.jsonl` used by `fire_corpus.py`) through JMeter, one CSV
row per request, for a manual run that captures every request/response as
evidence of the base used and of the flow itself — see its own section
below. It complements, not replaces, the `fire_corpus.py`-based experiment
evidence (composition/DLQ/idempotency reconciliation is unaffected by which
tool fired the requests).

## smoke-ingreso.jmx

### What it does

Each iteration builds a synthetic parametric event, signs it with
HMAC-SHA256 (`hmac_sign.groovy`, same canonicalization as
`services/ingreso-service/app/security.py`:
`external_event_id|timestamp|<payload, sort_keys, compact JSON>`), and POSTs
it to `/parametricos/v1/eventos`. Every 10th iteration (per thread) is
deliberately tampered so its signature is well-formed but wrong, to exercise
the `400 invalid_signature` path — a `JSR223Assertion` checks the response
code matches whichever outcome (`202` or `400`) that iteration expects.

### Running

```bash
HMAC_SHARED_SECRET=<the same secret configured in ingreso-service> \
  jmeter -n -t smoke-ingreso.jmx \
    -Jthreads=5 -Jramp_seconds=5 -Jduration_seconds=60 -Jtarget_rpm=300 \
    -Jtarget_url=http://<ingreso-service host>/parametricos/v1/eventos \
    -l results.jtl
```

Or open it in the JMeter GUI (`jmeter -t smoke-ingreso.jmx`) for interactive
exploration; `-J` properties above have the same defaults baked into the
plan (`threads=5`, `ramp_seconds=5`, `duration_seconds=60`, `target_rpm=300`).

### Verified

Run locally end-to-end against a throwaway HTTP server (`jmeter -n`, 2
threads, 8s, ~150 samples): 0 script errors, and the tamper/assertion logic
triggers on ~1/10 iterations as designed (those showed up as assertion
failures only because the throwaway server always answered `202` — a real
Adaptador de Ingreso would answer `400` for those and the assertion would
pass).

## corpus-run.jmx

### What it does

One CSV Data Set Config row per request, walking `corpus_export.csv`
sequentially exactly once (`recycle=false`, `stopThread=true`,
`shareMode=shareMode.all`, so all threads share one cursor through the
file — no row fires twice, none are skipped). Per iteration:

1. `build-event-from-csv.groovy` takes the row's `external_event_id`,
   `partition_key`, and payload fields, and stamps a **fresh current
   timestamp** — never one baked in at corpus-generation time.
2. `hmac_sign.groovy` (unchanged, shared with the smoke test) signs it and
   builds the request body.
3. `POST /parametricos/v1/eventos`, response code/body/latency captured per
   request in the results file (`corpus_results.jtl`) for evidence.
4. A `JSR223Assertion` expects `202` on every request: with a fresh
   timestamp every time, there's no `stale_timestamp` failure mode, and
   `ingreso` accepts every category at the envelope level — only
   `reclamos`, downstream, decides business validity (`invalido` events end
   up in the DLQ, not rejected here).

Signing at request time instead of reusing `generate_corpus.py`'s baked-in
timestamps is what lets `corpus_export.csv` be run at any time without
`scripts/experiment-2/resign_corpus.py` — the signature covers the
timestamp, so it has to be computed together with it, not precomputed once
and replayed later.

### Generating the CSV

```bash
cd scripts/experiment-2
python3 export_corpus_csv.py --corpus corpus.jsonl --output ../../load-tests/jmeter-exp2/corpus_export.csv
```

Row order matches `fire_corpus.py`: every record except late redeliveries,
in file order, then the late redeliveries at the end.

### Before running: the database needs to be empty

`corpus_export.csv` uses the same `external_event_id`s as whatever DB state
already exists from a prior corpus run. If `reclamos_inbox`/`siniestros`
already have rows for those IDs, every request downstream of `ingreso` will
look like a duplicate. Truncate first if you want a clean read (admin
credentials, not the app runtime role — see `scripts/experiment-2/sync-db-secrets.sh
PRESERVE_ADMIN_DB_SECRET=true` to get a short-lived admin `Secret`, then
`TRUNCATE TABLE reclamos_inbox, siniestros, outbox_ordenes_pagos` in the
`reclamos` database and `TRUNCATE TABLE pagos_inbox, ordenes_pago,
ledger_simulado` in the `pagos` database; delete the admin `Secret`
afterwards).

### Running

`ingreso` is a `ClusterIP`-only Service — no public endpoint. Tunnel to it
first:

```bash
kubectl -n solventa-exp2 port-forward svc/solventa-exp2-ingreso 8080:8080
```

Then, in another terminal:

```bash
cd load-tests/jmeter-exp2
HMAC_SHARED_SECRET=<the same secret configured in ingreso-service> \
  jmeter -n -t corpus-run.jmx \
    -Jcorpus_csv=corpus_export.csv \
    -Jthreads=16 -Jramp_seconds=10 \
    -Jtarget_url=http://127.0.0.1:8080/parametricos/v1/eventos \
    -Jresults_file=corpus_results.jtl
```

Or open it in the JMeter GUI (`jmeter -t corpus-run.jmx`) to watch it run
interactively; same `-J` properties, same defaults (`threads=16`,
`ramp_seconds=10`).

**Concurrency is deliberately modest.** `port-forward` is not reliable under
sustained high concurrency — 16 threads is chosen to stay well clear of
that, since this run is about capturing a complete, correct evidence trail,
not about hitting a specific throughput target. At roughly that concurrency
expect somewhere in the neighborhood of 10-20 minutes for the full 250,000
rows, depending on `port-forward`'s own overhead.

### Reading the evidence

`corpus_results.jtl` (CSV format) has one row per request: timestamp,
response code, response body (`responseData`), latency, thread name, and
the assertion result. `corpus_export.csv` alongside it is the exact base
used, including each row's `category` (`valido_unico`, `duplicado_exacto`,
`reentrega_tardia`, `invalido`) for cross-referencing against
`corpus_manifest.json`'s composition.
