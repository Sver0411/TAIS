# BLOCKED rearm: diagnosis, minimal repair and preregistration

Baseline: `96170fcb5df0534ca58e44827b2fcb214e7892ef`, branch `research/v0.2-same-channel-recall`. Work branch: `research/blocked-rearm-fix`. This design is committed before implementation. Frozen `src/tais`, `src/tais_v02`, configurations, v0.1/v0.2 reports/CSVs/plots and upstreams remain unchanged. The repair is a separately selectable strategy, not a new sampling algorithm.

## Reproduced cause

`pytest tests/test_v02.py::test_known_blocked_rearm_failure_after_spike --runxfail -q` actually fails (1 failed). The untouched suite gives125 passed/1 xfailed. Logs and sampled CSV are in `results/blocked-rearm/diagnosis`.

Seed91 long spike:600 PENDING, C DEGRADED75/SPIKE, raw160.27;605 returns24.078 near frozen reference23.918, raw79.60 from the old excursion history. `Evidence.step` cancels with `displacement_returned` but sets BLOCKED. The scheduler then **already reseeds its analyzer and zeros effective priority**.665 healthy28 C/raw26.09;675 upstream debounce true/raw11.88, but BLOCKED suppresses it. Old TAIS reports675 (matched), v0.2 only870 (outside662–838 truth). Both take78 samples; the lost report changes uploads40→39. Full records are byte-equal to the published v0.2 JSON. Truth is used only for offline matching.

The state inconsistency is requiring a *future* low-score observation after an already observed return and scorer reset. A later healthy transition alone is not reliable evidence of a new episode.

## Two candidates

| Candidate | Rule | Risk/cost | Decision |
|---|---|---|---|
| A: synchronize verified return cancellation with existing scorer reset | Rearm on a prior unconfirmed PENDING episode ending at a finite usable reading inside the frozen reference band; suppress the cancellation sample itself | Oscillations can create new candidates after real returns; persistent false steps remain ambiguous | Choose: one latch change, one log action, no new threshold/time/memory |
| B: retain a release reference and add WAIT_NEW_CHANGE | Require reference recovery plus subsequent healthy/new displacement evidence | Additional state, thresholds and delays; can lose a brief next event and needs extra validation | Reject for this minimal repair |

## Exact rule A

Delegate all existing evidence processing to the frozen v0.2 implementation. Capture the prior episode phase/start/reference before the call. Only when **all** hold:

1. A previously existing episode was PENDING (unconfirmed), started at an earlier sampled timestamp.
2. The original method emitted `cancelled / displacement_returned` on this call. Not deadline, unusable, confirmed release or same-call creation/cancellation.
3. Current value is finite and current C health is HEALTHY or DEGRADED, never FAULT.
4. `abs(value - frozen_reference) <= existing_event_threshold * existing_channel_noise_floor`.

Set blocked=false and log `rearmed / reference_return_reset`. Return environment_active=false for this cancellation sample, even if old raw debounce was true. The unchanged scheduler sees the original `displacement_returned` action and performs its existing analyzer reseed/score0. A later actual observation can start fresh healthy debounce or degraded bounded confirmation normally.

The absolute-band condition is narrower than the old signed-persistence failure: crossing far to the opposite side is **not** assumed to be a return. No health transition alone clears the latch. No FAULT exclusion, score formula, debounce, ladders, heartbeat, confirmation count/duration or payload changes. Existing rearm on low raw score remains. CONFIRMED release and deadline blocking remain unchanged, so this does not repeatedly retrigger a continuing confirmed event. All existing sample bounds5–60 s and pending deadline120 s remain. No future/unsampled value, truth or fault label is available online.

New package `tais_rearm` subclasses only the evidence implementation and installs it while constructing the frozen scheduler. The factory patch is scoped/restored; experiment concurrency uses processes. Original v0.2 remains directly runnable and its old failure remains reproducible. The known test becomes a normal regression targeting the repair **only after it actually passes**, with the same TP==1 assertion; a separate baseline regression preserves the old failure and archive equivalence.

## Small validation gate

