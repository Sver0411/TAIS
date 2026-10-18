# FO-1: fault–event timing and observable evidence

**Protocol fixed before new trajectories.** Base `5b06d2feae44db2b3503697d246f51c43e5d8f2e`; branch `research/fault-event-observability`. This is a synthetic timing benchmark, not TAIS v0.3, an algorithm search or a reversal of the budget-matched **NO-GO**. GateOnly remains the primary simple competitor. No detector, trust/scorer, original source/config/test/result or upstream is changed.

## Sources, seed audit and execution order

Read the original research report/protocol/specification, original generator/scheduler/replay/metrics, BM-1 protocol/report/selection/manifests/history protection. Actual original setup: 1800 seconds at 1 Hz; fault onset 600±30 seconds from an independent seeded schedule; events driven 60 seconds later; spike 1 second; short/long faults 240/600 seconds and intensity1/2; events26/180 seconds with5-second ramps, amplitude4 C/16%RH. Profiles jointly change duration and intensity; this study does not independently identify those physical effects.

[Before-run audit](../results/fault-event-observability/seed-audit.json): 565 structured files,261 historical structured Git blobs across accessible refs (including deleted/replaced versions),185,039 gzip paths, complete compressed CSV/link seed metadata, ignored archives and TAIS-external-data. Reserve0–199; no200–299 collision found. Full path inventory and protected bytes are pinned outside tracked results. Inaccessible external machines/runs are outside the audit's claim.

Freeze **development200–219, validation220–239, final240–299**. No overlap. All are new random seeds from the same generator family, not real-environment external validation. No parameter search in any split. Before final execution, commit this protocol, all new implementation/config/tests, completed development/validation manifests and a final lock of source and calibration hashes. Final run opens an exclusive output directory/start marker and executes each locked configuration once. No force/overwrite/retry-final facility. Failure retains partial outputs and is reported incomplete. Only old seed20 is used for software smoke/debug fixtures before new data.

Before final, implementation bugs may be corrected with recorded changes. If a correction affects generator, label definitions or protocol, refreeze with genuinely unused final seeds. No correction driven by final results is allowed. This protocol may not be silently revised after final access.

## Hypotheses and exact matrix

H1: spike benefits may depend on relative timing; sequential recovery benefits need not extend to concurrent event contamination. H2: persistent drift's effects may depend on duration and actual event overlap. H3: channel placement may affect available event evidence. H4: detection, fault flags and physical attribution are different; some latent states may be observationally indistinguishable. None is assumed true.

[Versioned configuration](../configs/fault-event-observability.json) enumerates all **93 unique IDs**:

- All45 original cases delegated exactly to the historical `signals.generate()` with original config.
- Spike ×same/cross ×short/long ×offsets[-60,-10,-1,0,1,10,60].
- Drift ×same/cross ×short/long ×offsets[-500,-220,-60,0,60,220,650].
- `event_plan_start = fault_start + offset`. Each +60 combination already exists among the45 original cases. The other6×4 offsets add24 cases per kind,48 total. Never count default twice or delete a case after results. Offset names identify configuration, not physical overlap.

Independent `observability_signals.generate()` delegates new cases to the same historical generator with an isolated deep-copied **generator-only event_delay_s**; the scheduler still receives the original config, multiplier1.0. This preserves noise RNG draw order, amplitudes, faults, physical labels and recovery behavior. No source edit or new detector. Save separate latent/noisy/faulted observations, truth, intervention metadata and all raw decisions/reports with deterministic gzip SHA256.

Physical labels use unchanged upstream `label_events()` on noise-free driven offsets: >=1.5 C/8%RH for>=10seconds. Event labels therefore start after ramp onset (typically+2/+3seconds), not at the nominal plan start. In particular spike offset0 or−1 is **not assumed concurrent** with the labeled event. Compute overlap from every actual label and injected interval.

Truth labels include their final1-Hz point; fault injection is `[start,end)`. Save geometric intersection duration `max(0,min(event.end,fault.end)-max(event.start,fault.start))` and the count of integer timestamps satisfying both `event.start<=t<=event.end` and `fault.start<=t<fault.end`. Classify overlap by shared observation count>0, including boundary-only intersections with duration0. Otherwise classify event-before-fault if event.end<fault.start, fault-before-event if event.start>=fault.end; clean/no-event explicitly separate. Save overlap endpoints, first-start order, nominal offset and event/fault intervals. These definitions are fixed before outcomes.

## Policies, causal access and counterfactuals

Only original AdaptiveSense, GateOnly and TAIS at **multiplier1.0**. TAIS is original frozen v0.1, not v0.2/Rearm. Existing C11 SensorTrust, scoring, health responsibilities, confirmation count/duration, blocking, sampling bounds, uploads and event matching remain unchanged. AdaptiveSense has no health diagnosis; its structural zero flags do not establish diagnosis inferiority under equal information. TrustLog has identical scheduling and is not duplicated as an independent policy.

Every method sees bit-identical post-injection input within seed/case; hash latent/noise/observed/truth/faults. Only actual sampled values enter Scheduler.update(t,values). Truth, plans, future/unsampled values and latent signals remain replay/evaluation data. Replacing hidden truth or future suffixes must not change prior sampled decisions in software tests.

An identical-noise **clean counterfactual** is replayed only offline for the unchanged evaluator. Cache by exact clean observation/truth hash and method, never just relation/profile when offsets differ. Retain cached replay and case pointers. Counterfactual unmatched-onset attribution is operational, not unique physical causation: intervention-driven scheduling can shift onset times. No new classifier or source-attribution decision is implemented.

