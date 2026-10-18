# Results provenance and claim ledger

Evidence snapshot: `f21bc2f0e1d01d0670ce1c1bd4ab5a2aab7e171d`. This portfolio only reads existing results. Claim IDs below apply to both language reports. [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json) records SHA-256 for figure/quantitative inputs; [VERIFIED_RESULTS.json](VERIFIED_RESULTS.json) contains the actual selected CSV records. `build_figures.py` does not import a simulator or train a model. No stage totals are added to create an independent “grand experiment count.”

## P1 — v0.1 synthetic experiment

**Code and split.** Actual test manifest source `97aa5d50afeb2cbf97bc9d91562a01c71dfd98cf`; algorithm/config freeze `273758d`, with a subsequent source-script import fix. [Manifest](../../results/test/manifest.json), [configuration](../../configs/experiment.yaml), [original report](../RESEARCH_REPORT.md), [specification](../ALGORITHM_SPEC.md). Development0–9, validation10–19, historically independent test20–49. All these seeds are now used. Two channels, 1,800 s, 45 scenarios, 13 scored operating points; the test contains17,550 rows, not17,550 independent physical deployments.

**Primary sources.** [Summary](../../results/test/summary.csv), [relationship strata](../../results/test/by_relationship.csv), [paired intervals](../../results/test/paired_bootstrap.csv), [raw metrics](../../results/test/metrics.csv). Filter `multiplier == 1`, methods `AdaptiveSense`, `GateOnly`, `TAIS`. Figures3–4 and JA/EN default statements use this point, not an outcome-selected new default.

| Claim | Exact record/calculation | Interval / limitation |
| --- | --- | --- |
| Both recalls51.56% | AS and TAIS `tp=464`, `n_events=900`; 100×464/900 | Paired CSV: relationship=all, method=TAIS, metric=recall: [−0.0111111,+0.0122222] fractions. Equal aggregate is not non-inferiority |
| Fault-attributed652→458 | `fault_induced_false` in summary; (458−652)/652×100=−29.7546% | Operational attribution via fault-free counterfactual and ±5s matching, not physical-cause certainty |
| Strict unmatched990→828 | `false_reports` in summary | Distinct from fault attribution and redundant reports; counts are report onsets |
| Samples−24.41%; requests−4.26% | AS101108/49816, TAIS76430/47694 | Values are sampling cycles and application requests, not measured sensor power |
| Bytes+60.04% | AS8000401, TAIS12804006; 100×(12804006/8000401−1)=60.0421% | Actual compact application JSON includes health metadata; excludes radio overhead |
| Same-channel35.28→30.28% | relationship=same: AS127/360, TAIS109/360 | TAIS−AS −5.00pp [−7.7778,−2.2222] |
| Cross-channel64.17→68.33% | relationship=cross: AS231/360, TAIS246/360 | +4.1667pp [1.9444,6.6667] |
| Clean unchanged60% | relationship=clean:36/60 for AS/GateOnly/TAIS | Same/cross/clean bars do not partition sequential and event-free cases |
| Confirmation only3 extra matches | TAIS−GateOnly:464−461,76430−75964 samples,47694−47427 requests,458−440 attributed reports | Recall +0.3333pp [0,+0.8889]; these are total differences over30 seeds |

The pair bootstrap resamples whole seed batches2,000 times, RNG731. Count differences in paired CSV are mean **per seed batch** across the indicated scenarios; the summary totals above cover all30seeds. No added confidence interval is manufactured from marginal bars. The experimental gate here is source/config freeze and synthetic causal/label controls, not the later OSP coverage gate. It supports only the declared synthetic population.

**Interpretation correction, historical metric unchanged.** [Forensics](../FAILURE_ANALYSIS_V0.1.md) and [identifiability output](../../results/v0.2/forensics/identifiability.json) compare event/no-event streams. All18 additional AS same-channel matches are in observation-erasing range cases and also occur without the event. These are temporal matches, not evidence that the latent signal was recovered. The old aggregate table is not rewritten; portfolio prose must not call this “18 observable events lost.” Same-additive AS/TAIS109/120 and GateOnly108/120 are a different information stratum, not a replacement for the original metric.

## P2 — v0.2 controlled persistence experiment

**Code and split.** [Design](../V02_DESIGN.md) committed at `8222873`, implementation `1dbc102`, final test source `14af61952229a6da6cda40c8ee7257f9582b4b40`. [Manifest](../../results/v0.2/test/manifest.json), [config](../../configs/v02.yaml). Development0–9/validation10–19 retain earlier exposure;20–49 are diagnostics; final50–99 was new at this stage. Same45 synthetic scenarios,19 points,42,750 final scored rows. No parameter selection; all three inherited multipliers retained.

