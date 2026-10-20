# JO-1 actual results

**Overall NO-GO for replacing GateOnly.** Full improves Recall and drift false reports but worsens sampling, aggregate fault-induced reports and data age. See [concise report](../../docs/TAIS_JO_RESULTS.md) and [frozen protocol](../../docs/TAIS_JO_PROTOCOL.md). Old research and raw data remain unchanged.

- `development`: 500–509, nine fixed diagnostic cases, all candidate configurations (1620runs).
- `validation`: 510–519, all45cases, six methods at one development-selected setting (2700runs).
- `test`: 520–549, all45cases, six frozen methods (8100runs), once after commit4cd19c37f3848cadf3f5510bcdec68cdaf6abd71. Not real-world external validation.
- `selection.json` pins candidate selection and policy/runner/analysis/config hashes before held-out test.
- `seed-audit-raw.json.gz` preserves full82MB audit response losslessly; legacy engine auto-allocation/base labels are not JO allocation. `seed-audit.json` states actual500–549 split, zero collisions and raw hash.
- `development-attempt1` retains failed engineering attempt before parameter selection; no erased failure. `checks` contains real tests, importer blockage and protection audits.
- `core`: six used-seed20 scenarios, both default Gate and JO, actual bytes/receiver logs. No new independent evidence. `case-timeline.csv` and `timelines.png` explain those runs. Initial plot/export also retained.
- `test/analysis/summary.csv`: all45cases and all subgroups, no adverse cases omitted. Ordinary ageP95 field is mean per-runP95. `pooled_age.csv` is true pooled time-levelP95. Conditional event delays and diagnostic delays are conditional on detection.
- `paired_intervals.csv`: 5000 whole-seed paired draws,95% descriptive intervals, four predefined contrasts. No claim based only on favorable subgroup/multiple testing.
- `drift_diagnosis.csv`, `drift_false_phases.csv`, `pooled_age.csv`: descriptive post-freeze audits only, not selection criteria. Strict unmatched recovery phases do not equal counterfactual-induced counts.

Run Core from repository root (Python+C11compiler and pinned submodules):

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python examples/tais-core/run.py --policy tais-jo --scenario clean_short \
  --seed 20 --pace .01 --ui live --verify --out results/scratch/jo-new-01
.venv/bin/python -m pytest -q
```

Fresh engineering replication of already-used final seeds, to exclusive NEW paths:

```sh
.venv/bin/python scripts/replay_joint_frozen.py --phase test \
  --output-root results/scratch/jo-replication-01 \
  --archive-root results/traces/jo-replication-01
```

The original benchmark refuses an existing phase and validates the selection's source fingerprints. Replication invokes the same frozen runner/config/analysis, preserves original paths and does NOT create a new independent test. Full source/noise/truth/fault records and exact frames are generated under the new archive; no original archive is needed. Standard final-test run used `scripts/benchmark_joint_optimization.py --phase test`, followed by `scripts/analyze_joint_optimization.py --phase test`. Original archive is local ignored `results/traces/tais-joint`; summary manifests pin artifact hashes. `scripts/verify_joint_delivery.py` verifies that archive without rerunning a policy, writes an exclusive check file. Counterfactuals were evaluated by the frozen runner from the noisy pre-fault trace; their reports can be regenerated but were not separately archived. No claim that the independent artifact audit reverified those unarchived counterfactual decisions.

For independently verified numeric-seconds real records:

```sh
.venv/bin/python scripts/import_joint_csv.py --input /absolute/path/verified.csv \
  --output /tmp/jo-input-new.csv --time-semantics 'independently documented clock/availability meaning'
.venv/bin/python examples/tais-core/run.py --policy tais-jo --csv /tmp/jo-input-new.csv \
  --pace 0 --ui log --out results/scratch/jo-user-new-01
```

This does not repair Hull's unverified dates. No natural event/fault accuracy without independent labels. Source recordings, local software samples and transmitted snapshots are distinct; nothing here measures ADC savings or actual radio energy. APPbit32 is suspicion only, original C11 mask31/state/score remain distinguishable. Core default stays GateOnly.
