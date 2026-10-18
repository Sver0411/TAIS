# IRB-1: independent same-quantity reference with shared hard caps

Synthetic information-value study. GateOnly remains the primary competitor; original TAIS and all previous NO-GO reports are preserved. No real environment, natural-fault diagnosis, measured radio bytes or energy result is claimed.

[Preregistration and pre-data P1 clarification](../../docs/INDEPENDENT_REFERENCE_BUDGET_PREREGISTRATION.md) · [Full87-case specification](../../configs/independent-reference-budget.json)

Both sensors measure temperature in Celsius, independent σ0.08C noise; modeled reference responseα1/.5/0. The63 core cases include48mixed,12event-only,2drift-only and1clean.24 declared missing/static-bias stress cases are descriptive. Strict twin worlds reuse existing drift-only/event-only matched-rampα0 cases; they are not additional duplicated samples.

`budget-lock.json` records actual development mean calibration over1,260uncapped GateOnly runs:94.1238095238reads,45.5793650794requests,7775.4857142857JSON bytes/run. Fixed common caps, floored after scaling:

| Level | A+B reads | Issued uploads | Actual UTF-8 JSON bytes |
| --- | --- | --- | --- |
| 0.75 | 70 | 34 | 5831 |
| 1.00 | 94 | 45 | 7775 |
| 1.50 | 141 | 68 | 11663 |

Every B baseline/candidate/followup read occupies the same physical-read budget as A; missing reads cost one too. Proposed-but-denied uploads are distinct from issued application requests. Exact complete frames are admitted atomically, with no dropped fields or free synchronization. Common caps do not mean equal actual usage.

Candidates are retained when B is flat or absent. **Unresolved is neither correct source attribution nor a false committed environment declaration.** Raw unmatched candidate metrics retain every candidate. Committed environmental metrics use ReferenceGate supported reports versus the original GateOnly/TAIS reports. Candidate Recall NI and supported Recall NI are both required; declining to classify most true events cannot pass. No reference-only fault diagnosis is invented. C11 scenario claims, partial environmental support, unresolved rate and unique-cause ambiguity are separate.

## File roles

- `seed-audit.json`, `history-protection.json`: before-run allocation300–319/320–339/340–399, full accessible-history/ignored-file audit and protected-byte inventory pointer; original0–299 reserved.
- `checks/`: actual609-pass/2-existing-xfail full suite,110new passing tests, retained initial108-pass/2-fail debug-field parity log and correction notes.
- `calibrate/`: actual1,260uncapped runs and independently recomputed JSON counts; no detection outcome enters budget calibration.
- `budget-lock.json`: source-pinned common budget vectors.
- `development/`, `validation/`, `test/`: exclusive start markers, full metrics, candidate/support event matches and all trace/replay checksums.
- `final-lock.json`: committed source/cap/calibration/verification hashes before final access.
- Each split's `analysis/summary.csv`: all methods,budgets,87cases and declared groups; event-free Recall=N/A.
- Final paired intervals and27primary corrected intervals, deletion checks and decision retain favorable/unfavorable results at every budget; no interpolation, threshold search or test-based selection.
- Observational-equivalence CSV compares entire A/B streams and complete per-method/budget outputs for both durations.

Raw deterministic gzip artifacts remain only under ignored `results/traces/independent-reference-budget/`. They preserve latent/noisy/intervened arrays, independent truth, reference-response metadata, main records, reference reads, candidate episodes, actual JSON envelopes and every accepted/rejected budget ledger event. Their SHA256s are in split manifests. The657 original tracked files,236,199 old ignored files, pinned upstreams and external raw-file stat signatures are protected. No raw workbook was modified.

## Reproduction in fresh roots

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q -rx

# Use new destinations: committed result directories refuse overwrite.
IRB_RESULTS=results/independent-reference-reproduction
IRB_RAW=results/traces/independent-reference-reproduction
.venv/bin/python scripts/run_independent_reference_budget.py --phase calibrate --workers 4 \
  --results-root "$IRB_RESULTS" --archive-root "$IRB_RAW"
.venv/bin/python scripts/verify_independent_reference_budget.py --phase calibrate \
  --root "$IRB_RESULTS" --output "$IRB_RESULTS/calibrate/verification.json"
git add "$IRB_RESULTS"
git commit -m 'reproduce IRB-1: lock verified calibration before execution'
for IRB_PHASE in development validation; do
  .venv/bin/python scripts/run_independent_reference_budget.py --phase "$IRB_PHASE" --workers 4 \
    --results-root "$IRB_RESULTS" --archive-root "$IRB_RAW"
  .venv/bin/python scripts/analyze_independent_reference_budget.py --phase "$IRB_PHASE" --root "$IRB_RESULTS"
  .venv/bin/python scripts/verify_independent_reference_budget.py --phase "$IRB_PHASE" \
    --root "$IRB_RESULTS" --output "$IRB_RESULTS/$IRB_PHASE/verification.json"
done
.venv/bin/python scripts/analyze_independent_reference_budget.py --freeze --root "$IRB_RESULTS"
git add "$IRB_RESULTS"
git commit -m 'reproduce IRB-1: freeze verified final inputs before test'
.venv/bin/python scripts/run_independent_reference_budget.py --phase test --workers 4 \
  --results-root "$IRB_RESULTS" --archive-root "$IRB_RAW"
.venv/bin/python scripts/analyze_independent_reference_budget.py --phase test --root "$IRB_RESULTS"
.venv/bin/python scripts/verify_independent_reference_budget.py --phase test \
  --root "$IRB_RESULTS" --output "$IRB_RESULTS/test/verification.json"
```

Existing destinations refuse overwrite. For reproduction use an isolated checkout with fresh `--results-root`/`--archive-root`, write and commit its locks before final. These commands reproduce old noise, not new evidence. After completion0–399must be treated as used/reserved. This study's thresholds were fixed from existing rules (1.2C displacement,10s minimum persistence); development only sets resource caps. Development/validation can execute independently under the same committed cap lock; final is withheld until both verify.

Conditional delay excludes missed events; no-event ratios are N/A. Scenario-level C11 fault claims are heuristic declarations evaluated against known injection presence, not calibrated fault probabilities or physical-cause proof. Missing B, unsupported local changes and cap exhaustion remain explicit. Runtime failure preserves partial evidence and must never be relabeled complete.

`--history` is an additional original-workspace integrity check against the pre-existing ignored archives; its full inventory stays local. A fresh clone can regenerate and independently verify all new artifacts using the commands above without possessing old ignored archives. The published manifests pin original artifact hashes; path/session metadata will differ in a new checkout. The presentation helper reads the original published results and creates new files exclusively, so do not rerun it over an existing report.
