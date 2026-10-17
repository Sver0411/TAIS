# v0.2 execution and integrity record

Work is on `research/v0.2-same-channel-recall`; `main` and both pinned submodules remain unchanged. No new code is placed in the AdaptiveSense working tree. The original TAIS v0.1 modules/config/scripts and all old result directories are retained.

## Ordered source history

- `dccf2f0`: passive forensic tools, event records, representative plots, old-seed identifiability proof.
- `8222873`: complete mechanism/experiment design, committed before algorithm implementation.
- `1dbc102a70e44011941fd2358af4f485f8f457ac`: implementation and original125-pass local test log; actual development/validation executable source.
- `2fd083790b4565498ea1cdb625946270b750859d`: CI portability fix to a test, no policy/config change. Retains the previous CI124-pass/1-failure log. Adds generated baseline source hashes.
- `14af61952229a6da6cda40c8ee7257f9582b4b40`: completed development/validation results, pretest review and executable/config hash freeze. Actual final-run source; seeds50–99 were unopened before this commit.

Each split manifest records full SHA, actual argv, Python/platform, seeds, scenarios, executable/config SHA256, metric/event CSV hashes and every canonical compressed archive hash. Output order is deterministic even when workers finish out of order. Parallelism is separate processes, avoiding shared monkeypatch state. `v02_verify.py --traces --replay-one` verifies recorded source against Git objects, every archive, both CSVs, and five fresh policy replays.

## Actual checks and retained failures

- New local suite: `.venv/bin/python -m pytest -q`:125 passed,0 failed. Logs `tests-initial.log` and `tests-portable.log`.
- New GitHub CI1dbc102:124 passed,1 failed because a depth-1 checkout has no68af4b6 object. The test was corrected to use the committed immutable source hash inventory; no test was deleted. Failure log retained in `ci-39013521047-failure.log`.
- Corrected CI2fd0837 and freeze CI14af619 completed successfully, including the full125-test suite and unchanged upstream reproduction/smoke workflow. [Corrected run](https://github.com/Sver0411/TAIS/actions/runs/39013800827), [freeze run](https://github.com/Sver0411/TAIS/actions/runs/39013995064).
- Fresh local upstream audit, output redirected **only** to `results/v0.2/baseline`: AS235 tests,69 configuration checks, SensorTrust27 Python tests,21 C tests/404 checks passed. Exact wrapper and all original argv/outputs are retained. Both baseline CSV hashes match the pinned originals and previous v0.1 reproduction.
- V0.1 local tests67 passed;18,900 old-test archive hashes checked and one fresh replay matched.
- Passive forensic observer4,050 results exactly equal archived originals;900 labels x3 policies=2,700 event rows.
- Every legacy comparator metric row in the new development/validation matrices is exactly equal to the old CSVs:5,850+5,850 rows. This includes costs, diagnosis and reconstruction, not merely recall.

The frozen SHA inventory covers experiment implementation/configs. Tests, documentation and publication tooling are separately committed; no post-final policy/config change is permitted. Cross-platform full-matrix bit identity is not claimed; exact regeneration is checked in the recorded reference environment. CI additionally tests Linux/Python3.14.8, while full local matrices use macOS/Python3.14.7.

## Commands and non-destructive reproduction

See [artifact README](../results/v0.2/README.md) for exact commands and pre-result source checkouts. Completed manifests are protected against overwrite; a disposable clone at the recorded source SHA can regenerate its corresponding not-yet-committed results. Do not run a new experiment by editing a published result CSV.

Signal/noise/fault schedules are common across methods; clean counterfactual replays are archived separately and used offline only. All full traces are excluded from Git and regenerable. Every operating point and unfavorable scenario remains in raw metrics and summaries. Bootstrap draws resample whole paired seed clusters (2000,RNG731); descriptive95% CIs and their actual valid-pair counts are stored. Conditional delay CIs use detected pairs, with misses separately reported.

No real greenhouse file, embedded runtime/CPU/flash benchmark, radio delivery model or measured current is added in v0.2. Previous403 evidence remains available; raw-field/missingness/greenhouse replay validation remains pending.

## Post-final checks and limitations

After the frozen run, all42,750 metrics and28,500 event-method records were retained;50,700 archive hashes and five fresh policy replays passed. `inspect_v02_results.py` adds offline explanation only. A strict expected-failure regression was added for the newly observed seed91 blocked-rearm failure; final local suite125 passed,1 xfailed,0 unexpected failures. This does not replace or erase the earlier125-pass logs. No experiment implementation/config hash changed after final opening. See [interpretation](V02_INTERPRETATION.md).