Before matrices: exact original failure, real-C spike/return without a later event, spike/return with a new event, persistent step/FAULT and repeated-impulse probes, normal healthy sustained event, recovery plus healthy-other-channel event, cross-channel fault isolation, long-lived BLOCKED released by a qualifying return, no confirmed-episode duplicates, bounded pending demand, valid intervals, causal-prefix/unsampled guards, disabled-repair equivalence, v0.1/v0.2 exact archived output. State-machine tests cover near-reference return versus opposite overshoot, health transition alone, deadline and confirmed release. Preserve every failed assertion/log.

## Seed audit and fixed experiment

Historical Git manifest/metrics/events/freeze/audit blobs and local numeric archive directories show used/predeclared0–99, no100–149. Audit scope/results are retained before new generation. Unrecorded external work cannot be attested. Proposed split is fixed now: development100–109; validation110–119; final120–149. Seed91 is a regression only. No parameter fitting or point selection is planned.

Two suites, **reported separately, never pooled**:

- `main`: unchanged45 v0.2 cases, original +/-30 s fault jitter. This estimates behavior on the existing scenario distribution, where a one-second impulse is often never sampled.
- `aligned_recovery`: the six spike none/same/cross x short/long cases, changing only fault_jitter_s to0 (fault starts600, event60 s later). This deliberately ensures exposure to the recovery transition identified in diagnosis; it is a controlled mechanistic challenge, **not natural fault prevalence**. All strategies receive the same modified latent/noise/fault schedule. It is declared before development/final data and cannot justify general superiority.

Methods: actual AdaptiveSense(1), original TAIS v0.1, original V02, original V02-Passive, V02-Rearm. All latter four retain multipliers[.75,1,1.5].13 points/case; main585+challenge78=663 scored runs/seed. Development6630, validation6630, final19890 (main17550, challenge2340), total33150. Plus clean counterfactual replays, offline only. Same physical truth and upstream one-to-one onset matching/tolerance5 s, false attribution120 s and payload definition as v0.2. No-event recall N/A.

Primary paired contrasts: repair minus unfixed V02 at each multiplier, overall and separately same/cross/clean/sequential and spike-recovery groups. Report TP/misses/recall, strict and fault-induced false reports, conditional latency, samples, uploads and bytes; retain diagnosis and per-channel reconstruction metrics too. Whole-seed2000 bootstrap, RNG731, descriptive95% CIs; no multiplicity-adjusted superiority claim. Count deltas per seed batch in the named suite/group. Report all declared points and two tradeoff plots.

Before opening120–149: small tests must pass, complete development/validation review, freeze repair/config/analysis source hashes and commit. No tuning after final; any negative/null or cost-increasing outcome stays. If improvement occurs only in aligned spike recovery, say so. Low exposure in random-jitter main is not proof of equivalence. Evaluate whether to retain this as a targeted correctness repair separately from whether TAIS outperforms v0.1.

## Limits

Returned values are observational evidence, not proof a physical fault ended. Fault oscillations, persistent offsets and overwritten same-channel events remain ambiguous. This repair does not solve all BLOCKED causes (e.g. timeout without observed return), guarantee every healthy event, compress payload, measure RF energy or acquire real greenhouse data. New final seeds become used once opened. No mechanisms will be stacked merely to improve final outcomes.

## Small-gate observation before any matrix run

The repair actually restores the original seed91 assertion at multiplier1: matched TP0→1, report675, samples78 unchanged, uploads39→40. The new state suite initially gave66 passed/2 failed because its *additional* all-points TP==1 assertions also required success at1.5. Investigation (retained log) shows original v0.1, unfixed v0.2 and repaired policy all miss both profiles at1.5:665/670 raw scores exceed12,675 falls to11.8787 before the unchanged10 s debounce. The repaired state is IDLE, not BLOCKED. This is a separate existing score/debounce limit; changing it would exceed this repair. Both TP==1 assertions remain intact as strict expected failures, and normal state-boundary tests prove the latch is released. No threshold was changed, no failure deleted, and the original known multiplier1 regression is promoted to an ordinary test only after its real replay succeeds. All initial failures are retained. The targeted suite will report this unfavorable point too.
