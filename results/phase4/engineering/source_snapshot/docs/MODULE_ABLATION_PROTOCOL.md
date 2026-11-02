# MA-1: three-factor module ablation and multi-metric evaluation

Protocol frozen before new final outcomes, 2026-11-02 (Asia/Shanghai).
Repository base `afa2b1719a14931f52129ae3699a03ceefcdb906`.
The actual checkout is `/Users/mac/Documents/TAIS`; the originating chat folder
was the separate AdaptiveSense repository. No changes to that predecessor or
vendored sources. No tuning or default-policy replacement in this study.

## Audit and missing work

Reviewed the current repository/source/script/result indices; original replay,
Scheduler, C11 bridge, scoring/matching, JO sampling, Upload U, SU wrappers,
independent schedules, codec and receiver metrics; G1/G2 configurations, methods,
source freezes, seed cohorts, reports and current CI/test entry points.

| Existing evidence | Reuse / limitation |
| --- | --- |
| v0.1, v0.2, rearm, BM-1, FO-1, independent reference and spatial pilot | Keep historical experiments/failures; not a new classifier study |
| JO H/S/U | Existing decomposition concerns an extra trend H, **not** disabling original SensorTrust; H failed |
| SU | U orthogonality, actual frames, decoded receiver edges, data age already implemented |
| G1 | Independent Fixed/Delta/Variance/Rao-inspired and common/native views; frozen development-selected bounds |
| G2 | 20 seeds700–719 ×46 cases ×14 methods; no test-time calibration; truth differs from G1 |
| Missing | Complete original SensorTrust × AdaptiveSense sampling × U factorial; deadline-limited scores and miss-inclusive delay; consolidated finite-value age and event/non-event sampling analysis |

Historical scores remain authoritative and unchanged. G1 and G2 counts are never
pooled. No old final cohort is used for choosing new parameters. New test seeds
900–919,20 whole-seed replicates, matching the existing G2 scale. Engineering
uses already exposed seed20. Seeds0–899 reserved. Audit accessible current JSON
configs/manifests before freezing; it cannot certify inaccessible machines or
unrecorded work. No further size increase based on observed results.

## Exact module semantics

| ID | T: C11 gate | S: adaptive sampling | U: selective transmission |
| --- | --- | --- | --- |
| A0 | off | off | off |
| A1 | on | off | off |
| A2 | off | on | off |
| A3 | off | off | on |
| A4 | on | on | off |
| A5 | on | off | on |
| A6 | off | on | on |
| A7 | on | on | on |

All groups call unchanged per-channel `Scheduler(confirmation=False)`.
T on uses actual C11 health gate, suppression and recovery reset; this is an
integrated reliability effect, not calibrated fault probability or diagnostic
accuracy alone. T off replaces the gate's health input with an explicit neutral
`100/HEALTHY/flags0`, without running C11. Neutral fields are placeholders,
**not** observed health. Common nonfinite sanitation/recovery remains necessary
in both groups. This design isolates gating from wire-layout savings: all eight
groups keep the same health field layout. Disabled-module resource estimates
exclude physical CPU/energy, which is not measured. Do not deploy neutral fields
as real diagnosis. Baseline+C11 means logging only, not gating.

S on uses native per-channel AdaptiveSense ladders and gate diagnostic intervals.
S off ignores the requested next interval and samples at0,20,...,1780s. Detection
still uses those actual samples. It does not receive extra observations to make
up for sparse sampling. U on is unchanged last-sent deadband2 noise floors,
heartbeat120s, mandatory sampled event/health/validity edges. U off sends every
sample. Original internal upload bookkeeping never feeds U into sample times.
A7 is exactly GateOnly+U; A4 shares GateOnly's sampling/local detection but uploads
every sample. A2 is per-channel Scheduler with neutral gate; it is not identical
to the upstream global AdaptiveSense scheduler. No JO trend H or JO bounded
recheck S is hidden inside this factor. JO-SU20/40 are separately named controls.

Other controls: Fixed5/20/60+C11, frozen Delta-budget-SU40+C11 and
Variance-budget-SU40+C11, native GateOnly, JO-SU20/40. All use the original codec,
thresholds, held sample history and detector. Independent bounds are inherited
from saved G1 development choices; no recalibration on new outcomes.

## Conditions fixed before test

`configs/module-ablation.json` is the central study config and embeds unchanged
G2 physical parameters. Every run lasts1800s at a1Hz source grid. Only due rows
are visible to policies. All methods share exactly the same observations,
latent process, faults and event labels within(seed,case); hashes verify this.
All46 G2 scenarios retained, covering clean, range, spike, stuck, drift, missing,
invalid and stable offset in both channels and none/same/cross relations.
Existing G2 already varies short/medium/long durations and step/pulse shapes.

Eight supplementary cases reuse the G2 generator without new equations:

* low_frequency: one onset in660–780s instead of3; original random duration/shape.
* high_frequency: six nonoverlapping onset slots100+260i..120+260i,41–100s durations,
  original three shapes repeated twice.
