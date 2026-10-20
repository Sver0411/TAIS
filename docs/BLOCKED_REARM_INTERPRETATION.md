# BLOCKED rearm: conclusion and decision

The root cause is confirmed and the targeted repair is reproducible. Retain `V02-Rearm` as an optional research strategy on `research/blocked-rearm-fix`; keep the frozen v0.2 comparator. The evidence supports recovery after a sampled spike returns to its reference, not a general improvement in concurrent same-channel fault/event inference or a replacement sampling algorithm. No final-result-driven rule or parameter changes were made.

[Design and alternatives](BLOCKED_REARM_FIX.md), [all measured tables and plots](BLOCKED_REARM_REPORT.md), [reproduction commands and test history](BLOCKED_REARM_REPRODUCIBILITY.md), [pretest decision](BLOCKED_REARM_PRETEST_REVIEW.md), [independent raw metrics](../results/blocked-rearm/test/metrics.csv), [event-level changes](../results/blocked-rearm/test/changed_events.csv).

## Confirmed transition defect

Seed91 is a known regression, not independent statistical evidence. At600 a sampled temperature spike creates PENDING. At605 the observation returns near the frozen reference: v0.2 cancels the unconfirmed candidate and the scheduler resets its analyzer, yet Evidence remains BLOCKED until a later low *raw* score. At665 the healthy real step starts being sampled, and at675 score/persistence qualify, but BLOCKED vetoes it. Original TAIS reports675; unfixed V02 misses it. The full per-channel sampled health/score/lifecycle/block/interval/upload logs and before/after PNG are retained under `results/blocked-rearm/diagnosis/`.

The repair clears BLOCKED only when a prior PENDING candidate from an earlier timestamp is cancelled for `displacement_returned`, the finite current reading is HEALTHY or DEGRADED, and its absolute displacement from that candidate's frozen reference is within the existing threshold times noise floor. The original scheduler still executes its cancellation reseed. The return sample itself is explicitly forbidden from confirming an event from stale debounce. New observations must satisfy the unchanged scoring/debounce/health rules. FAULT exclusion, confirmed-episode release, bounded confirmation, interval limits and numerical parameters are unchanged. Health transitions alone cannot unlock. This fixes seed91: TP0→1, report675, samples78 unchanged, uploads39→40.

## Independent evidence, seeds120–149

Seeds100–149 were audited as unused in reachable historical experiment records before this repair's runs. Development100–109 and validation110–119 were reviewed before source/config/tests/analysis hashes were frozen at8a73593. Final120–149 produced19,890 scored runs across all13 declared operating points and both separately reported suites. Development and validation each produced6,630 runs. The final verifier passed37 source files,26,100 archive hashes and10 fresh representative policy replays. All50 new seeds are now used; they cannot be a fresh final set for later result-driven design.

At the predeclared multiplier1, repair versus unfixed V02:

| Independent suite/group | Unfixed recall | Repaired recall | Paired recall difference,95% CI | Samples difference | Uploads difference | Payload bytes difference |
| --- | --- | --- | --- | --- | --- | --- |
| Main45 scenarios, all900 events |450/900 (50.00%)|454/900 (50.44%)|+0.444 percentage points [0,+1.111]|0|+4|+1,068|
| Main, actual same-channel overlap |102/360 (28.33%)|102/360 (28.33%)|0 [0,0]|0|0|0|
| Main, actual cross-channel overlap |243/360 (67.50%)|243/360 (67.50%)|0 [0,0]|0|0|0|
| Main, normal/no-fault events |35/60 (58.33%)|35/60 (58.33%)|0 [0,0]|0|0|0|
| Aligned recovery6 scenarios, all120 events |58/120 (48.33%)|118/120 (98.33%)|+50 percentage points [50,50]|0|+57|+15,256|
| Aligned recovery, same-channel sequential |0/60 (0%)|60/60 (100%)|+100 percentage points [100,100]|0|+57|+15,256|

Costs above are totals over30 seeds in each indicated group/suite, not per-run differences. The primary paired bootstrap resamples whole seeds2,000 times (RNG731); these are descriptive percentile intervals on a fixed synthetic suite, without multiple-comparison adjustment. Main's interval includes zero and does not support a broad statistically established improvement.

