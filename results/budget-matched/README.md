# BM-1 budget-matched policy evaluation

**Final decision: NO-GO.** B0.75/B1.00 matched within1% samples and uploads but increased fault-induced false reports. B1.50 reduced them5% yet failed the sample matching limit (1.0298%); no tolerance was changed.

[Preregistration](../../docs/BUDGET_MATCHED_EXPERIMENT_PREREGISTRATION.md) · [Technical report](../../docs/BUDGET_MATCHED_EXPERIMENT_REPORT.md) · [Plan](../../configs/budget-matched.json)

- `seed-audit.json`: before-run accessible-history audit, reserved0–149, no150–199collision; complete compressed path inventory is local with hash.
- `development/`: seeds150–159,9,000actual runs, all9multipliers per main method and2context baselines; full grid summaries.
- `validation/`: seeds160–169,9,000actual runs, same fixed grid, no expansion.
- `selection_candidates.csv`: every81real pair per budget, feasibility and resource-only ranking.
- `selection.json`: committed pre-test3pair lock, all calibration/source hashes,8unique final configurations. No outcomes used for selection.
- `test/`: seeds170–199,10,800actual scored runs, all45scenarios; `run_started.json` exclusive start marker, metrics,event matches and manifest.
- `test/analysis/summary.csv`: micro metrics, all method/point/group outcomes, fault diagnosis, delay, costs and reconstruction.
- `paired_intervals.csv`:6,222paired interval rows,95% and fixed-family98.3333% bounds, seed clustering, valid-draw counts.
- `absolute_intervals.csv`:14,152absolute interval rows, every actual final point/group.
- `robustness_deletions.csv`:249predefined leave-one-seed/scenario/fault-class checks.
- `decisions.csv`, `decision.json`: every gate and the final NO-GO; unmatched1.5positive findings retained.
- `common_matched_delay.csv`, `common_matched_event_pairs.csv`: co-detected event delay with survivor-bias context.
- `budget_tradeoff.png`: all frozen final configurations and all3budget contrasts; no interpolation used for matching.
- `checks/`: actual software logs, raw-metric recomputation and historical protection proof.

All scientific split artifacts use new paths under ignored `results/traces/budget-matched/{development,validation,test}`; manifests pin all34,890gzip outputs (including2,250signals and3,840clean counterfactuals). Old521tracked files and150,108ignored experimental files were protected by a full-byte guard. This work neither modifies protocols nor claims radio energy savings. It is a fresh-noise test under the same synthetic generator, not external real-environment validation. Seeds0–199 are now used/reserved.

## Reproduce without overwriting results

Initialize submodules, install the locked environment, and use fresh results/archive roots. The scripts always refuse existing phase outputs; there is no force/rerun-final flag. The actual final run used the committed selection at7600f2c, once per unique operating point. Offline verification rereads saved results and never invokes a scheduler.

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q -rx

# Exact frozen final configuration reproduction (not fresh evidence):
.venv/bin/python scripts/run_budget_matched_experiment.py --phase test \
  --selection results/budget-matched/selection.json \
  --results-root results/scratch/budget-reproduction \
  --archive-root results/traces/budget-reproduction --workers 4
.venv/bin/python scripts/verify_budget_matched_experiment.py --phase test \
  --root results/scratch/budget-reproduction \
  --output results/scratch/budget-reproduction-verification.json
```

Actual staged commands before that final lock were:

```sh
.venv/bin/python scripts/run_budget_matched_experiment.py --phase development --workers 4
.venv/bin/python scripts/analyze_budget_matched_results.py --phase development
.venv/bin/python scripts/run_budget_matched_experiment.py --phase validation --workers 4
.venv/bin/python scripts/analyze_budget_matched_results.py --phase validation
.venv/bin/python scripts/analyze_budget_matched_results.py --select
# Commit selection.json plus both calibration CSVs/manifests before final execution.
.venv/bin/python scripts/run_budget_matched_experiment.py --phase test --workers 4
.venv/bin/python scripts/analyze_budget_matched_results.py --phase test
.venv/bin/python scripts/verify_budget_matched_experiment.py --phase test \
  --history results/traces/budget-matched/history-guard.json.gz \
  --output results/budget-matched/checks/final_verification.json
```

These historical commands will correctly refuse to overwrite committed results. For a complete recalibration reproduction use an isolated checkout/new roots and commit its identical resource-only selection before test. Do not rerun the seed allocator expecting150–199to remain unused: the before-run audit is immutable evidence, while completed results now reserve those seeds. A new research design needs a new seed audit rather than reuse of this final cohort.

Every split manifest contains command,Python/platform,code/source/config fingerprints,seed/case/config matrix and artifact SHA256. No individual measurement is treated as an independent statistical sample; all intervals resample whole original seed blocks.

The original analysis manifest contains a disclosed self-hash bookkeeping defect (its own entry hashes the initially empty file). All other listed hashes verify. `checks/delivery_integrity.json` is the supplementary completed-file checksum list, including the original manifest. Numerical results and frozen source files are unchanged; see the report.
