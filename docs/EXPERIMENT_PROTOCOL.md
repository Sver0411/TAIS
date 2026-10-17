# Experiment protocol

## Phase 0 — freeze and reproduce the baseline

From the repository root, run the existing commands:

- python -m pytest tests/ -v
- python scripts/check_config_parity.py
- python dataset/generate_dataset.py
- python analysis/analyze.py

Record the commit SHA, Python version, dependency versions, test summary, and checksums of the baseline result CSVs. Do not modify the existing AdaptiveSense baseline results to make TAIS look better.

## Phase 1 — controlled synthetic benchmark

### Signal and independent labels

Start from the existing 1 Hz synthetic scenarios and generator. Extend the generator in a separate TAIS directory or config; do not silently change the seven existing scenarios.

For each run, preserve separate artifacts:
1. latent environmental signal before measurement noise/fault injection;
2. observed signal after noise;
3. event labels generated from the latent signal using a predeclared physical-unit deviation and duration rule;
4. fault labels generated from the fault-injection schedule;
5. sampled observations and scheduler/upload decisions.

Never derive ground truth from AdaptiveSense or TAIS detector output.

### Fault cases

At minimum:
- clean channel / no fault;
- out-of-range value;
- isolated spike and spike recovery;
- stuck/flatline;
- gradual drift;
- missing/invalid readings;
- stable in-range offset (documented SensorTrust blind-spot probe).

Test three separate relationships:
- fault without a true environmental event;
- true event on a healthy channel while another channel is faulty;
- true event and fault overlapping on the same channel.

Include fault recovery and more than one fault intensity/duration. The single-channel ambiguity case must be reported separately, not hidden in pooled averages.

### Seeds and split

Use deterministic seeds. A proposed initial split is seeds 0–9 for development, 10–19 for validation/parameter selection, and 20–49 as held-out test seeds. Fix this split before examining held-out results. If the implementation makes the 50-seed run too expensive, justify any reduction before final testing.

### Strategies

1. Fixed-rate sampling at all existing intervals.
2. AdaptiveSense as currently implemented.
3. AdaptiveSense with SensorTrust in diagnostic-only mode (health is logged but does not affect decisions).
4. Trust-gated policy without bounded confirmation sampling.
5. Full TAIS.
6. Optional threshold-proximity cue ablation, evaluated separately.

Tune only on development/validation runs. Use identical signal seeds and injection schedules for paired comparisons. Do not let one strategy see future readings when making its next-sample decision.

## Phase 2 — public greenhouse trace

