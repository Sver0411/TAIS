# v0.2 design and predeclared validation contract

This document is committed **before implementation**. Baseline code is retained byte-for-byte under `src/tais`, config `configs/experiment.yaml`, old scripts/results/report. New code lives in `src/tais_v02`, scripts `v02_*`, results `results/v0.2`.

## Candidate choice based on forensic evidence and old development/validation

| Candidate | Expected benefit | Failure risk | Cost / decision |
|---|---|---|---|
| A: permit FAULT evidence / broad soft gating | Apparent recall on erased cases | Confirms identical event-free streams; physical information absent | Low implementation cost, unacceptable interpretation; reject |
| B: one bounded persistent candidate episode for DEGRADED evidence | Avoid >=12 re-entry and previous-reading cancellation, make confirmation lifecycle explicit | Persistent drift can confirm; primary recall gain may be zero | One frozen reference/count/time per channel; choose as a falsifiable mechanism |
| C: more surveillance for healthy channels under another fault | Could improve short cross events | Additional samples even without observable change, not same-channel erasure remedy | Separate research question; retain existing channel isolation without adding this mechanism |

Old development/validation same-channel comparisons and old test diagnostics are in `FAILURE_ANALYSIS_V0.1.md` and `identifiability.json`. They show that FAULT loosening has no observation-based justification and that v0.1 confirmation lacks a stable benefit. B is selected for an explicit, independently testable lifecycle, **not a prediction that it will win**. No fitting or threshold search is planned. Validation may conclude it should not replace v0.1; all predefined points are still evaluated once on final seeds.

## Complete selected mechanism (B)

Reuse the original C11 trust contexts, AdaptiveSense scorer/state transition/hysteresis/ladders, channel isolation, health reports, heartbeat and application envelope. Narrow fork of the legacy decision method is needed because it exposes no candidate-policy hook; upstream and legacy files remain untouched.

Each channel has IDLE, PENDING, CONFIRMED or BLOCKED episode state:

- HEALTHY/IDLE uses the original healthy policy. Only a **DEGRADED**, finite reading with raw score greater than the existing event threshold can open PENDING. No new change-score formula or independently tuned trigger is introduced.
- Capture the **pre-update EMA** and displacement sign on creation. Require displacement in that sign strictly greater than event-threshold x noise-floor. Count real sampled supporting readings (including creation). Once pending, retain evidence when raw score falls below ALERT entry; do not require the unrelated >=12 scheduler entry on every sample.
- Confirm only with raw upstream debounced event, >=3 supporting observations and >=10 s elapsed (same event duration criterion), strictly before120 s timeout. Single suspect readings never authorize an event. A pending episode continues across DEGRADED→HEALTHY with the same rules.
- Cancel on missing/nonfinite/FAULT, recovery reset, failed signed displacement, or >=120 s timeout. Failed persistence reseeds only the channel scorer (as in legacy spike-return handling). Cancellation/confirmation/creation/release reasons are logged with timestamp and reference/count, including multiple transitions in one call.
- CONFIRMED is active while raw debounce and displacement persist. It does not repeatedly reopen confirmation on each high reading. Release to BLOCKED when evidence fails. BLOCKED re-arms only when raw score<=event threshold, including across a HEALTHY transition; pending episodes are never silently extended. FAULT/invalid always cancels and excludes environmental priority, preserving hard information boundaries.
- PENDING requests5 s (the configured minimum) only for the full mechanism. Passive ablation retains the **same evidence rules** with no extra confirmation scheduling; ordinary ladders/diagnostic60 s continue. Both terminate pending by the deadline; the next sample interval is capped by remaining deadline (clamped to legal minimum). Timestamp granularity may delay observing expiry by at most one minimum interval; no new confirmation interval is requested after expiry.
- Eligible environmental priority = healthy raw score or a confirmed degraded event. Other health states contribute diagnostic demand60 s. Choose shared minimum eligible/diagnostic/pending interval, clamp[5,60]. No node-wide health veto.
- Keep envelope metadata unchanged so measured payload differences reflect requests/decisions, not compression. Diagnostic evidence logs are **offline traces**, not silently free online transmissions.

Parameters live in `configs/v02.yaml`: enabled, confirmation_samples3, max_confirmation_duration_s120, diagnostic_interval_s60, confirmation_interval_s5, min_duration_s10; multiplier scales original score thresholds [.75,1,1.5]. Disabling v0.2 returns the exact original TAIS scheduler, not a nominal reimplementation. The passive ablation disables only accelerated confirmation demand.

## Frozen experiment (before final test)

- Seed audit: all reachable old metric/manifest Git blobs and local archive seed directories are inventoried in `results/v0.2/seed_audit.json`. No50–99 found. Development0–9, validation10–19;20–49 diagnostic only. Final50–99, never used to choose parameters.
- Same unchanged45 scenarios,1800 s, two channels, same noise/fault RNG and schedule per seed across policies. This intentionally preserves comparability and also preserves the v0.1 timing/profile limitations. No new favorable challenge suite or truth relabeling.
- Comparators: Fixed5/10/20/40/60, actual AdaptiveSense, logging-only, v0.1 GateOnly and TAIS, full V02 and passive V02-Passive. GateOnly/TAIS/V02/V02-Passive all report **every** [.75,1,1.5] point.19 operating points/case,855 runs/seed;8550+8550+42750=59850 scored runs.
- Primary: same-channel actual-overlap reported recall **and** counterfactual-new fault false reports; report overall/clean/cross/none/sequential, and event-erased versus non-erased same separately. Count a matched artifact historically as TP, but identify indistinguishable pairs alongside the unchanged primary metric.
- Secondary: misses, total false/h, conditional event/fault delays, samples, uploads, actual serialized application bytes, C any/type fault detection, diagnostic/confirmation demand, per-channel sample/upload causal-hold MAE/RMSE.
- Same channel-aware one-to-one matching/tolerance5 s and counterfactual attribution120 s as v0.1. Ground truth/fault labels offline only. No-event recall N/A.
- Selection rule: **no parameter selection**. One candidate and one mechanism ablation, three inherited operating points, all disclosed. Freeze source+config+tests and commit a development/validation review before final run. Any algorithm correction after final opening invalidates independence and requires a new never-used final split.
- Paired whole-seed2000 bootstrap draws, RNG731, descriptive95% percentile CIs for full-minus-v0.1 and full-minus-passive at each point. Count deltas per seed batch of all stated scenarios; recall in fractions. Full tables by scenario/type/profile/relationship/information class and two plots: recall vs uploads; fault false vs recall. No unadjusted multiple-testing superiority declaration.
- Cost is a result, not an optimization constraint hidden by filtering. Do not claim physical energy. Report negative outcomes without retuning. This benchmark cannot establish physical cause identification or field validity.

## Required verification and failure expectations

Test C adapter parity (legacy tests), healthy isolation, single spike veto, degraded sustained opportunity, candidate timeout and rearm, recovery reseeding, interval bounds, causal prefixes and unsampled-read guards, deterministic same-config/seed, legacy archive reproduction, disabled equivalence, and observation-identical event/no-event pairs. Tests must exercise real C health for integration; controlled states may additionally test exact lifecycle boundaries. A persistent degraded event test establishes opportunity, not universal specificity.

Expected failures: range/missing/stuck replacement remains unrecoverable, stable offsets remain a C blind spot, drift may be confirmed, brief events can lie between samples, and candidate evidence can be absorbed by EMA or recovery. Greenhouse403 remains pending; no real-data or RF-energy result is implied.
