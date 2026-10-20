# BM-1: budget-matched confirmation-mechanism evaluation

**Frozen before new development/validation/test generation.** Base `97feccb36acb6790b40be31e3cee1661e8811a61`; branch `research/budget-matched-policy-eval`. Question: does the existing v0.1 TAIS confirmation policy provide independent value against GateOnly at matched sample/upload budgets? No assumption of superiority. No algorithm, thresholds in historical files, generator, truth rules, trust C code, Wire1/2 or OSP result is modified. This is a new-noise test under the **same synthetic generator**, not external/real-deployment validation.

## Seed audit and scope

The before-run [audit](../results/budget-matched/seed-audit.json) examined419 accessible structured files,224 historical Git blobs (including deleted/replaced artifacts across all refs),150,120 gzip paths, ignored scratch/archive records and TAIS-external-data. Gzip CSV and complete wire link JSONL seed metadata were read; large synthetic archives also retain pinned numeric seed path identities. All0–149 are conservatively reserved. No150–199 execution evidence was found. Source seed/generate references were reviewed; prior text suggesting150+ was not treated as an executed experiment. Auditing cannot establish absence of inaccessible external runs. The full29.5MB path inventory is compressed outside tracked results with a recorded SHA; the versioned audit retains all structured/Git evidence, seed union and inventory fingerprint.

Allocate development150–159, validation160–169, final170–199, with no overlap. Final generation is prohibited until both calibration phases and committed parameter selection are complete. Software smoke checks use only already-used seed20, never final seeds. The seed reservation is recorded before generating any new trajectory. Main configuration: [budget-matched.json](../configs/budget-matched.json).

## Fixed population, methods and permissible parameter space

Use the unmodified `tais.signals.generate`, all45 existing scenarios,1800seconds/1Hz latent source per run; all seven fault kinds,none/same/cross relationships,short/long profiles and three clean controls remain. Labels retain independent physical-unit event truth and fault schedules; `match_events`,5second event tolerance,120second fault attribution and per-channel health outputs are unchanged. Inputs/truth/fault/noise are shared identically across methods within each(seed,scenario). Hash and archive every signal, sampled stream, report, detection and clean counterfactual.

Four actual existing methods: AdaptiveSense, AdaptiveSense+TrustLog at1.0; GateOnly and TAIS share the **same frozen scheduler implementation**, distinguished by its existing `confirmation` switch. They use the same SensorTrust C11 bridge and upstream scorer. No v0.2/Rearm mechanism is imported. Every sampling bound, ladder, heartbeat,diagnostic interval,confirmation count/duration and upload trigger remains unchanged. Permitted calibration variable is only the existing `multiplier` argument, scaling stable/active/event thresholds together as upstream already supports.

For both GateOnly and TAIS, complete grid:
`[0.5,0.625,0.75,0.875,1.0,1.25,1.5,1.75,2.0]`.
This is0.125steps over[0.5,1],0.25steps over[1,2]. No expansion/refinement after results. All9points ×2methods +2context baselines =20operating points/scenario,9,000 scored runs/development and9,000/validation, plus independently archived clean counterfactuals. All points/outcomes are retained; no fault class or unfavorable row is excluded.

## Three predetermined budgets and unique selection rule

Budgets are named **B0.75, B1.00, B1.50**, anchored to GateOnly at multipliers0.75,1,1.5. Development budget vectors are that anchor's **mean samples/run and mean uploads/run**, averaging all450 development runs equally. These vectors are resource observations, not outcome-optimized targets. Existing default historical gaps are already below1%; that fact does not establish confirmation value or bypass fresh calibration/test.

Enumerate every actual grid pair(Gate multiplier,TAIS multiplier). A calibration-feasible pair must satisfy:

1. Development **and** validation: `abs(TAIS-Gate)/Gate <=0.01` for each of total samples and uploads, independently. No rounding to make a point feasible.
2. Development: each method's mean samples/uploads must remain within2% of the development anchor vector, keeping the point tied to its declared budget. This is not an additional final-test acceptance tolerance.

Validation therefore filters a fixed development grid; it does not define new budgets or thresholds. Among feasible pairs, select lexicographically:

1. Prefer a **common multiplier** when one is feasible (better isolates confirmation).
2. Lowest worst relative deviation of either method's development sample/upload mean from the fixed target.
3. Lowest maximum pair resource gap over both resources and both calibration phases.
4. Lowest sum of absolute deviations of both multipliers from the anchor.
5. Lowest Gate multiplier, then TAIS multiplier.

Only resource fields enter selection, never TP,Recall,false reports,latency,bytes or subgroup outcomes. If no feasible pair exists, freeze the same-anchor pair as a **descriptive unmatched fallback**, never a matched success. All candidate pair feasibility and ranking data are retained. Duplicate chosen pairs across budgets are recorded, not counted as independent evidence.

After selection, commit a JSON lock with all three choices, target vectors, calibration CSV/manifest hashes, protocol/config/source hashes and final run matrix. Final matrix includes selected pairs plus both policies at all three native anchors as descriptive common-threshold controls, and both context baselines at1.0. Deduplicate identical operating points; at most14points/scenario,18,900 final scored runs (usually8points/10,800). Every final configuration is frozen before test generation. If selected multipliers differ, the primary claim is about calibrated policy configurations, not a purely isolated causal confirmation effect; show the common-threshold controls as context.

Final test is one execution of that matrix for all30seeds ×45scenarios; an exclusive start marker/output directory prevents accidental repetition. No test metric may select another pair, budget, scenario or rule. On runtime failure retain partial artifacts and report incompleteness; do not silently regenerate a successful-looking final run. Outcomes from all declared budgets are reported, even if unmatched/unfavorable.

