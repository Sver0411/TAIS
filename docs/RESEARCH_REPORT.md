# TAIS v0.1 research report

Report date: 2026-10-17. This is a research prototype report, not a field deployment result.

## Scope and independent evidence

The research question is how channel health can constrain event-aware sampling when another healthy channel may experience an event, and where same-channel event/fault overlap becomes ambiguous. The real C11 SensorTrust detector and pinned AdaptiveSense primitives are reused without upstream edits. The package preserves per-channel state and independent latent/noisy/faulted streams and truth labels.

## Exact original baseline reproduction

AdaptiveSense `f7ec30fd4721aa1a7c308f879050a83936e60067`: 235 Python tests and 69 configuration checks passed. SensorTrust `2ce98dd043bb01ea99052eda218c68a172499a4c`: 27 Python tests and 21 standalone C tests (404 checks) passed. These were run in isolated temporary copies. The original seven-scenario AdaptiveSense benchmark regenerated 24 channel event labels and the following actual result:

| Strategy | Local detected events | Samples | Application uploads | Strict unmatched detections |
| --- | --- | --- | --- | --- |
| Fixed 5 s | 22/24 | 5280 | 5280 | 17 |
| Fixed 10 s | 22/24 | 2640 | 2640 | 20 |
| Fixed 20 s | 19/24 | 1320 | 1320 | 20 |
| Fixed 40 s | 17/24 | 660 | 660 | 14 |
| Fixed 60 s | 11/24 | 440 | 440 | 5 |
| AdaptiveSense | 18/24 | 1178 | 768 | 17 |

Both CSVs matched their pinned originals byte-for-byte: metrics_all SHA-256 `46d49bfd7ac606930cccfb11f982ee9bfa578f84f40703fc2b0bfe80f16a7876`; metrics_summary `2f41f5478e4acabe57a9811246cc144862b7afd5e0315963b3cc5afab0e60bbf`. [Logs and environment](../results/baseline/manifest.json). These are original baseline results, not TAIS results and not the two-channel fault benchmark below.

## Frozen new benchmark

All 50 seeds retained: development 0–9, validation 10–19, independent test 20–49. No threshold tuning or selection on any split; three predeclared threshold multipliers are all reported. 45 scenarios x13 operating points x50 seeds =29,250 scored runs, plus cached clean counterfactual replays. Algorithm/config frozen at 273758d, source-script import fix at 97aa5d5; per-split manifests record the actual source commit and configuration hash. Later report/analysis tooling changes do not change the experimental policy.

Each 30-minute run has two channels, independently labeled physical events and one injected faulty temperature channel in fault scenarios. Profiles jointly vary duration and intensity; event-free, healthy-other-channel and same-channel overlap are separately tabulated. Main recall matches upload-requested report onsets; local TP is a separate column. Statistical and attribution definitions are in the [protocol](EXPERIMENT_PROTOCOL.md).

Full-run numerical tables and interpretation are populated only after the corresponding commands complete and hashes are checked.

<!-- RESULTS_START -->

Full-run output pending completion.

<!-- RESULTS_END -->

## Interpretation boundaries and next work

The health gate and confirmation sampler are separate hypotheses. Any measured benefit of gating cannot be assigned to confirmation without the GateOnly ablation. Healthy-channel state isolation is a tested implementation property; it is not a guarantee of observing a brief event between samples. Hard replacement/missingness on the same channel removes information that this single sensor cannot recover. Stable offsets and sparse-sampling diagnosis expose SensorTrust limitations.

No rule or threshold was changed based on independent test outcomes. This first suite has jointly varied profiles, two channels, one faulty channel and sequential rather than concurrent one-second spike/event cases. A subsequent preregistered suite should vary timing, intensity and duration independently, include concurrent spikes and multiple faults, and evaluate spatial/cross-sensor corroboration. Any tuning requires new held-out seeds.

The real Hull greenhouse CSV could not be acquired through the tested API (403). Nominal metadata/license/5-minute resolution were checked, but actual header/missingness and TAIS replay were not. The fixture-tested audit helper is not empirical dataset evidence. No control-threshold cue, hardware current measurement or embedded deployment result exists. Literature verification is focused; comparison implementations for AAS/CLARA/sentinels are not provided, so no novelty or superiority claim over those works.
