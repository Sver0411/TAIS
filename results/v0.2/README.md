# v0.2 research artifacts

All v0.1 results remain in their original directories. This tree contains new forensics, then development/validation and fresh test outputs. Reports: [failure analysis](../../docs/FAILURE_ANALYSIS_V0.1.md), [preimplementation design](../../docs/V02_DESIGN.md), and later `docs/RESEARCH_REPORT_V0.2.md`.

From the repository root (Python venv and dependencies as in the main README):

```sh
.venv/bin/python scripts/v02_seed_audit.py   # run BEFORE new test seeds are opened
.venv/bin/python scripts/v02_identifiability.py
.venv/bin/python scripts/v02_forensics.py   # requires regenerated v0.1 test archives
.venv/bin/python -m pytest -q
.venv/bin/python scripts/v02_run.py --split development --workers 4
.venv/bin/python scripts/v02_summarize.py --split development
.venv/bin/python scripts/v02_run.py --split validation --workers 4
.venv/bin/python scripts/v02_summarize.py --split validation
# Review/freeze required before --split test; see V02_DESIGN.md.
.venv/bin/python scripts/v02_run.py --split test --workers 4
.venv/bin/python scripts/v02_summarize.py --split test
.venv/bin/python scripts/v02_verify.py --split test --traces --replay-one
```

Completed result manifests protect their directories against overwrite. Use a fresh checkout/remove only your explicitly disposable regeneration outputs to repeat, never delete published evidence. Canonical compressed signals, counterfactuals and sampled decisions live under ignored `results/traces/v02-<split>`; every file hash is retained in the split manifest. Representative v0.1 forensic JSONs/PNGs are small and versioned. Event rows, raw metric rows, all operating points, paired bootstrap CIs and two tradeoff plots are versioned. Reconstruct full traces using exactly the recorded source commit/config; source hashes and archived run hashes verify equivalence.

Counts are application requests and serialized envelopes, not measured RF energy. Truth and fault annotations only enter offline evaluation. Information-erased same-channel cases, sequential spikes, stable-offset blind spots and absence of real-greenhouse validation remain explicit.

## Reproduce without overwriting committed evidence

The source commits precede their result commits. In a **separate disposable clone**, check out `1dbc102a70e44011941fd2358af4f485f8f457ac` for development/validation, or `14af61952229a6da6cda40c8ee7257f9582b4b40` for the final run, then update submodules and install the locked environment. Those commits do not yet contain their corresponding completed result directories; the runner's overwrite guard therefore permits exact regeneration. The main checkout and historical artifacts stay intact.

```sh
git clone --recurse-submodules https://github.com/Sver0411/TAIS.git TAIS-v02-replay
cd TAIS-v02-replay
git checkout 14af61952229a6da6cda40c8ee7257f9582b4b40
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q
.venv/bin/python scripts/v02_run.py --split test --workers 4
.venv/bin/python scripts/v02_summarize.py --split test
.venv/bin/python scripts/v02_verify.py --split test --traces --replay-one
```

For v0.1 forensic regeneration, first reproduce its legacy test archives at the recorded legacy source; the committed representative JSONs and event CSV remain inspectable without that large download/regeneration. The old source is in this Git history, not in an unpinned external branch.

Fresh original upstream reproduction is also retained under `baseline/`, with the exact wrapper in `baseline-reproduction-command.txt`. The wrapper changes only the evidence destination of the existing audit script; every original upstream test, generator, analysis and C compiler command runs unchanged in temporary copies.

## Completed outcome

59,850 scored runs completed:8,550 development +8,550 validation +42,750 fresh final. Final50,700 archive hashes and five fresh policy replays passed. Source14af619 and frozen config/algorithm were retained unchanged. Tests:125 passed,1 strict known expected failure for blocked rearm,0 unexpected failures. All19 operating points and both tradeoff figures are available. The.75 same-channel gain is small and late; other points show no gain. See [interpretation](../../docs/V02_INTERPRETATION.md), [report](../../docs/RESEARCH_REPORT_V0.2.md), and [execution record](../../docs/V02_REPRODUCIBILITY.md).
