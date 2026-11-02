# MA-1: module ablation and unified evaluation

Synthetic software replay,2026-11-02. No hardware energy or wireless experiment.
Base `afa2b1719a14931f52129ae3699a03ceefcdb906`; frozen sources are stored here
because this base commit predates the new implementation.

*20 paired seeds900–919 ×54 conditions ×16 methods =17,280 scored runs.*
Counterfactual executions are additional offline evidence, not extra independent
replicates. Engineering uses exposed seed20 (864 runs); the initial completed
engineering/schema/plot review remains in [the original set](../module-ablation-engineering-attempt1/README.md).

[Protocol and audit](../../docs/MODULE_ABLATION_PROTOCOL.md) ·
[Chinese results interpretation](../../docs/MODULE_ABLATION_RESULTS_ZH.md) ·
[Japanese professor progress draft](../../docs/MODULE_ABLATION_PROGRESS_JA.md).

## Files and definitions

| File | Meaning |
| --- | --- |
| `freeze.json`, `sources/` | Complete effective source/config/protocol hashes and actual source snapshots before final execution |
| `seed-audit.json` | Current accessible manifests/configs checked for candidate seed collisions; scope explicitly limited |
| `test/manifest.json` | Status, complete method/case/seed matrix, source commit/hashes, package versions, output hashes, archive root |
| `test/metrics.csv` | Per(seed,case,method) raw observation summaries, primary and native scores, costs, ages, sampling, same-fault FNs, input/result/sample-time hashes |
| `test/events.csv` | Every truth event for both sender and independent receiver, including misses, actual report time, capped loss, coverage, event-onset ages |
| `test/inputs.csv` | Shared trace identities, event/fault counts and signal hashes |
| `test/archives.json` | Hashes of full inputs, sampled records, counterfactuals and actual encoded frames; archive location from manifest |
| `test/analysis/summary.csv` | Pooled micro metrics for all54, original46-case G2 and8 supplements; successful-delay and event-onset-age statistics |
| `test/analysis/seed_metrics.csv`, `distributions.csv` | Whole-seed metrics and mean/median/std/min/max distributions |
| `test/analysis/paired_effects.csv` | Six requested contrasts plus seven factorial effects ×six endpoints;95% paired seed bootstrap CIs, sign-flip p, Holm p across78 tests |
| `test/analysis/fault_summary.csv`, `fault_trust_effects.csv` | Fault-class comparisons and descriptive trust subgroup intervals |
| `test/analysis/budget_comparisons.csv` | Actual sampling gaps,5% qualification and exact sample-timestamp identity; no test-time calibration |
| `test/analysis/matched_in_both_delays.csv` | Per-seed delay differences on identical truth events detected by both methods |
| `test/analysis/figures/` | Six figures, each PNG and vector PDF, generated only from saved observations |
| `test/analysis/analysis_manifest.json` | Analysis source identity, input/output hashes and inference scope |
| `checks/` | Actual local tests and read-only verification logs |

`sender_*`/`receiver_*` use the common deadline120s and5s matching tolerance,
ending at the earlier of physical-event end+5s and onset+120s. Raw `tp`,
`false_reports`, `rx_tp`, `rx_false_reports`, `fault_induced_false` retain the
historical native window. Primary FI is `sender_fault_induced_false`, not the
native FI column. Never mix these definitions within a comparison.

Conditional mean/median/P95 delay excludes misses and must accompany FN/Recall.
`sender_restricted_delay_sum_s / n_events` counts a miss as120s; this is a
declared bounded loss, not a measured delay for undetected events. Undefined
no-event quantities stay empty/N/A. Event CDF denominator includes every event.

Frame age can reset on a null frame. Finite-value age only resets on a finite
received value and holds age across nulls; it is an availability metric, not
proof the value is accurate/trusted. Coverage is separate. `mean_run_p95_age_s`
is the mean of per-run P95s, **not** the P95 of pooled source seconds. Sampling
rates divide by event/non-event union seconds, avoiding duplicate channel time.
Application bytes are sums of actual Binaryv1 frame lengths, including health
fields, timestamp, values, nulls, event bits and CRC. No estimated radio energy.

T off uses explicitly neutral health placeholders; only T on is actual C11
diagnosis/gating. All factorial groups keep constant health serialization layout.
S is native AdaptiveSense per-channel sampling; U is unchanged Upload. A7 is
GateOnly+U, not JO-SU. Native GateOnly has its historical emission rules; A4
instead sends every sample. Delta/Variance/Fixed controls carry actual C11 logs
without gating, retain frozen G1-selected bounds, and are not guaranteed to
match actual budgets in this new suite. Exact fixed-grid and U pairs differ
from adaptive comparisons with variable sampling opportunities.

## Reproduce

From the repository root with Python3.14, a C11 compiler, installed
`requirements-lock.txt`, editable project and initialized pinned submodules:

```sh
# One complete fresh batch, using the exact saved freeze; choose a NEW name.
python scripts/benchmark_ablation.py replicate --out results/scratch/ma1-replica-01 --workers 4

# One analysis/plot command, using saved per-run/per-event CSVs only.
python scripts/analyze_ablation.py

# Or analyze the fresh replica.
python scripts/analyze_ablation.py --root results/scratch/ma1-replica-01

# Read-only checks: raw archives optional and local-only.
python scripts/verify_ablation.py
python scripts/verify_ablation.py --archives --replay
python -m pytest tests/test_module_ablation.py -q
```

The initial study construction used `engineering`, then `freeze`, then `test`
phases of `benchmark_ablation.py`; the frozen protocol records them. These phases
refuse existing output directories. Reproduction uses the same already-exposed
final seeds and provides no new inferential evidence. Current effective source
hashes must match the saved freeze; no silent migration to newer policies.
Raw storage uses `results/traces/<output-directory-name>/<phase>`; use a unique
basename as well as a fresh output path.

Full per-sample traces, latent/noisy/observed signals and every actual frame are
stored locally under ignored `results/traces/module-ablation`. They can be
regenerated by the batch command rather than committing hundreds of MB. The
small saved per-run/per-event observation tables suffice to rebuild all
statistics and figures without those archives. A fresh clone may omit local
archives: default verification checks shipped structured evidence, while
`--archives` intentionally requires the actual files. Numeric output sorting
and gzip mtime0 are deterministic; PDF/PNG byte identity across plotting builds
is not required. CI runs the contracts, shipped-evidence checks and fresh
seed20 end-to-end engineering/analysis smoke.

Pooled point estimates and mean seed effects are different estimands.95% CIs
are descriptive bootstrap intervals; adjusted significance uses Holm across78
prespecified tests and the sign-flip symmetry/exchangeability assumption.
Fault subgroup CIs are exploratory/descriptive, without a multiplicity claim.
No-field validation, no default replacement, no favorable-case exclusions.