Sources: [summary](../../results/v0.2/test/summary.csv), [strata](../../results/v0.2/test/by_relationship.csv), [paired CSV](../../results/v0.2/test/paired_bootstrap.csv), [interpretation](../V02_INTERPRETATION.md), [changes and archived cases](../../results/v0.2/cases/README.md). Compare `V02` with `TAIS` **within this test split**, never compare its1500-label denominator directly with P1's900.

| Point | Same-channel overlap (TAIS→V02) | Overall (TAIS→V02) | Cost and adverse effect |
| --- | --- | --- | --- |
| 0.75 |140→146 /600; +1.00pp [0.3333,1.8333]|707→711 /1500; +0.2667pp [−0.1333,+0.6667]|+7795 samples,+480 requests,+128539bytes; fault-attributed−75 |
| 1 |166→166 /600;0[0,0]|707→705 /1500;−0.1333pp[−0.4,0]|+7206 samples,+270 requests,+71890bytes; attributed−41 |
| 1.5 |153→153 /600;0[0,0]|353→353 /1500|+2161 samples,+181requests,+48262bytes; attributed+23 |

For recall intervals select `group=relationship:same` or `all`, `reference=TAIS`, desired multiplier, `metric=recall`. Count totals are differences of matching summary rows; count-CI means remain per-seed batches, not totals. Whole-seed2,000bootstrap/RNG731 as specified in the original design.

All six same-channel gains at0.75 belong to `drift_same_long`, seeds50/64/71/74/75/89; reports169–174s after onset near the176s truth end. Source: [changed-events CSV](../../results/v0.2/cases/changed_events.csv) and original interpretation. They are not independent onset-detection success or natural fault diagnoses. Full-versus-passive overall seven extra matches at0.75 cost5817samples,705requests and113additional attributed reports; these numbers are differences of `V02` and `V02-Passive` summary rows.

**P2-F archived failure.** Figure5 uses only [stable_offset_none_long-TAIS.json.gz](../../results/v0.2/forensics/stable_offset_none_long-TAIS.json.gz): seed20, multiplier1, a previously documented diagnostic probe. Fields: `trace.latent/observed/faults/events`, `result.records` sampled time/value/health/score/state, and `result.reports`. There are no true environment events; reports610/1205s illustrate the in-range-offset blind spot. This old case is explanatory, not new independent v0.2 evidence. The forensic observer was committed after the original policy; its provenance is explicitly explained in the original forensics document.

## P3 — BLOCKED rearm state repair

**Code and split.** [Design](../BLOCKED_REARM_FIX.md), [interpretation](../BLOCKED_REARM_INTERPRETATION.md), [config](../../configs/blocked_rearm.yaml). Actual final source freeze `8a735930883cd1a2dc6e6a0f0860bc3d2f91440e` in [test manifest](../../results/blocked-rearm/test/manifest.json); dev100–109, validation110–119, final120–149. Those seeds were audited as unused before that study;0–149 must now all be treated as used. Main45 scenarios and aligned-recovery6 scenarios are separate suites, not independent samples of one natural distribution. Final19,890 scored rows across13 points and both suites.

Sources: [main summary](../../results/blocked-rearm/test/main/summary.csv), [main strata](../../results/blocked-rearm/test/main/by_relationship.csv), [main paired intervals](../../results/blocked-rearm/test/main/paired_bootstrap.csv), [aligned strata](../../results/blocked-rearm/test/aligned_recovery/by_relationship.csv), [aligned paired intervals](../../results/blocked-rearm/test/aligned_recovery/paired_bootstrap.csv). Compare `V02-Rearm` versus `V02`, multiplier1.

| Claim | Exact selector | Meaning / validity |
| --- | --- | --- |
| Main450→454 /900 | Main summary TP / n_events | +0.4444pp, `group=all, reference=V02, metric=recall`: CI[0,1.1111]pp; includes0 |
| Same overlap102→102 /360 | Main by_relationship relationship=same | No improved concurrent same-channel recall |
| Cross overlap243→243 /360 | Main relationship=cross | No changed cross overlap at this point |
| Recovery0→60 /60 | Aligned relationship=same_sequential | +100pp[100,100] on deliberately sampled-spike challenge; not main or natural prevalence |
| Default extra costs | Main0samples,+4requests,+1068bytes; aligned0,+57,+15256 | Totals over30seeds in each separate suite |
| High-multiplier risk | Main1.5:0extraTP,+6attributed/+6strictfalse,+128samples,+39requests,+10499bytes | Keep adverse point; do not call repair general dominance |

Main repaired default reaches the same454 matches as v0.1 TAIS on120–149, while adding4282samples/159requests and removing29attributed/35strictfalse reports; those differences come from main summary rows, not from P1. Bootstrap settings unchanged2,000/RNG731. Tests and code establish synchronization; matching results establish only the declared conditional effect.

