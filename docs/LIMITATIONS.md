# Limitations and failure boundaries

- This is a host simulation. No field deployment, radio model, measured current, joules, battery-life claim or embedded resource benchmark.
- SensorTrust is a heuristic detector. A persistent valid offset may look healthy; an actual sustained environmental ramp can resemble drift. Confirmation tests persistence, not physical causality.
- Same-channel event plus fault can be unidentifiable. Fault replacement can erase the true signal. Recovery reseeding prevents stale-history alarms but can miss an event already in progress.
- Stable-offset and slow-drift blind spots are explicit scenarios, not evidence of complete fault coverage. STUCK/DRIFT confirmation windows are sample-based: sparse sampling delays or misses diagnosis. One-second spikes can occur wholly between actual samples.
- Independent physical-unit event labels are synthetic interventions. Event duration and fault intensity vary together in two profiles, so this version is not an independent factorial analysis of those factors. Only two environmental channels and one injected faulty channel are studied. Multi-fault combinations and real fault distributions need future work.
- There is no finite universal guarantee that gating preserves every healthy-channel event. Channel isolation prevents direct veto; different shared schedules can still miss brief healthy events. See short and cross scenario results.
- Counterfactual-new false reports are an explicit operational attribution, with a 120 s post-recovery window and 5 s onset comparison. A changed sampling schedule can shift an otherwise similar alarm, and effects later than 120 s are excluded. Report all strict unmatched alarms alongside this metric.
- Reconstruction is simple causal zero-order hold from finite raw values, including annotated faulty values, compared to latent signal. There is no fault repair, model-based reconstruction or imputation benefit hidden in TAIS.
- Payload bytes are actual serialized simulated application envelopes. Health logging has metadata costs; they are not calibrated radio bytes. No transport delivery success is simulated. Local detections and upload-requested reports are separate.
- Diagnostic/confirmation demand counts overlap other scheduling needs. They cannot be added as extra samples. Paired total sample counts measure actual incremental sampling under each policy.
- Bootstrap CIs cluster by seed on this fixed scenario suite. They do not describe uncertainty across farms, sensors or climates. Many descriptive comparisons are not multiple-testing-adjusted significance tests.
- Baseline experiments and TAIS have different signal suites. The former is an exact separate upstream reproduction; only same-suite same-seed methods in TAIS may support relative comparisons.
- Closest literature methods are reviewed but not reproduced as runnable baselines. No superiority to AAS, CLARA or sentinel methods, and no first/novelty claim.
- Greenhouse download/API access and actual file validation status are reported in data/README.md. Documentation of nominal fields/resolution is not empirical verification of raw-file missingness. No real-greenhouse TAIS result is claimed unless the raw-file audit and replay actually succeed.
- Optional control-threshold proximity is deferred. Reinforcement learning, neural methods, multichannel corroboration and firmware integration are outside v0.1.

During development analysis, two reporting distinctions were made explicit: clean temperature events are not same-channel fault cases; and the generated one-second spike occurs 60 s before the event. Its cross/same cases are reported as sequential, while actual cross/same overlap tables exclude them. All raw traces and all 45 scenario outcomes are retained. Concurrent single-spike/event robustness remains untested.

Sensor-specific ranges and spike thresholds are proposed heuristic settings, not field-calibrated sensor specifications. The hand-designed event/fault amplitudes and absence of tuning do not remove benchmark-design bias. Robustness across thresholds, physical sensor types and independently varied interventions needs further work.

## v0.2 forensic and validation additions

The old same-channel recall gap includes18 range matches that appear identically in event-free observed streams. This is a limitation of temporal matching as evidence of causal event sensitivity; historical numbers are preserved. Four replacement/missingness interventions produce observation-identical event/no-event pairs. Their primary recall is still reported, accompanied by the information-erased subgroup.

V0.2 changes one candidate episode policy. A frozen EMA and persistence count cannot distinguish physical environmental change from additive drift or offset. The passive ablation removes accelerated pending demand, but confirmed event priority can still change future sampling and hence C diagnosis. It is not a fixed-schedule control. The hard FAULT gate remains; unsupported event recovery is not promised. Blocking until low raw score may also discard later genuine changes before rearm. Detailed execution traces expose these failures.

The scenario suite intentionally retains the old45 definitions. It has two jointly varying profiles, and its single spike precedes the event rather than overlapping it. Fresh random seeds do not correct structural benchmark bias or establish unseen fault-type generalization. The old test seeds20–49 are diagnostic; v0.2 final50–99 were frozen before opening and are now used, so any subsequent result-driven design needs another untouched set.

Offline logs are not transmitted bytes, and their storage/CPU cost has not been benchmarked on an embedded node. Application payload remains verbose JSON; v0.2 does not solve the health metadata overhead. No additional greenhouse raw data was acquired in this phase; actual field validation remains incomplete. Previous403 evidence is retained without claiming a new successful download.

The false-report metric counts unmatched **episode onsets**. A persistent CONFIRMED episode can merge what would otherwise be several onsets. A lower false-report count therefore does not by itself establish less time spent falsely active; false-active occupancy is not a primary measured metric here. Do not interpret persistence as reliable environmental cause identification.

Final v0.2 evidence is conditional: same-channel improvement occurs only at multiplier.75 and consists of six detections169–174 s after onset; multipliers1/1.5 have no same-channel improvement. Seed91 demonstrates BLOCKED suppressing a later healthy event after a returned spike. It remains a strict expected-failure regression; no post-final algorithm correction was made. See the v0.2 interpretation and complete paired CIs.

## Optional BLOCKED reference-return repair

The preceding v0.2 findings describe the frozen strategy. The subsequent optional `V02-Rearm` strategy addresses seed91 with a separate Evidence subclass; the original v0.2 module and report remain intact. See [repair interpretation](BLOCKED_REARM_INTERPRETATION.md) and [all operating points](BLOCKED_REARM_REPORT.md). The repaired multiplier1 regression passes normally; two additional1.5 score/debounce boundary assertions remain strict expected failures.

An observed numerical return inside the existing threshold band is not proof of physical fault recovery. Continuing drift can cancel an unconfirmed candidate and later produce additional false episodes. Final main fault-attributed/total false reports increase by2 at0.75 and6 at1.5, with extra sampling/upload costs. At1 the small main recall difference has a95% CI including zero. Deliberately aligned sampled-spike recovery yields a much larger conditional benefit, but does not estimate real fault prevalence, concurrent same-channel robustness or superiority to v0.1. Continuing CONFIRMED episode release semantics are unchanged; passing no-repeat regressions do not establish a universal guarantee under arbitrary recurring faults.

Main random-jitter and aligned recovery suites must remain separate. All seeds100–149 are now used. Further result-driven design requires a new untouched test set. No real-greenhouse or radio-energy validation was added in this repair.