* slow_change: one smooth900–1000s pulse beginning300–360s; original amplitude.
* noisy_none/noisy_events: original noise sigmas ×7, retaining existing AR/tails.
* multi_range/multi_stuck/multi_drift: compose each channel's existing single
  `kind_channel_same` trace, including its own latent/noisy/events/fault schedule.
  These are two-channel interventions, not a new redundant-sensor architecture.

Main pooled estimand is this **predefined54-case mixture**; report46-case G2 and
8 supplementary conditions separately. This is not an estimate of field prevalence.

## Matching, misses and metrics

Preserve original `paper_metrics` native sender/receiver scoring as auxiliary
columns. Primary new scores reuse `match_events`, channel-aware one-to-one,
closest onset,5s tolerance, but cap the effective truth endpoint so a report
must occur by `min(original_end+5s,onset+120s)`. Early tolerance remains5s and
negative latency is clamped0. Late reports are unmatched FPs and leave FNs.
No retrospective reuse of the detector's candidate start. Labels are physical
G2 schedule supports, not detector outputs; slowly rising labels can precede a
physically material deviation, a known sensitivity limit.

Sender report = first uploaded active sample of each local episode. Receiver
report = independently decoded false→true edge; hidden local clears cannot
create receiver detections. Exact Binaryv1 encode/decode round trips and actual
frame lengths, ideal zero-delay/loss local link. Bytes are application bytes,
not RF traffic/joules. Native payload JSON estimate remains auxiliary only.

P/R/F1,TP,FP,FN,miss rate; successful-delay mean/median/P95 with match count;
**restricted delay** = matched delay, or120s for a miss, averaged over ALL
channel-level events. This is a declared capped loss, not an observed delay of
missed events and not a survival estimate. Deadline detection CDF uses all truth
events as denominator; paired delays only among same events matched by both
methods are supplementary (selection persists). No-event Recall/delay N/A.

Message count, Binaryv1 bytes, relative byte change versus Fixed20; exact actual
samples and mean timestamp differences. Per-source-second event union determines
event/non-event sample rates, so overlapping channel labels do not double exposure.
Frame age uses latest received frame; finite-value age uses latest finite
received value per channel and continues across nulls. Coverage reported separately;
no pre-first-value future filling. Stored per-run P95 age is not pooled P95;
summary explicitly calls its mean `mean_run_p95_age_s`. Report event-onset sample,
frame and finite delivered value age, fault-associated/induced false counts, same-channel overlapping
fault FNs, and finite sampled event coverage. FI uses primary deadline matching
and unchanged operational fault+120s attribution/counterfactual exclusion within5s.
Native FI also retained. This is operational attribution, not causal proof.

## Resource fairness and inference

Same fixed20 grid gives exact equal sample budgets for A0/A1/A3/A5. Each U pair
also has identical actual sample times by construction and invariant tests.
Adaptive-vs-fixed and trust-on/off adaptive comparisons use **actual resources**;
do not equalize sampling by feeding free observations, truncation or interpolation.
Report actual budget ratios and5% eligibility as descriptive checks. Nearby totals
alone do not isolate causal quality effects or establish matched-budget superiority.
There is no hard wireless energy budget experiment here.

Pooled micro metrics and per-seed mean/median/distributions both reported. Whole
seed bootstrap5000 draws,RNG2026110201; retain the full scenario block for each
seed. Primary comparisons: A1−A0,A2−A0,A3−A0,A7−A4,A7−A5,A7−A6. Factorial
T/S/U = mean simple difference; two-way effects = averaged differences of
differences; three-way = difference of differences of differences, using0/1
coding. Report seed-mean micro F1,Recall,bytes,restricted delay,FI,same-fault FN
differences. Bootstrap95% CIs are descriptive. Two-sided paired sign-flip20000
draws requires symmetric/exchangeable seed differences under its null. Holm
correction across all13×6=78 prespecified tests; no inference from point means
alone. Fault subgroups have descriptive intervals without multiplicity support.
G1/G2 reports are context, not additional independent replicates. The shared
source RNG across cases/channels is preserved by clustering the whole seed.

## Execution and evidence

Engineering, invariant tests and source/config/protocol freeze precede final.
Freeze saves actual source snapshots/hashes because Git HEAD alone cannot name
uncommitted implementation. Final runner rejects changed hashes or existing
output directories, writes STARTED before execution and COMPLETE only after
all expected runs. No parameter selection stage. Failures remain visible;
use fresh paths for repairs and document any new execution. Raw traces under
ignored `results/traces/module-ablation`; committed per-run/per-event tables
are sufficient to regenerate statistics/figures without traces. Manifests
retain input/signal/result hashes, code base, packages, seeds and archive paths.
Full clean reruns rebuild signals and traces from the saved config/source.

```sh
.venv/bin/python scripts/benchmark_ablation.py engineering --workers 4
.venv/bin/python scripts/benchmark_ablation.py freeze
.venv/bin/python scripts/benchmark_ablation.py test --workers 4
.venv/bin/python scripts/analyze_ablation.py
```

See root README for copyable final reproduction commands and new-path options.
All unexpected malformed data or
config errors fail rather than being silently repaired. No hardware, natural
fault, energy or agricultural effectiveness claim; no default-policy change.