All four extra main matches are `spike_same_short/long`; main same-channel **sequential** recall rises33/60→37/60, difference+6.667 percentage points [0,+16.667]. Actual overlapping faults/events do not improve. Main pooled matched-event mean delay changes25.122→25.015s; conditional means do not penalize misses. Aligned newly recovered events are reported13s after onset; cross-channel events already matched at12s are unchanged. The aligned pooled delay12→12.508s reflects the added matched population, not slower reports for those previously detected events.

The aligned suite deliberately places a sampled impulse at600, followed by a separate real event60s later (labelled start662). It changes only fault jitter to zero, and is a conditional transition challenge, not natural fault prevalence. It is never pooled with main. Default cross sequential58/60 and event-free false alarms are unchanged. Repaired aligned totals match original v0.1 at each multiplier: this restores a lost capability rather than demonstrating superiority to v0.1. Main default repaired and v0.1 each match454 events, but repaired uses4,282 more samples and159 more uploads; it has29 fewer fault-attributed and35 fewer total unmatched reports. Those are separate tradeoffs, not dominance. AdaptiveSense and passive comparisons remain in the full report/paired CSVs.

## All operating points and unfavorable outcomes

| Multiplier | Main extra matches | Main extra fault-attributed / total false reports | Main extra samples / uploads / bytes | Aligned extra matches | Aligned extra fault-attributed / total false reports | Aligned extra samples / uploads / bytes |
| --- | --- | --- | --- | --- | --- | --- |
|0.75|+4|+2 / +2|+121 / +33 / +8,869|+60|0 / 0|0 / +57 / +15,248|
|1|+4|0 / 0|0 / +4 / +1,068|+60|0 / 0|0 / +57 / +15,256|
|1.5|0|+6 / +6|+128 / +39 / +10,499|+44|0 / 0|0 / +45 / +12,098|

Default main total false reports remain794, of which437 are operationally fault-attributed. Aligned totals remain76, fault-attributed0. Those nonzero unmatched onsets are not hidden by reporting only the fault attribution. No claim of universal false-alarm elimination is supported. Fault attribution uses the frozen paired counterfactual/timing definition, not proof of physical cause.

Development already exposed the drift risk at1.5 (seed102, `drift_same_long`): a cancelled unconfirmed candidate can return inside a broad numerical band while physical drift continues, then produce new false episodes. Final outcomes retain this risk. The repair does not repeatedly release a continuing CONFIRMED episode, and direct persistent/spike/confirmed-lifecycle regressions pass; it cannot guarantee absence of multiple onsets under every continuing fault or oscillation. No additional mechanism or threshold tuning was stacked on this repair.

At1.5, two seed91 short/long TP==1 assertions still fail because the score falls below12 before the unchanged10s debounce completes. They remain strict xfails with original assertions and initial failure logs; original TAIS has the same boundary and the repaired latch is already IDLE. This is not presented as solved. Information-erasing faults, valid persistent offsets and drift/event ambiguity remain unresolved.

## Tests and disposition

Actual history: forced original regression1 failure; untouched suite125 passed/1 xfailed; initial new suite66 passed/2 failed; small gate67 passed/2 xfailed; final full suite192 passed/2 strict expected failures/0 unexpected failures. The requested original multiplier1 regression now passes normally with unchanged TP==1 assertion. Frozen V02's missed event and exact historical replay are separately asserted. C adapter, causality/no-leakage, healthy/cross-channel, repeated episode and interval regressions pass. Original v0.2 archive verification also passed42,750 rows,50,700 hashes and five fresh replays. Implementation CI passed the complete suite plus AdaptiveSense235 tests/69 configuration checks and SensorTrust27 Python tests,21 C tests/404 checks.

Keep the optional repair because its return/reset synchronization has repeatable targeted benefit. Do not automatically merge it or replace frozen v0.2: the main distribution shows only a small gain, high multipliers add false reports/resource cost, and actual same-channel overlap remains unchanged. New policies informed by these outcomes need another untouched final seed set and a new frozen protocol. No new greenhouse verification, physical radio measurement or general fault identifiability result is claimed.