Dataset: Hull et al. (2023), “Dataset of temperature, humidity, and actuator states of an east-facing South African Greenhouse Tunnel.” DOI: [10.17632/54htxm94bv.1](https://doi.org/10.17632/54htxm94bv.1). Data are available from [Mendeley Data](https://data.mendeley.com/datasets/54htxm94bv/1), CC BY 4.0. The full dataset contains 162 days, three spatial positions, temperature/humidity, and fan/wet-wall state at 5-minute resolution.

- Provide a downloader/instructions, not a silently altered copy. Store raw data outside version control by default and record the source/version/checksum.
- Preserve the original time ordering and missingness. Document any filtering/resampling.
- Evaluate only intervals that the 5-minute resolution can support (e.g. 5, 10, 15, 30, 60 minutes). Do not make sub-minute claims from this dataset.
- Use actual fan/wet-wall state transitions only as a **control-transition reference/proxy**. They are not labels for every environmental event.
- Inject faults into a copy of one channel using a separate seed while retaining the original trace as the latent environmental signal.
- Report reconstruction MAE/RMSE against the full trace, sampled-point count, upload count, and retention/detection around control-state transitions. Clearly distinguish these results from the synthetic ground-truth event experiment.

## Metrics

Primary:
- event recall = TP / number of independently labelled events;
- fault-induced false environmental detections and false alarms per hour;
- event detection latency;
- application uploads at a matched upload budget / the event-recall-versus-upload trade-off.

Secondary:
- missed-event count, precision, redundant detections;
- samples taken, application upload count, estimated payload bytes;
- reconstruction MAE/RMSE on the full trace;
- fault episode detection recall and wall-clock detection latency;
- health-state transitions and diagnostic sample overhead.

Use channel-aware one-to-one event matching and the existing metric definitions where appropriate. For scenarios with no true events, event recall is N/A, not 0%. Aggregate counts across scenarios (micro aggregation) rather than averaging percentages.

## Statistical reporting

- Report each scenario and the pooled result; do not hide poor short-event or same-channel fault cases in one average.
- Use paired comparisons on the same seed/trace and report 95% bootstrap confidence intervals over held-out runs.
- Plot the Pareto trade-off between event recall and application uploads; a single arbitrarily chosen operating point is insufficient.
- Tune only on development/validation runs and lock the method before final held-out testing.
- Do not claim statistical significance unless the analysis supports it.

## Energy and communication terminology

- Report sample count, application upload count, and estimated application payload bytes.
- A dimensionless upload proxy is not energy in joules/mJ.
- Application payload counts exclude Wi-Fi beacons, TCP acknowledgements, MQTT keepalive, retransmissions, and radio overhead.
- Physical energy claims require a current monitor and a separately documented hardware experiment.

## Minimum completion gate

Before writing a performance claim, the project must have:
- passing tests and baseline reproduction evidence;
- an independent event/fault ground-truth pipeline;
- all required baselines and ablations;
- held-out test results and confidence intervals;
- a results README stating what was simulated, what used real data, and what remains unmeasured;
- a limitations section covering SensorTrust's stable-offset blind spot and same-channel event/fault ambiguity.

## Frozen v0.1 execution contract (2026-10-17)

The sections above record the migrated proposal. This section fixes the executable choices where the proposal left details open.

- Full split retained: 10 development, 10 validation, 30 test seeds. No tuning or point selection: every threshold multiplier [0.75,1,1.5] is reported. The code/config commit preceding the full runs freezes all methods.
- 45 scenarios per seed: clean no-event, clean long-event, clean short-event; seven fault types (range, 1-second spike, stuck, drift, missing, NaN-invalid, stable offset) x three relationships (no event / healthy other-channel event / same-channel event) x two profiles. Profiles jointly vary duration, event duration and intensity; they are not a factorial sensitivity study.
- Each run is 1800 points at 1 Hz. Fault starts at 600 +/-30 s from an independent seeded RNG. Short/long faults last 240/600 s (spikes always 1 s); event starts 60 s later and lasts 26/180 s including 5 s ramps. Amplitudes 4 C /16 %RH. Long faults use intensity 2; short use 1. Config is authoritative.
- Same seed and relationship/profile share bit-identical latent/noisy signals across all fault types. Each method gets exactly the same post-intervention observations. A clean counterfactual uses the identical noisy pre-fault trace, never future online values. Counterfactual outputs are used **only offline** for metrics.
- Truth is the unchanged upstream generator's `label_events()` applied to noise-free driven physical offsets: >=1.5 C /8 %RH deviation and >=10 s. Generator code and fault schedules never invoke a detector. Fault labels are schedule intervals, even when never sampled. No-event recall is blank/N/A.
- 13 operating points per scenario: five fixed rates, original AdaptiveSense, logging-only, GateOnly x3 and TAIS x3. 585 runs per seed, 5850 development +5850 validation +17550 test =29250 scored runs, plus cached clean counterfactual replays.
- Match reports channel-wise one-to-one with unchanged upstream `match_events`, +/-5 s tolerance around the physical event interval. Strict false reports include redundant onsets. Local detection TP is separately recorded. Upstream reproduction uses its original local-detection metric and is not relabeled TAIS evidence.
- Fault-associated false reports are unmatched onsets on the injected channel inside [fault start, fault end+120 s). Operational fault-induced count further excludes any onset within 5 s of an identical method's clean-counterfactual onset. This onset attribution is limited: fault-altered sampling times can shift a report. It is not proof of physical causation.
- Fault detection: any C fault flag during the injected interval; type-specific flag detection reported separately. Offset has no corresponding C bit. Delay uses first flagged sampled timestamp; misses have N/A delay, not zero. Fixed/plain baselines have no health detector and zero detected episodes by construction. Health false alarms on clean traces remain available in archived records but are not a primary summary metric.
- Reconstruction: causal zero-order hold from all finite sampled readings and, separately, requested uploads, evaluated against full latent temperature/humidity; per-channel MAE/RMSE and coverage are separate. No future interpolation online. No normalization hides different physical units.
- Counters for diagnostic/confirmation demand are not additive energy estimates. Diagnostic-only excludes confirmation and active environmental cycles. Incremental sample overhead is a paired count comparison, not the diagnostic flag count itself.
- Micro aggregate event counts. Bootstrap whole seed clusters (2000, fixed RNG 731) preserves all scenarios/method pairing. Absolute recall/upload and paired differences have percentile 95% intervals. Difference CIs are descriptive; no multiple-comparison significance claim. All operating points and nearest actual baseline budgets are saved; a budget gap is not silently treated as matched.
- Signals and decisions are canonical gzip JSON with sha256 manifests under ignored results/traces. JSON null denotes missing/nonfinite data; fault type distinguishes injection mechanism. Metrics/config/figures/logs/manifests are committed. Regenerate full traces with the run commands.

### Reporting clarification discovered during development analysis

The raw `relationship` field describes assigned channel placement. Clean event controls use `same` internally to select the temperature channel; they are **not fault-overlap cases**. Also, a one-second spike at fault start precedes the event (which starts 60 s later). Its cross/same placement is temporally sequential, not overlapping. No trace or test result is discarded or relabeled as concurrent. Analysis explicitly separates `clean`, `cross_sequential` and `same_sequential`; `cross` and `same` aggregate only the 12 actual overlapping cases per seed (six other fault types x two profiles). All four sequential spike cases remain in by_scenario and overall tables. This corrects the proposal's overly broad relationship wording without changing any signal, threshold, method or held-out sample. A future suite should additionally align isolated spikes within events and vary their timing independently; v0.1 does not claim that experiment was run.

Plots show every operating point and a clearly labeled policy zoom. No method point is selected from held-out outcomes; annotation changes do not change experimental measurements. TAIS-minus-GateOnly paired intervals directly report incremental confirmation cost and benefit.
