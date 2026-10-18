# Figure index

All eight figures are read-only redraws at evidence snapshot `f21bc2f`, except Figures1–2 explicitly labeled schematics. No signal was regenerated, no parameter fitted, no confidence interval invented. PNG300dpi and editable-text SVG share identical content, white backgrounds, and line/marker/hatch distinctions beyond color. Vector fonts use the renderer's available DejaVu Sans; SVG viewers may substitute a font.

Generate from the repository root:

```bash
.venv/bin/python docs/research-portfolio/build_figures.py
```

This writes only this portfolio's figures, selected-result JSON and source fingerprints. It does not overwrite any historical figure or result. Paths below are repository-relative; exact input SHA-256 values are in [SOURCE_MANIFEST.json](SOURCE_MANIFEST.json). Paired intervals belong to comparisons, not independent bar errors; graphs use archived point estimates and reports quote the paired CSVs.

| Figure / outputs | Source and fields | Fixed selection and interpretation |
| --- | --- | --- |
| 1 [SVG](figures/fig01_research_framework.svg) / [PNG](figures/fig01_research_framework.png) | `src/tais/{scheduler,replay,metrics}.py`; `src/tais_spatial/methods.py` | Implemented workflow schematic; separate syntheticTAIS and offlineOSP paths. No live cloud/control platform implied |
| 2 [SVG](figures/fig02_algorithm_interfaces.svg) / [PNG](figures/fig02_algorithm_interfaces.png) | `src/tais/trust.py`, `trust_bridge.c`, `scheduler.py`; v02/rearm evidence | Interface schematic: separate health/change quantities, per-channel arbitration, optional version-specific lifecycle. Health is not probability |
| 3 [SVG](figures/fig03_v01_recall_fault_reports.svg) / [PNG](figures/fig03_v01_recall_fault_reports.png) | `results/test/summary.csv`:method,multiplier,tp,n_events,recall,fault_induced_false | P1 test20–49, multiplier1, AS/GateOnly/TAIS,900events/method. Counts not natural-fault accuracy; point estimates, CI source in P1 |
| 4 [SVG](figures/fig04_v01_event_strata.svg) / [PNG](figures/fig04_v01_event_strata.png) | `results/test/by_relationship.csv`:relationship,tp,n_events,recall | Same P1 point; clean60/same360/cross360labels. Sequential cases separate. Same-channel gap includes information-erased coincidental AS matches |
| 5 [SVG](figures/fig05_stable_offset_failure.svg) / [PNG](figures/fig05_stable_offset_failure.png) | `results/v0.2/forensics/stable_offset_none_long-TAIS.json.gz`:trace.latent/observed/events/faults;result.records.values/health/scores/state;result.reports | Prior documented seed20failure; no event truth interval because noeventexists. Shadefault572–1172s, reports610/1205s. Full signal shown only offline; circlemarkersactualsamples; C remainsHEALTHY |
| 6 [SVG](figures/fig06_blocked_rearm.svg) / [PNG](figures/fig06_blocked_rearm.png) | `results/blocked-rearm/diagnosis/{V02,V02-Rearm}.json.gz`, `{before,after}-samples.csv`:t,channel,raw_score,phase,health_state,value;result.reports | Prior knownseed91spike_same_long,multiplier1; display580–905s; dashedvertical605sreset, repairedreport675s. Symlogscoreabove10; allpointsretained. Greenphysicaltruth662–838s/redspike600–601s. Notindependent60-labelstatisticalevidence |
| 7 [SVG](figures/fig07_osp_coverage.svg) / [PNG](figures/fig07_osp_coverage.png) | `results/offline-spatial-pilot/{development,validation,test}/gate.json`:mean_target_coverage,mean_reference_quorum_coverage | P4primaryalignment/allnodes/variables/untouched;6/5/9dates.50%gateexplicit; held-outNO-GO, not an effectiveness bar |
| 8 [SVG](figures/fig08_spatial_information_cost.svg) / [PNG](figures/fig08_spatial_information_cost.png) | `results/offline-spatial-pilot/validation/summary.csv`:drift_added_reports,incremental_recall,mean_application_bytes,variable,case,method | Validationonly0s/900s/multiplier1;135requestednode-days/variable. DriftT/RH, localfast/slowT, bytesTlocalfast(logaxis). Real-referencecostcharged; no independentfinalsuccessclaim; humidityslowharmquotedinthetext |

Figures5–6 are specified historical probes from existing failure documents, not selected by a new “best-looking” search. Latent traces and truth shading are evaluator-only annotations; they do not imply the scheduling code read them. Reference offsets/age sensitivity and all original points remain in the historical CSVs linked by [provenance](RESULTS_PROVENANCE.md).

JA FigureA/B are localized references to full Figure2/7 respectively; the English report uses Figure1–8 throughout. Their captions preserve the same evidence conditions. No plotted control transition is treated as complete natural-event truth.
