# v0.2 interpretation after the frozen final run

**The improvement is narrow and conditional.** On new seeds50–99, multiplier.75 raises actual same-channel overlap recall140/600→146/600 (23.33%→24.33%, +1.00 pp; paired descriptive95% CI[+0.33,+1.83] pp). At multipliers1 and1.5 the same-channel difference is0, CI[0,0] on this fixed sample. Equality on these seeds is not a general equivalence/non-inferiority guarantee. All points were declared before final testing; no favorable point is promoted to a newly selected default.

## What the gain actually is

All six gains are `drift_same_long`, seeds50,64,71,74,75,89. Reports occur169–174 s after truth onset, close to the end of176 s truth intervals. Seed50 illustrates the mechanism: raw scoring starts a false drift-driven episode625 before physical truth634–810. At795 C DRIFT yields DEGRADED. Legacy confirmation compares against the previous sampled value already inside the excursion and cannot preserve the candidate. V02 freezes pre-update EMA32.478, samples795/800/805, retains positive displacement and confirms805. Passive waits too long and loses persistence after the event. This is late event retention, not timely event-onset detection or separation of physical causes.

The same V02 fault-only/no-event probe reports830 rather than805. All six gained onsets differ by more than5 s from their paired fault-only runs; this distinguishes them from the observation-identical range matches. This post-final diagnostic is explanatory, not a new primary metric or selection rule. Every changed event against legacy and passive is exported in [changed_events.csv](../results/v0.2/cases/changed_events.csv); representative gain/loss plots and full JSON are retained.

## Benefit and cost, all declared points

| Multiplier | Same recall v0.1→V02 | Same recall difference95% CI (pp) | Overall TP v0.1→V02 /1500 | Additional samples, all cases | Additional uploads | Additional bytes | Change in fault false reports |
|---|---|---|---|---|---|---|---|
|.75|23.33→24.33%|[+.33,+1.83]|707→711|7,795 (+5.99%)|480 (+.61%)|128,539 (+.60%)|-75|
|1|27.67→27.67%|[0,0]|707→705|7,206 (+5.74%)|270 (+.34%)|71,890 (+.34%)|-41|
|1.5|25.50→25.50%|[0,0]|353→353|2,161 (+1.82%)|181 (+.23%)|48,262 (+.23%)|+23|

At.75 within the same-channel group alone, the six gains cost2,137 samples (+6.57%),496 requests (+2.38%) and133,495 bytes (+2.39%); fault false295→263. Per-seed batch increments: samples42.74, CI[37.90,47.46]; requests9.92, CI[8.48,11.18]. Across all scenarios the recall difference vs v0.1 is only+.267 pp, CI[-.133,+.667] pp: the six gains coexist with two sequential-case losses. The.75 same-channel result remains below v0.1 at its original multiplier1 (27.67%), which uses fewer same-channel samples/uploads and has fewer fault false reports. The conditional matched-point improvement is not evidence of a new universally preferable operating point.

At original multiplier1, overall recall47.00% vs v0.1 47.13% (difference-.133 pp, CI[-.400,0] pp). The same-channel group costs an additional1,770 samples and407 requests for no TP gain. Overall count differences per seed batch of45 scenarios: samples+144.12/seed, CI[137.8775,149.92]; requests+5.4, CI[3.6195,7.2205]; fault false-.82, CI[-1.18,-.44].

## Independent confirmation ablation

At.75, full V02 versus passive gains6 same-channel events (+1 pp, CI[+.33,+1.83]) and one sequential cross event:7 overall (+.467 pp, CI[+.200,+.800]). It costs5,817 extra samples,705 requests and113 additional fault false reports. At multiplier1, full gains just one sequential cross event (+.067 pp overall, CI[0,+.200]), with5,673 samples,705 requests and107 extra fault false reports; same-channel TP is unchanged. At1.5, recall is unchanged with2,788 extra samples,525 requests and107 additional fault false reports. Confirmation therefore has an observable narrow benefit at.75, **not a consistent benefit across points/scenarios**, and the cost/false-report tradeoff must accompany it.

## Other scenarios and known failure

Cross-channel actual-overlap recall is unchanged against v0.1 at every point (at1:377/600=62.83% for both). Clean recall is unchanged (55/100 at1) and costs at original thresholds are identical across the gated policies. Shared scheduling still cannot guarantee an event between samples. SensorTrust's valid-offset blind spot and sparse STUCK detection remain unresolved.

New seed91 sequential spike cases lose an event at.75 and1 for both short and long profiles. The trace shows PENDING600, returned-spike cancellation605 and BLOCKED thereafter. The next real healthy event is sampled665/670/675; raw debounce is true675, but BLOCKED requires a low-score sample before rearm and suppresses the event. Legacy clears its block on healthy recovery and reports it. The v0.2 block was an explicit design choice; **it is now a demonstrated failure**, not silently corrected after opening final data. A strict expected-failure regression preserves this limitation. Future correction needs new independent seeds;50–99 are now used.

The final local suite is **125 passed,1 known expected failure (xfail),0 unexpected failures**. The original125-test implementation suite and corrected/freeze CI pass; the added post-final regression documents the newly observed blocked-rearm failure rather than certifying that all healthy events survive. Initial CI124-pass/1-failure portability evidence remains retained.

## Unidentifiability, metrics and external validity

At multiplier1, new same-additive cases give AS/v0.1/V02 each166/200; erased cases give AS28/400 and both gated methods0/400. These AS temporal matches remain an information-erasure caveat, not evidence of recovering the latent event. Historical v0.1 numbers were not altered or removed.

Persistent episode continuity changes onset counts: fewer unmatched onsets do not necessarily mean less falsely active time, which is not a primary measured metric here. C health is heuristic, not a fault probability. Reconstruction remains naive causal hold of finite raw readings, with no fault repair. Payload bytes count actual application JSON and health metadata; they are not RF energy. Joint profiles, sequential spikes, two channels/one faulty channel and a fixed synthetic scenario suite limit generalization. All type/profile/relationship metrics and conditional delays are retained in the report tables.

The greenhouse raw file was not acquired; old403 evidence remains, and real greenhouse validation is still incomplete. No field, firmware, physical energy or broad superiority claim is supported. The defensible result is a verified reproducible prototype with a small late-event benefit at one predeclared point, additional costs and a clearly traced recovery-block failure.