**Final matching:** for each locked pair, independently check actual final total samples and uploads with the same1% Gate-denominator rule. Calibration match does not guarantee final match. A budget is inferentially eligible only if calibrated-feasible **and** final resources meet both tolerances. Report final deviation from the original development vector separately; new noise can move the absolute budget vector, and that is not silently treated as the original exact target. No cap, interpolation, resampling, post-hoc thinning or mixed configurations can manufacture a matched result.

## Outcomes, costs and matching

Primary outcomes: micro event Recall; strict unmatched environment reports; fault-induced false reports; samples; upload requests; application bytes; matched-event detection delay. Report Precision,F1,misses,redundant reports,per-hour false rates,local pre-upload detection, fault-associated errors, fault detection/type rates and delay,confirmation/diagnostic overhead and reconstruction MAE/RMSE/coverage. No-event Recall is N/A. Precision=TP/(TP+strict unmatched); F1=2TP/(2TP+FP+missed), undefined denominators remain N/A.

Primary byte accounting is original exact JSON envelope length, unchanged from `replay.py`; additionally report the existing **stateless Binaryv1** costs for every method equally. Do not use stateful v2, new codecs or compression tuning. Cost is application serialization only, not joules or radio packets. Individual health observations may differ because actual sample schedules differ; health **implementation** and matching inputs are common, not artificially forced into equal outputs.

Generate the exact clean-noise counterfactual for each method/multiplier/seed/relationship/profile for offline fault-induced attribution, as the original evaluator does. Labels/counterfactuals never enter `Scheduler.update`. Retain event-level truth IDs and matches; compare conditional average delays with misses/TP, and separately delay on events matched by **both** configurations to expose survivor bias. No imputed zero delay for a missed event.

Micro aggregate counts; event/fault detection delays are conditional means using their detected counts. Reconstruction averages use valid reconstructed-time coverage weights; RMSE pools squared errors before square root. Complete per-run raw metrics remain available independently of aggregate choices.

## Paired statistics and subgroup discipline

Cluster by original seed, preserving all paired scenarios/configurations within a resampled seed.10,000 paired percentile Bootstrap draws, fixed analysis RNG2026101810. Report95% intervals for absolute outcomes and TAIS-minus-Gate differences (Recall in fractions/percentage points; counts as total cohort differences and per-seed differences; resource ratios and raw totals). No per-observation pseudoreplication. Undefined ratio/delay replicates remain N/A with valid-draw counts reported, not replaced with0. Use paired input hash equality and per-event IDs.

Predetermined groups: overall; each of seven fault kinds and clean controls; fault+event same-channel; fault+event cross-channel; no-event fault scenarios; all no-event scenarios; clean event scenarios; short and long profiles; and each individual45scenario. These overlap and are not independent tests. Group confidence intervals are descriptive, not alternative paths to GO. Conditional common-matched delay differences are clustered by seed and show paired-event counts.

Three budget points create selection multiplicity. In addition to requested95%CIs, decision tests use conservative **98.333333%CIs** (two-sided alpha0.05/3), fixed for all3budgets including unmatched ones. Both endpoint conditions must hold at one eligible point (intersection-union); a favorable95% interval at one of many points is not enough. Secondary metrics/subgroups do not create extra confirmatory claims. Correlated or duplicate pairs do not reduce the family size.

## Fixed GO / NO-GO gate

Continue studying the **current confirmation mechanism** only if at least one predeclared eligible matched budget meets **all**:

1. Recall difference95% lower bound **and** multiplicity-adjusted lower bound are strictly above−0.01 (−1percentage point).
2. Fault-induced false point-count reduction is at least5% relative to GateOnly;95% **and adjusted** relative-difference upper bounds are strictly below0. A zero Gate count is insufficient evidence, not a perfect reduction.
3. The benefit is not solely a seed,scenario or fault-kind artifact: leaving out each single test seed, each single45scenario, and each of eight fault-kind/clean classes must retain a strictly negative aggregate fault-induced count difference (with positive Gate denominator) and Recall point difference>=−0.01. These are predetermined robustness direction checks, not another tuning loop; worst deletions are reported.
4. Samples/uploads meet final1% rules and all latency/diagnostic/byte costs and subgroup harms are disclosed. No unmeasured-energy claim. Increased delay is not hidden; no additional delay threshold is invented without application justification.

If no point clears every gate: **NO-GO**. Do not add complexity or tune the current confirmation rules again on these data. Keep GateOnly as the simpler competitor and record that confirmation's sufficient independent value was not established within this generator/test range. NO-GO is not a universal impossibility proof. A new mechanism would require a separate task, seed audit and protocol.

## Implementation and execution locks

Only new experiment/audit/analysis/test/config/report files and `results/budget-matched/` are written. Raw new traces use an exclusive `results/traces/budget-matched/` subtree, never old paths. Pin/hash all existing files and submodules against the base; record raw/ignored historical inventory signatures. Preserve v1/v2 protocol outputs and original config/CSV/manifest. No external real data are modified.

Software checks use old seed20 fixtures and synthetic numeric selection/statistics fixtures before new final testing. Freeze runner/analyzer/plan code before calibration; commit the selected lock before the single final run. Generate all final reports using the frozen rules; corrections to reporting errors must be disclosed, never used to rerun/select a better policy. Record actual commands,environment/source fingerprints,artifact hashes, failures and CI status. Network push failure must be reported honestly; no fake branch/commit links.
