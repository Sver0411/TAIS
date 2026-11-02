# Phase4.1: source audit and MA-1 diagnosis

Base c71e621a90e3dce0fa925ffaf62402a8579116f0. Historical protection ledger
`results/phase4/historical-protection.json` pins1,521 existing files and the
two upstream submodules. No historical source, data, metric or default changes.
MA-1 full archive verification passed before new implementation.

## Source findings before algorithm changes

The actual path is sampled row → C11 health → per-channel ChangeAnalyzer →
gate/recovery → per-channel hysteretic state/ladder → minimum channel demand →
upload. A faulty channel does not directly veto another, but both share a clock.
The GateOnly base uses confirmation=False. FAULT/nonfinite suppresses analysis
and requests60s diagnostics; DEGRADED suppresses environmental priority, and
first usable recovery reseeds that channel. C11 itself is unchanged.

The original algorithm already has substantial hysteresis: relative0.5 around
stable3/active8, immediate escalation and gradual de-escalation. STABLE uses
20,20,40,40,60,...; ACTIVE15,10,5; ALERT5. Thus “missing hysteresis” is not the
diagnosis. Minimum spacing is requested after high change scores, confirmed
events or channel-specific active ladder persistence; sample debounce and
schedule state are different quantities. Score=max(previous-EMA deviation,
30s population STD,10s mean absolute rate)/fixed noise floor. A persistent
noise floor mismatch can keep the STD/ROC high. There is no rolling fast-sample
budget or robust online noise scale, so hysteresis can retain costly activity.

Once STABLE waits60s, an unannounced event cannot be observed sooner than the
next actual sample. Speeding up afterward does not recover missing onset
observations. Changing the sample sequence also changes EMA, debounce and C11
sample-count windows. This is an important scheduling/detection dependency,
not evidence that C11 thresholds alone identify physical event causes.

## Actual per-event evidence

`scripts/diagnose_phase4.py` reads the existing MA-1 archives. For all eight
factor groups it replays the unchanged Scheduler on exactly the SAVED sample
times, verifies local active/health parity, and extracts actual debounce starts
and gate suppression. Other native controls use recorded state; unrecorded
debounce is explicitly unknown, rather than invented. No candidate algorithm
runs on900–919, and no new parameter selection uses these outcomes.

The corrected `results/phase4/diagnosis-v2` contains43,520 event rows (all methods,
one row per truth event, with separate sender match and receiver match), sample
times, pre-event age/coverage, first post-onset/finite sample, event-period gap
distribution, candidate times, gate states/resets, reasons and sampled-value
timelines. Noisy_none has no truth events, so it has a timeline rather than
fabricated event rows.

Observed A7 has647 deadline misses with no/insufficient finite opportunities,
1,263 covered detector failures,41 health/reset exposures and1 confirmed gated
candidate; it detects768 events. A5 detects1,341, with278 opportunity misses,
1,054 covered detector failures,43 exposures,3 confirmed gated candidates and
1 reporting/onset-assignment case. These are diagnostic categories, not a
complete causal identification. In particular C_exposure does NOT prove the
gate caused the miss; same-channel replacement may erase evidence. Common
nonfinite recovery and logging-only C11 must not be called reliability gating.

A7 has a pre-onset sample within20s for40.40% of events versus100% for fixed20;
mean first post-onset sample delay is24.61s versus10.08s. A7 nevertheless takes
10.74 samples per event support versus5.02: dense late sampling does not imply
good onset coverage. Exact values remain in the structured event table.

The initial diagnostic pass incorrectly grouped some common recovery resets
as health exposure with T disabled. It remains under`diagnosis/`, including
its exact source and an explanation; the scope-aware v2 fixes this attribution
before candidate implementation. No MA-1 result was rewritten.

## Seed and implementation boundary

Audited150 current accessible config/manifest files and trace directory seed
identities. No collisions for final920–939 or engineering940/941. This does not
certify inaccessible machines/unrecorded work. Engineers are not validation
replicates. Use a separate `tais.adaptive` subpackage so historical source-hash
enumerations remain unchanged. Keep the old detector/C11/U; replace ONLY next
sampling demand in explicit optional wrappers. Professor-specific reports are
local outside Git; public research docs remain generic. No push authorized.