**P3-F known regression.** Figure6 reads [V02 JSON](../../results/blocked-rearm/diagnosis/V02.json.gz), [Rearm JSON](../../results/blocked-rearm/diagnosis/V02-Rearm.json.gz), [before sampled CSV](../../results/blocked-rearm/diagnosis/before-samples.csv), [after sampled CSV](../../results/blocked-rearm/diagnosis/after-samples.csv). Seed91 is used diagnostic data, not a new test. Filter temperature, methodV02/V02-Rearm. At600PENDING,605cancellation; new event truth662–838; fixed report675. It is one saved `spike_same_long` trace, not the complete60-label recovery result.

## P4 — OSP-1 semi-synthetic offline pilot

**Source and freeze.** Real Greenhouse-1.xlsx, Zenodo5793685/v1.0, CC BY4.0; SHA `9b5f48b5f37ebc90052658649de7471b298da7dd4581bf47d0d8ec404cadff19`. [Protocol](../OFFLINE_SPATIAL_PILOT_PROTOCOL.md) `6feafb2`; independent code `ba46b81`; [freeze](../../results/offline-spatial-pilot/freeze.json) and development/validation outputs committed at `f2fcbbb` before final opening; final evidence snapshot `f21bc2f`. [Config](../../configs/offline_spatial_pilot.json), [report](../OFFLINE_SPATIAL_PILOT_REPORT.md), [source quality](../../results/offline-spatial-pilot/source-quality.json), [full reproduction](../../results/offline-spatial-pilot/README.md).

CalibrationApr18–25; developmentApr26–Jun1, validationJun2–Jul1, held-outJul2–Sep1,2020 proxy dates, intervals left-closed/right-open. One weekly04:00–20:00episode;2hwarmup;10minpoll; all27nodes/two quantities; one-day partition guards. Six/five/nine dates, not independent sites. Negative-control/bootstrap seeds2026101801/2026101802; not synthetic test seeds0–149. No future reference on the assumed availability axis; −10min offset is a hypothesis, not evidence of actual timely reception.

| Claim | Source and selector | Calculation / gate |
| --- | --- | --- |
| Target coverage80.47/76.38/25.89% | Per-split `gate.json`, key `mean_target_coverage` | Main alignment0s/900s, multiplier1, untouched, Spatial, allnodes/variables |
| Reference quorum83.34/84.59/24.12% | `mean_reference_quorum_coverage` in same gates | At least2usable geometric references; not overall original file completeness |
| Held-outNO-GO | [test gate](../../results/offline-spatial-pilot/test/gate.json) and [failure declaration](../../results/offline-spatial-pilot/TEST_NO_GO.md) | Both<50%,9dates≥4; output remains failure audit only |
| Validation humidity added1.140741 vs1.118519 | [validation summary](../../results/offline-spatial-pilot/validation/summary.csv), case=drift, humidity, Spatial/NullSpatial, shift0, age900, multiplier1 | Mean added onsets per requested node-day, not natural false rate |
| Validation slow-local humidity51→46 /135 | case=local_slow, HistoryExtended/Spatial | Difference−0.037037; paired CSV metric=event_incremental_hit, comparatorHistoryExtended: CI[−0.074074,−0.007407] |
| Reference388requests/13968bytes | summary reference_requests/reference_payload_bytes |4slots×97polls×36bytes; same Spatial/Null budget, assumed application frames |
| Validation T local-fast bytes | methodSpatial14008.6667, HistoryExtended35.0667, Null14005.3333 | Per requested node-day, includesenvironmentreports; not radio energy |
| 617760metricrows | manifests185328+154440+277992 | Dependent method/point/scenario/node/date combinations; not independent trials |

Figure8 uses only the validation main point; it is chosen as the named validation point, not promoted as final validation. All primary multipliers and timing assumptions remain available in [operating points](../../results/offline-spatial-pilot/audit/all-primary-operating-points.csv) and [timing assumptions](../../results/offline-spatial-pilot/audit/all-timing-assumptions.csv). CI source: [validation paired-differences](../../results/offline-spatial-pilot/validation/paired-differences.csv), date-cluster10,000bootstrap; small date count and no multiplicity correction limit inference. Development temperature drift differences across9assumptions change sign; reference-age sensitivity is not omitted.

“Drift added” means unmatched report onsets in controlled copies relative to the paired unaltered background using±10min one-to-one matching; net added-minus-removed is distinct. Incremental event recall requires a new report relative to the no-event counterpart within90min, not just any background report in the window. No independent natural-event/fault labels exist, so strict natural metrics are N/A. Held-out effects were computed before gate evaluation and are retained as diagnostics, not silently discarded or used to tune a new split.

## Implementation evidence is not effectiveness evidence

The existing OSP source snapshot records215passed/2legacystrictxfails and a successful [CI run](https://github.com/Sver0411/TAIS/actions/runs/39097996830); this portfolio does not relabel that as a new test execution. The earlier milestones record different suite sizes. C11 parity, causal-prefix, interval-bound and deterministic-output tests support implementation claims only. They do not establish greenhouse deployment validity. This documentation stage runs source-hash, number, figure, link, PDF-layout and scope checks; no parameter search or large-effect rerun.