## Outcomes and grouping

Use original channel-aware one-to-one report matching with5-second interval tolerance. Save per-event matches/misses and report/first-fault-flag times. Primary outcomes: micro Recall,misses,fault-induced false reports,strict unmatched reports,conditional event delay,any-flag/type-specific fault detection and conditional first-flag delay. No-event Recall/delay are N/A. Precision/F1, local TP,redundant/associated reports, false/hour, per-channel causal reconstruction, confirmation/diagnostic annotations also retained.

Resource metrics: actual samples,upload requests,exact original compact JSON envelope bytes. Preceding sampling interval means the **previous record's scheduled interval** immediately before each report, not the report's next interval; timestamp0 has none. Save per-report intervals and totals/denominators. Count sampled points in event,fault and overlap intervals to expose missed evidence. Diagnostics are demand annotations, not measured causal extra sampling; only paired total differences quantify actual additional samples. Counters may overlap and are not additive energy costs. No Binary protocol development, radio bytes or energy conversion.

Separate event-and-fault-detected, fault-flagged-but-event-missed, event-detected-with-no-in-interval-fault-flag, event-detected-with-flags-but-wrong-type. These are **joint detection descriptors, not physical attribution accuracy**. No unique environment-versus-fault classifier exists, so physical attribution accuracy is N/A. A matched report can be numerically fault-driven; its coincidence with truth does not prove causal recognition.

Report all93scenarios, original/added cohorts, each fault kind/clean, same/cross/none,short/long, event-present/absent, actual temporal classes and first-start order. All56 timing cells (including the8 default cases once) receive summaries and paired intervals, plus pooled kind×offset and kind×topology/temporal groups. No unfavorable point or undefined metric is removed. Overall pooling is a balanced benchmark mixture, not a natural fault prevalence estimate.

## Paired statistics and multiplicity

Resample whole original **seed clusters**, retaining all paired cases/methods.10,000 paired percentile Bootstrap replicates, RNG2026101811;95% CIs. Micro event metrics use pooled counts; delays are conditional and use detected counts. Additionally compare latency only on events detected by both GateOnly/TAIS (same truth IDs), report cohort size/misses. Resources and false counts show raw cohort totals and per-run differences. Do not treat measurements/scenarios sharing a seed as independent replicates. Same-seed scenario reuse also preserves noise and schedule dependencies.

Fixed **12-test primary interaction family**: six contrasts ×two outcomes, Recall and fault-induced false per run. Let Δ(group) be TAIS−GateOnly at that group. Contrast is Δ(left)−Δ(right), computed per seed from the same fixed scenario cells; for Recall each event-bearing cell has one truth, for false reports divide by cell count. Contrasts:

1. Spike dt−10 minus dt+60, pooling both profiles/topologies. −10 overlaps labeled truth for both profiles; compare concurrent contamination to original sequential spike.
2. Spike dt−60 minus dt+60. Profile interaction retained descriptively: −60 is sequential for short and overlapping for long; do not call it a uniform overlap contrast.
3. Drift dt0 minus dt+60, pooling profiles/topologies.
4. Drift dt+650 minus dt+60 (post-fault event versus overlapping default).
5. Spike cross minus same, pooling all7 offsets and both profiles.
6. Drift cross minus same, pooling all7 offsets and both profiles.

Report95% and **Bonferroni familywise99.583333%** intervals (alpha0.05/12) for every primary contrast, including null/unfavorable results. Claim statistical interaction only when adjusted interval excludes0; directional conclusion additionally must survive deletion of each seed and each contributing scenario (direction only). No post-hoc replacement by another offset/group. Other cell/group intervals and deletion tables are descriptive; no subgroup-wide significance claim. Record valid Bootstrap draws for undefined ratios. Contrast plots show all predeclared offsets, not a fitted/interpolated optimum.

## Observable evidence, failure criteria and research decision

Analyze: event-channel readings altered vs unaffected; whether a healthy channel actually carries the event; whether sampling sees a1-second spike or any labeled event point; timing of C flags; similar additive drift/event changes. Cross placement here gives a true **humidity** event, not a second colocated temperature reference. Better cross performance cannot establish benefit of a newly implemented cross-sensor fusion mechanism, or isolate topology from differing channel amplitude/noise/trust settings.

Inspect original range/missing/invalid/stuck same-channel pairs for equality of observed streams **during erased windows**, separately from full-run sequences. Identical erased windows do not prove full-run equivalence if outside-window events differ. Exact full-stream/prefix equivalence is stronger than poor scheduler performance; this benchmark alone is not an information-theoretic identifiability proof. No additional classifier/information upper-bound experiment is smuggled in. Nonidentifiability of latent decomposition under unmodeled additive biases is a stated boundary, not an empirical detection result.

Stop before final if population, truth, caching, source hashes, causal-access or reproducibility checks fail. Do not trim a broken case. Infrastructure failures retain incomplete artifacts. If final complete: preserve BM-1 NO-GO; stable adjusted interactions may motivate a **separate** future question on timing/drift observables or healthy independent evidence. Persistent false reports favor studying drift ambiguity rather than extending confirmation duration. If no adjusted robust pattern, report insufficient evidence and stop mechanism development. No universal per-case attribution guarantee, natural-fault validation, budget-matched causal comparison or deployment claim is permitted. No final-result-based threshold/protocol changes.
