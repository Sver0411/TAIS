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
