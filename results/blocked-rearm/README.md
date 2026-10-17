# Minimal BLOCKED rearm repair

[Design](../../docs/BLOCKED_REARM_FIX.md). All original v0.1/v0.2 code, config, results and reports are retained. New policy name `V02-Rearm`, package `src/tais_rearm`; numerical sampling/trust/event parameters are unchanged.

Actual before-failure, after-success and boundary failures are in `diagnosis/`. The old multiplier1 xfail is now a normal repaired regression with unchanged TP==1 assertion; unfixed V02's failure and exact archived output are separately tested. Two added1.5 assertions remain strict xfails because original TAIS also fails the score/debounce requirement, despite the repaired latch being IDLE. No failing assertion was removed or relaxed.

Run from TAIS root in a locked Python environment:

```sh
.venv/bin/python -m pytest -q -rx
.venv/bin/python scripts/rearm_diagnose.py --after
.venv/bin/python scripts/rearm_plot.py
.venv/bin/python scripts/rearm_run.py --split development --workers 4
.venv/bin/python scripts/rearm_summarize.py --split development
.venv/bin/python scripts/rearm_verify.py --split development --traces --replay-one
.venv/bin/python scripts/rearm_run.py --split validation --workers 4
.venv/bin/python scripts/rearm_summarize.py --split validation
# Commit pretest review and FREEZE.json before the final command.
.venv/bin/python scripts/rearm_run.py --split test --workers 4
.venv/bin/python scripts/rearm_summarize.py --split test
.venv/bin/python scripts/rearm_verify.py --split test --traces --replay-one
.venv/bin/python scripts/rearm_report.py
```

Completed or partial run directories are protected; regenerate in a disposable checkout at the manifest's **pre-results source commit**, not by overwriting versioned outputs. The final source commit precedes final results and contains its hash freeze. Per-split manifest records actual SHA/env/argv/seeds, source hashes, metrics/event hashes and all canonical gzip archive hashes. Full signals, observations, labels, counterfactuals and decisions are under ignored `results/traces/blocked-rearm/<split>`. Every policy receives only actually sampled observations; full signals/labels are offline only.

Main45 scenarios retain random jitter; aligned_recovery6 scenarios set only fault_jitter_s=0. They are separately summarized and never pooled. The latter is a deliberate recovery exposure, not prevalence evidence. Seeds100–109 development,110–119 validation,120–149 final; old seeds0–99 are used/diagnostic. All13 method/threshold points retained, no parameter search. Counts are application requests/serialized bytes, not radio energy. No new raw greenhouse data is supplied.
