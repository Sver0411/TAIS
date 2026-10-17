# BLOCKED rearm reproduction and provenance

The baseline v0.2 branch is `96170fcb5df0534ca58e44827b2fcb214e7892ef`; the work is isolated on `research/blocked-rearm-fix`. Designb43e34c precedes implementation4958b6e. Development/validation run source4958b6e; final source8a73593, committed with the pretest review and37 executable/config/test SHA256 values before opening120–149. No policy/parameter selection is made from final results.

## Regeneration without overwriting evidence

Use a separate disposable clone at the source commit **before its corresponding results were committed**. Current completed result directories and partial outputs are protected by the runner. For final results:

```sh
git clone --recurse-submodules --branch research/blocked-rearm-fix https://github.com/Sver0411/TAIS.git TAIS-rearm-replay
cd TAIS-rearm-replay
git checkout 8a73593
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q -rx
.venv/bin/python scripts/rearm_run.py --split test --workers 4
.venv/bin/python scripts/rearm_summarize.py --split test
.venv/bin/python scripts/rearm_verify.py --split test --traces --replay-one
```

For development/validation, use4958b6e, then the corresponding split arguments. To regenerate the combined report, all three completed split directories must be available; `rearm_report.py` generates tables, with final interpretation documented separately. Do not relabel a regeneration of120–149 as a new independent validation. The archived seed audit is a **pre-run** audit; rerunning it after new seeds are used should detect that use rather than falsely certify freshness.

The recorded reference environment is macOS/Python3.14.7/Apple Clang17. CI also exercises Linux/Python3.14.8. Exact full-matrix byte regeneration is verified in the recorded environment, not promised universally across libm/platform versions. Dependencies are the existing lock; no new learning or scientific library was installed. Both submodule SHAs/licenses are unchanged.

## Verification meaning

Each manifest records actual source commit, command, environment, split seeds, suites/overrides, every source hash, metric/event CSV hashes and canonical gzip archive hashes. The verifier compares source to actual Git blobs, verifies every archive, and freshly replays five strategies on each of the two suites. Full signals/labels/counterfactuals/decisions are regenerated under ignored `results/traces/blocked-rearm/<split>`. Canonical gzip usesmtime0 and nonfinite/null normalization from the original helper.

The original v0.2 verifier independently passed its42750 metric rows,50700 archive hashes and five fresh replays after the repair. Frozen v0.1/v0.2 module/config hashes are listed in `results/blocked-rearm/frozen_baseline_sources.json`. A new strategy injects only an Evidence subclass while constructing the unchanged scheduler; no upstream or baseline scorer is rewritten. Constructor patches are process-local and restored; batch parallelism uses processes, not shared threads.

Original forced regression:1 actual failure retained. Untouched suite125 passed/1 xfailed. New tests initially66 passed/2 actual failures; both extra1.5 assertions remain unchanged as strict expected-failure boundaries, after confirming the same scoring failure in original TAIS. Repaired original regression passes normally; full local suite192 passed/2 expected failures/0 unexpected failures. Successful implementation CI also reproduces AS235 tests/69 configuration checks and SensorTrust27 Python tests plus21 C tests/404 checks. Logs are retained, not overwritten with fictitious passes.

Main and aligned recovery suites have common signals/noise/schedules per paired policy but are never pooled. The aligned suite deliberately schedules a sampled impulse followed by an event; it supports conditional transition verification, not natural fault prevalence. Every multiplier[.75,1,1.5], false-report cost and unfavorable scenario remains in the summaries. No physical current/radio-energy claim or new greenhouse validation is made.
