# P4-1: adaptive sampling mechanism study

Protocol before final outcomes,2026-11-02; base c71e621. No default replacement,
no upstream/historical changes, no GitHub push. Generic public documentation
only. Personalized reports are local artifacts outside every Git checkout.

## Ordered stages and question

4.1 source audit and MA-1 event diagnosis completed before new samplers:
PHASE4_AUDIT.md and `results/phase4/diagnosis-v2`. Initial scope-attribution
mistake retained in diagnosis/; no old experiment CSV changed. 900–919 are
diagnostic only,0–899 reserved; candidates never run/select parameters there.
4.2 mathematical design: PHASE4_ALGORITHM_DESIGN.md. 4.3 independent optional
implementation in tais.adaptive, leaving old Scheduler/C11/Upload/Core intact.
4.4 contracts/regressions. 4.5 engineering940/941. 4.6 only implementation repairs
with fresh directories/evidence, no parameter search. 4.7 freeze all effective
source/config/analysis/protocol/test hashes and source snapshots. 4.8 one final
920–939 execution. 4.9 analysis/12figures/verification. 4.10 generic Chinese
results and separate local private report. Retain failed attempts, do not overwrite.

Question: can bounded robust noise estimation or past-only trend risk improve
onset observation opportunities without wasting fast samples, at an acceptable
real sampling cost? Keeping the event detector fixed intentionally exposes
covered-but-undetected events; no promise to repair slow-event detection by
scheduling alone. Algorithms are hypotheses, not guaranteed improvements.

## Conditions and cohorts

20 final seeds, matching MA-1/G2 replication scale. Audit150 currently accessible
configs/manifests plus trace directory identities before generating new outcomes:
no candidate920–939 or engineering940/941 collisions. Record audit scope;
unrecorded/inaccessible runs cannot be certified. No sample-size increase based
on outcomes. Engineering does not count as an independent final replicate.

All54 MA-1 conditions retained unchanged. Add12 balanced clean-event conditions:
amplitude factors0.75/1.5 ×duration short12–20/medium45–75/long180–240s ×noise
sigma factors1/3. Use the same G2 shapes, physical support labels, background,
onset strata and RNG derivation; duration assigned to each of3 slots with three
same-bound bins. Amplitude/duration/noise varied independently in the supplement.
No favorable-case selection. Always1800s,1Hz source grid; process only due
sample rows. The66-case mixture is artificial and fixed, not field prevalence.
Report original54 versus balanced12 separately. Fault class/relationship,
short/long, frequency and slow/noisy/multichannel cases remain available.

## Full24-method matrix

Eight old factor groups A0..A7 retain their exact MA-1 semantics: T=C11 gate,
S=original per-channel AdaptiveSense, U=Upload. Fixed20=their S-off grid.
Retain all8 MA-1 controls: Fixed5/20/60+C11 logging, Delta/Variance saved G1
operating points+C11 logging, native GateOnly,JO-SU20/40. No retuning native
budgets or scorer thresholds. Independent+C11 logs do not gate their detector.

Add Robust/Risk ×T0/1 ×U0/1,8 new explicit modes. T off uses MA-1's neutral
100/HEALTHY/flags0 health input, not diagnosed health; common invalid sanitation
continues. T on is the same actual C11 and GateOnly suppression/reseed logic.
The new samplers read that health but do not redefine it. U off every sample;
U on unchanged deadband2 floors,heartbeat120s,event/health/validity edges.
All factorial frames retain identical health layout. U never feeds back into
sample times/history/budget/local detector. Actual observation hashes and
timestamps verify pairing and U invariance; code signatures expose no truth.

## Metrics and units

Primary matching and restricted-delay definitions EXACTLY reuse MA-1:
channel-aware one-to-one,5s tolerance; effective endpoint
min(physical_end+5,onset+120). Report sender and decoded receiver P/R/F1/TP/FP/FN,
Miss Rate and deadline detection rate (=Recall at this deadline). Retain native
TP/FP/FI auxiliary columns. A late report is FP and leaves FN; never call that
event “never detected” if native matches exist. Successful mean/median/P95 delay
has a match denominator. Restricted delay loss=min(actual matched delay,120),
or120 for a miss, over ALL truth events. This is a declared loss, not fabricated
delay or a survival estimate. Undefined no-event quantities stay N/A.

Real samples/mean actual gaps/interval histogram; event/non-event union sampling
rates; strict-before-onset sample within20s coverage (sample AT onset is separately
post-onset, not a past sample); first actual and finite post-onset sample delays,
availability counts if no later sample; finite event coverage; fast actual gap<=5s
share/count and every120s rolling maximum; outside-truth fast samples, fast bursts
with no truth overlap, fast bursts with no local onset by burst-end+10s. “Without
truth” is an offline operational waste proxy, not an online trigger or proof of
uselessness. Count all diagnostics and ordinary samples too. Request counters
are separate from actual fast acquisitions, important with delayed input ticks.

