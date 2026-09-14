# Experiment 1 load test

The JMeter 5.6.3 plan implements the agreed **baseline**, not the original
50,000-RPM hypothesis:

- a 1-minute warm-up at **50 RPM**, followed by an immediate step to exactly
  **500 requests per minute total** (8.33 RPS), not 500 RPM per partner;
- 50 concurrent threads representing `partner-01` through `partner-50`;
- `POST /api/v1/cotizaciones`, HTTP keep-alive, redirects disabled, and no
  automatic retries;
- AWS SigV4 authentication for the API Gateway `execute-api` service; unsigned
  requests are accepted only in an explicit localhost validation mode;
- JSON contains only synthetic, non-authentication labels:
  `partner_ref` and `profile_ref`; the server creates `request_id`;
- 20 deterministic profiles per partner (1,000 values across all partners in a
  run), reused between warm-up, measurement, and cooldown for observable cache
  hits;
- an 8-minute measured window whose JTL begins at the 500-RPM step;
- three complete runs, each writing a measured JTL and an HTML dashboard, then a
  30-second cooldown at 50 RPM, followed by a 30-second observation interval.
  Each run therefore lasts 10 minutes.

The request body is computationally useful even though all data are synthetic:

```json
{"partner_ref":"partner-01","profile_ref":"profile-00000000-0000-4000-8000-000000000101"}
```

## Interpretation boundary

This baseline can validate the deployed path at 500 RPM, error rate, latency,
resource consumption, deterministic dependencies, and whether an HPA happens to
react at this load. It **cannot** validate 50,000 RPM, the documented 100x scaling
hypothesis, endurance, complete HPA scale-down, or strong statistical fairness
among partners. At 500 RPM split over 50 partners, each partner receives only
about 10 requests/minute; partner-level p95 comparisons therefore have limited
statistical power in an 8-minute measured window.

Do not claim the experiment-1 hypothesis is confirmed from these runs. A later,
separately authorized load ladder is required for the 50,000-RPM claim.

## Runner

The image is reproducible: JMeter is pinned to `5.6.3` and its Apache SHA-512 is
verified during the build. It runs as an unprivileged user and optionally uploads
an encrypted archive to S3 using the ECS task role—never static access keys.
The local runner receives only temporary credentials exported from
`solventa-lab`; authorization headers and session tokens are excluded from JTL.
The runner, quotation image, and profile image are all built for `linux/amd64`,
matching both the current Colima context and the EKS/Fargate runtime platform.
The local orchestration starts one container per run and exports a fresh session
before each container; every session must remain valid for that run plus a
two-minute safety margin. Fargate keeps all three runs in one task and refreshes
its task-role credentials before every run.

Each evidence run uses a disjoint seeded profile range without flushing Redis:
run 1 uses profiles 1–20, run 2 uses 21–40, and run 3 uses 41–60 for every
partner. This gives every run the same cold-to-warm cache transition while its
own warm-up, measured phase, and cooldown reuse the same keys.

The JTL explicitly excludes request/response headers, sampler data, and response
bodies. It retains only timings, status metadata, byte counts, and `partner_ref`.
A Groovy assertion validates the complete business response schema.

Local results are written below `load-tests/results/`, which is ignored by Git.
Use the scripts in `scripts/experiment-1/` rather than invoking JMeter manually so
the warm-up and three-run protocol cannot be accidentally changed.
