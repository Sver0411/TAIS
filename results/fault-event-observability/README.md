# FO-1: fault–event timing benchmark

This is a new-seed **synthetic** timing/observability study of unchanged AdaptiveSense, GateOnly and original TAIS at multiplier1.0. It is not a new algorithm, natural-fault validation, spatial fusion, budget-matched comparison or radio/energy experiment. BM-1's NO-GO remains in force.

[Preregistration](../../docs/FAULT_EVENT_OBSERVABILITY_PREREGISTRATION.md) · [Versioned matrix](../../configs/fault-event-observability.json)

- `seed-audit.json`: before-run audit of accessible histories/ignored/external records; reserve0–199, allocate development200–219, validation220–239, final240–299.
- `history-protection.json`: SHA256 pointer to full local protection inventory,576 original files,185,135 old ignored files and both submodules.
- `checks/`: actual software logs and disclosed pre-development smoke failure/correction. Original partial smoke outputs were preserved; corrected smoke used a separate root.
- `development/`, `validation/`, `test/`: actual per-run metrics, event matches, per-report preceding intervals/health, exclusive start markers and complete artifact manifests.
- Each full split has93 cases ×3 methods per seed. Original45 scenarios are retained byte-identically;48 additions exclude the8 already-existing default timing cells.
- `final-lock.json`: source/config/protocol/calibration/verification hashes committed before final generation; no parameter search or outcome-based point selection.
- `analysis/summary.csv` inside each split: micro outcomes and all groups. No-event Recall is blank/N/A.
- Final `analysis/paired_intervals.csv`: whole-seed paired95%CIs. Non-primary groups are descriptive.
- `analysis/timing_interactions.csv`: all12 primary interactions,95% and Bonferroni99.583333% intervals; `interaction_deletions.csv` keeps all seed/scenario direction checks.
- `analysis/observational_equivalence.csv`: full observed-stream hashes versus distinct physical labels in original replacement/stuck same/no-event pairs. Equal outcomes do not resolve physical attribution.
- Final `analysis/*timing.png` shows every registered offset and both profiles/topologies; `primary_interactions.png` shows all primary contrasts.
- `verification.json`: every original and additional metric recomputed offline from saved artifacts, without invoking a scheduler again; all raw and analysis hashes checked.

Raw latent/noisy/intervened streams, labels, intervention/overlap metadata, replay records and clean counterfactuals live only under ignored `results/traces/fault-event-observability/`, with deterministic gzip SHA256 entries in each phase manifest. Raw data are not needed inside Git; exact commands regenerate them in fresh roots. Original real-data workbooks and prior results are untouched. Geometric overlap duration and actual shared1-Hz label/injection points are separate fields.

## Reproduce without overwriting evidence

Use the pinned submodules and locked Python dependencies. A C11 compiler is required for the actual SensorTrust core. Scripts insert the repository source path; for ad-hoc imports use `PYTHONPATH=src`.

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q -rx
```

Actual staged sequence (existing destinations refuse overwrite):

```sh
.venv/bin/python scripts/run_fault_event_observability.py --phase development --workers 4
.venv/bin/python scripts/analyze_fault_event_observability.py --phase development
.venv/bin/python scripts/verify_fault_event_observability.py --phase development \
  --output results/fault-event-observability/development/verification.json
.venv/bin/python scripts/run_fault_event_observability.py --phase validation --workers 4
.venv/bin/python scripts/analyze_fault_event_observability.py --phase validation
.venv/bin/python scripts/verify_fault_event_observability.py --phase validation \
  --output results/fault-event-observability/validation/verification.json
.venv/bin/python scripts/analyze_fault_event_observability.py --freeze
# Commit lock and all calibration/verification outputs before final access.
.venv/bin/python scripts/run_fault_event_observability.py --phase test --workers 4
.venv/bin/python scripts/analyze_fault_event_observability.py --phase test
.venv/bin/python scripts/verify_fault_event_observability.py --phase test --history \
  --output results/fault-event-observability/test/verification.json
```

For reproduction use an isolated checkout and fresh `--results-root`/`--archive-root`, run calibration, write/commit that root's lock, then run its final matrix. This is reproduction, not fresh evidence; after completion0–299 are used/reserved. Do not rerun the allocator expecting its original seeds still to be unused. Runtime failure retains partial artifacts and must not be relabeled a complete experiment.

Per-phase manifests pin source commit, all source/config/protocol hashes, exact commands/environment, methods/seeds/cases, clean-counterfactual paths and all archive/CSV checksums. Analysis manifests exclude themselves from their output list, avoiding the BM-1 manifest self-hash issue. Counterfactual increments in samples/uploads/bytes are operational intervention differences, not a unique causal decomposition into diagnostic effort. Flagged samples are annotations, not extra measurements automatically added to totals.