Binaryv1 actual encoding/independent decoding, messages/bytes/Fixed20 ratios;
all sampled event/health edges, including clears; frame age versus age of latest
FINITE received value. A null frame does not reset finite age; coverage separate.
Age of a fresh but faulty value is not reliability. Mean-of-run P95 explicitly
distinguished from a pooled P95. Event-onset frame/sample/finite age saved.

FI: unmatched sender/receiver reports within same-channel fault through120s after
recovery, excluding a clean counterfactual onset within5s. Counterfactual uses
same pre-fault noisy stream, no new RNG. Report all FP too. Same-channel fault
overlap FNs and diagnostics remain. FI is operational attribution, not causal proof.

Per-event forensic categories are scoped to actual gating: A no/<2 finite
opportunities; C_gate actual confirmed candidate suppressed; C_exposure health
or reset exposure without identified causal effect; B finite coverage without
confirmed report; D active without new matched report. Priority C_gate,A,C_exposure,
D,B; never claim exposure identifies the cause. New-wrapper candidate starts
and raw debounced states are actually saved, legacy factor states reconstructed
only on exact saved acquisitions with parity checks. Other native unrecorded
candidate state remains unknown. Every event and miss retained, including failures.

## Inference fixed before final

Whole paired seed is the cluster, preserving all66 cases/channels. Pooled micro
metrics distinct from the mean of seed micro metrics.5000 paired seed bootstrap,
RNG2026110204,95% percentile descriptive intervals.20000 two-sided seed sign-flip
draws assume symmetric/exchangeable differences under the null; finite Monte
Carlo uncertainty remains. Never infer from means alone or treat source seconds,
channel labels or repeated conditions as independent seeds.

For each candidate K,8 contrasts:
K-T0-U0−A0,K-T1-U0−A1,K-T0-U0−A2,K-T1-U0−A4,
K-T1-U1−A5,K-T1-U1−A7,K-T1-U1−K-T0-U1,K-T1-U1−K-T1-U0.
Also Risk-T1-U1−Robust-T1-U1.17 contrasts ×8 endpoints:
F1,Recall,samples,bytes,restricted delay,pre-onset coverage,fast samples outside
truth,FI =136 tests with ONE Holm family. Other subgroup intervals are
descriptive; no favorable subgroup substitutes for main default gates.
Zero U differences verified by records, not a non-significance equivalence claim.

## Predeclared recommendation gates (engineering tolerances)

Evaluate BOTH full T1/U1 candidates, without selecting a test winner first.
Against A5: seed-paired95% lower F1 and Recall differences>=−1pp for sender,
receiver F1 lower>=−1pp; sample ratio95% upper<=0.95 (at least5% saving), byte
ratio upper<=1,FI ratio upper<=1.05,mean finite-value age difference upper<=10s,
pre-onset coverage difference lower>=−5pp. In noisy_none, sample ratio95% upper
<=1.10 versus A0. Versus A7, positive F1 difference with Holm p<0.05.
All actual sampled important edges delivered and all rolling fast maxima<=6.
Every condition must pass; otherwise NO_GO as a default replacement. These
tolerances are not validated agronomic requirements. If both pass, lower sample
count then simpler Robust breaks ties; do NOT silently change the default.
Any later redesign needs new untouched seeds. Hardware timing, energy, C port,
natural faults and field utility require separate validation even if gates pass.

## Execution and reproduction

Every phase has exclusive output paths, STARTED/COMPLETE status, sources/seeds/
input/result hashes, package versions, actual raw records and frames. Freeze
checks engineering source equality and saves source snapshots because Git HEAD
alone does not identify uncommitted changes. No source/parameter/scoring edits
during final. Bug repairs preserve failure output and use a fresh directory.

```sh
python scripts/diagnose_phase4.py --out results/phase4/diagnosis-new
python -m pytest tests/test_phase4_sampling.py -q
python scripts/benchmark_phase4.py engineering --out results/phase4 --workers 4
python scripts/benchmark_phase4.py freeze
python scripts/benchmark_phase4.py test --workers 4
python scripts/analyze_phase4.py
# One exact new-path batch AFTER saved freeze exists:
python scripts/benchmark_phase4.py replicate --out results/scratch/p4-replica-01 --workers 4
```

Raw traces under ignored results/traces/phase4; small structured observations,
Engineering export attempt1 remains in engineering/ with exact sources. Numeric
timestamp ordering is corrected before final and rerun with the same engineering
seeds under the configured engineering-v2/ directory; no algorithm parameter
changes. Initial timeline Figure03 is retained but not used for conclusions.

Raw traces under ignored results/traces/phase4; small structured observations,
including compressed event forensics and gap histograms, can reproduce every
summary/figure without raw archives. The historical diagnosis specifically
requires MA-1 raw samples; this is different from final statistical regeneration.
No new GPU training, large models, front end or claimed physical energy model.
