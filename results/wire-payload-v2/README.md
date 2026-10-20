# Wire Payload v2: historical serialization and controlled-link outputs

This is a communication engineering review of already-used historical synthetic uploads, not a new detector experiment or measured radio study. Main KEY period16; predeclared8/32 sensitivities; all native methods/points retained. [Protocol and technical report](../../docs/WIRE_PAYLOAD_V2.md).

- `audit/`: all10,800 frozen streams' health occupancies, state/score/flag transition rates, per-scenario repetition and optimistic health-only bounds. Initial health is charged independently for every run.
- `test/summary.csv`: every method/point ×3periods ×7link profiles, actual sent bytes, discarded vs received-but-unreconstructed business records, all framing/identity/initialization/refresh expenses.
- `test/recovery_summary.csv`: completed-episode mean/P95/max waits and separately censored tails, for v1 and v2. Waits begin at the first missing business record, not a later point chosen to reduce latency.
- `test/per_run.csv.gz`, `recovery_episodes.csv.gz`: detailed per-run link accounting and every recovery episode, including censored tails. Ordinary CSV inside gzip, deterministic header timestamps.
- `test/invariants.csv.gz`: original per-run detector metrics, v1 reconciliation, unchanged sender output and input hashes. Sender invariance is separate from receiver records lost over the link.
- `test/by_seed.csv`, `by_scenario.csv`: complete breakdowns; `paired_uncertainty.csv`:30seed-cluster paired bootstrap95% intervals,10,000 replicates.
- `test/frame_sizes.csv`, `frame_histograms.csv`: exact v1/v2 no-loss size distributions for all inherited points and periods.
- `test/trace_excerpt.csv`: public per-frame example across all link profiles.
- `test/cost_recovery.png`: actual application bytes and missing-information tradeoff.
- `test/manifest.json`, `verification.json`: exact source/version/input/output fingerprints and invariant/target verdicts.
- `checks/`: actual software/upstream checks and protection of the entire v1 baseline tree.

Full per-frame link logs are intentionally kept under ignored `results/traces/wire-payload-v2/test/link_events.jsonl.gz`, independent of all original archives. The manifest records their SHA256, byte size,8,047,116 expected event rows for the complete matrix, and columns. Each line groups one original run/period/profile, retaining each transmitted frame's hex bytes, sequence, session, discard/reception, exact decode/wait/recovery outcome. Lost records are never backfilled after a snapshot.

Reproduce using an unused output/log directory:

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q -rx
.venv/bin/python scripts/audit_wire_health.py --output results/scratch/health-audit-new
.venv/bin/python scripts/benchmark_wire_v2.py \
  --archive /absolute/path/to/original/results/traces/test \
  --output results/scratch/wire-v2-review-new \
  --log-dir results/scratch/wire-v2-logs-new
```

`--smoke` uses24 archived runs only, with an explicit partial label; it cannot decide the full-test challenge target. Neither script runs a policy, modifies original archives, nor overwrites an existing output directory. For archive reconstruction in an isolated original-source checkout, follow the preserved [v1 instructions](../../docs/WIRE_PAYLOAD_EXPERIMENT.md#reproduce-without-touching-historical-results). Match every original archive SHA; do not bypass a mismatch.

Independent full-log count/byte reconciliation and selected status/hash replay:

```sh
.venv/bin/python scripts/verify_wire_v2_results.py \
  --results results/scratch/wire-v2-review-new \
  --output results/scratch/wire-v2-verification-new.json
```

The simulated link has no ACK/retry channel. A snapshot only restores current state. It cannot recover dropped or rejected past measurements/event flags. CRC is not authentication. Durable session allocation, authenticated identity, transport framing and actual link/current measurements are prerequisites for physical deployment claims.
