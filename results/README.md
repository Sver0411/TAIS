# Results and evidence map

Start with the [current paper summary / 中文](../docs/TAIS_PAPER_SUMMARY_ZH.md) or the [document index](../docs/README.md). This is one results entry point for distinct studies, not a pooled benchmark. A report's recorded test count, branch or maturity rating belongs to its date/cohort, not the live repository. All old failures, logs, result paths and raw-evidence pointers remain intact.

## Current paper and runnable system

| Namespace | What it contains | Interpretation and authoritative entry |
| --- | --- | --- |
| [tais-core/](tais-core/README.md) | Actual local input/sample/TX/RX acceptance journals and byte/receiver audits | Software integration, not new effectiveness evidence; [Core contract](../docs/TAIS_CORE_PROTOTYPE.md) |
| [tais-su/](tais-su/README.md) | SU-1 engineering/development/validation/test; final 570–599, seven methods | All cap 20/30/40 points retained; GateOnly default, balanced replacement NO-GO; [protocol](../docs/TAIS_SU_PROTOCOL.md), [report](../docs/TAIS_SU_RESULTS.md) |
| [tais-paper/](tais-paper) | G1 independent schedules, native/common views, development selection and held-out 610–629 | 73,800 scored runs include 53 native versions and 29 common views, not 82 independent algorithms; [protocol](../docs/TAIS_PAPER_PROTOCOL.md), [evidence](../docs/TAIS_PAPER_EVIDENCE.md) |
| [tais-transfer/](tais-transfer/README.md) | Frozen G2 policies, final 700–719, 46 scenarios,14 native systems | 12,880 scored runs without retuning; [protocol](../docs/TAIS_CROSS_GENERATOR_PROTOCOL.md), [report](../docs/TAIS_CROSS_GENERATOR_REPORT.md) |
| [tais-paper-review/](tais-paper-review/README.md) | Post-hoc budget qualification, current PDF/build provenance and regression logs | No new campaign; [major revision](../docs/TAIS_PAPER_REVISION_CHANGELOG.md), [current manuscript](../papers/tais/README.md) |

G1 and G2 change signal dynamics, faults, timing **and ground-truth interval definitions**. Report within-task comparisons separately. Do not add their counts into field-validation totals. The latest [quality review](../docs/TAIS_PAPER_QUALITY_REVIEW.md) limits the claims; earlier reports' stage ratings remain historical evidence.

### Useful files before raw logs

| Need | Direct artifact |
| --- | --- |
| G1 native/common overall and grouped P/R/F1, samples, bytes and FI | [G1 summary](tais-paper/test/analysis/summary.csv); filter `view`, `group` and method explicitly |
| G1 actual budget qualification | [G1 budget comparisons](tais-paper/test/analysis/budget_comparisons.csv) |
| G2 overall comparison | [G2 overall summary](tais-transfer/summary.csv) |
| G2 groups and descriptive paired uncertainty | [G2 grouped summary](tais-transfer/test/analysis/summary.csv), [paired intervals](tais-transfer/test/analysis/paired_intervals.csv) |
| G2 figures | [figure directory](tais-transfer/figures) and its manifest; no smoothed/interpolated superiority curve |
| 2/5/10% budget eligibility | [All 60 saved pairs](tais-paper-review/budget_sensitivity.csv), [focused table](tais-paper-review/budget_sensitivity_focus.md); thresholds change eligibility, not performance |
| Paper numeric source cells | [G1 audit](../papers/tais/tables/data_audit.csv), [G2 audit](../papers/tais/tables/transfer_data_audit.csv), [review audit](../papers/tais/tables/review_data_audit.csv) |
| Current PDF/render/build checks | [Revision evidence](tais-paper-review/README.md), [layout audit](../docs/TAIS_PAPER_LAYOUT_AUDIT.md) |

Use each campaign's manifest for its exact inputs, methods, seed ranges, source hashes and outputs. `metrics.csv` is per-run software evaluation; `events.csv`/`faults.csv`, where present, retain episode-level evidence. Grouped CSV rows, one-second source rows and method variants are not independent seed replicates.

## Other frozen studies and negative results

| Namespace | Scope | Result / report |
| --- | --- | --- |
| [tais-joint/](tais-joint/README.md) | JO H/S/U decomposition; final 520–549 | Full default replacement NO-GO; [JO report](../docs/TAIS_JO_RESULTS.md) |
| [wire-payload/](wire-payload/README.md) | Binary v1 encoding of historical v0.1 uploads | Serialization engineering evidence; [v1 report](../docs/WIRE_PAYLOAD_EXPERIMENT.md) |
| [wire-payload-v2/](wire-payload-v2/README.md) | Stateful health compression and controlled loss/recovery | Separate protocol, not Core default; [v2 report](../docs/WIRE_PAYLOAD_V2.md) |
| [budget-matched/](budget-matched/README.md) | BM-1 confirmation at declared sample/upload budget points | NO-GO; [protocol](../docs/BUDGET_MATCHED_EXPERIMENT_PREREGISTRATION.md), [report](../docs/BUDGET_MATCHED_EXPERIMENT_REPORT.md) |
| [fault-event-observability/](fault-event-observability/README.md) | FO-1 timing, attribution and identical-observation boundaries | Conditional benefits and harms; [protocol](../docs/FAULT_EVENT_OBSERVABILITY_PREREGISTRATION.md), [report](../docs/FAULT_EVENT_OBSERVABILITY_REPORT.md) |
| [independent-reference-budget/](independent-reference-budget/README.md) | Same-quantity reference under shared hard budgets | ReferenceGate main gates failed; [protocol](../docs/INDEPENDENT_REFERENCE_BUDGET_PREREGISTRATION.md), [report](../docs/INDEPENDENT_REFERENCE_BUDGET_REPORT.md) |
| [v0.2/](v0.2/README.md) | Separate persistent-candidate policy and forensics | Narrow gains and unresolved failures; [report](../docs/RESEARCH_REPORT_V0.2.md) |
| [blocked-rearm/](blocked-rearm/README.md) | Specific reference-return rearm repair | Repair does not solve event/fault overlap; [report](../docs/BLOCKED_REARM_REPORT.md) |
| [offline-spatial-pilot/](offline-spatial-pilot/README.md) | Real greenhouse background plus controlled offline interventions | Held-out coverage NO-GO; [protocol](../docs/OFFLINE_SPATIAL_PILOT_PROTOCOL.md), [report](../docs/OFFLINE_SPATIAL_PILOT_REPORT.md) |

The pilot is exploratory, uses an explicit assumed reception clock and is not an online natural-fault study. [greenhouse-access.json](greenhouse-access.json) records the **initial**403/download failure, not the latest intake status. [C0](../docs/REAL_DATA_INTAKE_AUDIT.md) subsequently obtained five original files outside Git; [C1](../docs/REAL_DATA_EXPERIMENT_PREREGISTRATION.md) still found unresolved time semantics for the proposed formal online experiment. No timestamp axis is repaired by this navigation work.

## Files and local-only evidence

| Kind | How to use it |
| --- | --- |
| Committed CSVs, figures and manifests | Small, reviewable outcomes; follow the corresponding report and configuration, rather than inferring methods from directory names |
| `checks/`, run/setup/CI logs, `SHA256SUMS` | Dated reproduction/audit evidence. Old test totals or PDF fingerprints are historical; a new codebase/PDF needs its own current checks |
| `traces/` | Ignored canonical gzip input, truth, sampled decisions and per-frame archives, grouped by study/split/seed/scenario; complete archives may be large and absent from a clone |
| `scratch/` | Ignored fresh demos, clean-install checks and reproduction replicas; paths in examples must be new |
| External raw workbooks / provenance ledgers | Not shipped in Git. Consult C0/OSP records for source, hashes, license and clock assumptions; no raw download is needed for the Core demo |

Some historical manifests contain absolute original archive roots. A recorded hash is a pointer to evidence, not a guarantee that the file exists on another computer. Use a documented fresh replica or supported root override; do not silently rewrite old manifests to point at invented inputs. Small explicitly committed Core acceptance journals are exceptions to the general local-only raw-log convention.

The original [SHA256SUMS](SHA256SUMS) also pins the **old version of this index**. Its 72 other entries still match; checking it against this navigation revision reports one expected mismatch for `results/README.md` only. The manifest is deliberately unchanged. To check the old index itself, `git show 94a80a1:results/README.md | shasum -a 256` produces its recorded `6a74973e…` hash. Use the study-specific checks below for current source/result verification; do not replace a frozen checksum merely to make an edited navigation document match.

## Safe checks and reproduction

From the repository root after [installation](../docs/QUICKSTART.md):

```sh
python scripts/check_paper_artifacts.py
python scripts/verify_paper_revision.py
python scripts/verify_paper.py
python scripts/verify_transfer.py
```

These do not reselect operating points or run a full campaign. G1/G2 optional archive validation is separate and can require local-only inputs. The [script index](../scripts/README.md) distinguishes default summary checks from writers that regenerate analyses or create exclusive historical audit records.

For a minimal fresh end-to-end reproduction use the [Core demo](../docs/QUICKSTART.md#minimal-end-to-end-run). For a small benchmark smoke use the [scratch-root example](../scripts/README.md#experiment-runners). Full paper replicas are intentionally **not** part of setup: `reproduce_paper.py --output NEW_PATH` runs the entire frozen G1 final matrix; `reproduce_transfer.py` runs the entire frozen G2 matrix in new scratch paths. They can produce substantial storage and runtime costs. Follow the [paper build/reproduction guide](../papers/tais/README.md) and study records before starting them.

## Original v0.1 evidence

The original index's findings remain specific to v0.1 and are preserved here for interpretation; its underlying files have not been moved or regenerated.

- [Baseline manifest](baseline/manifest.json): original actual AdaptiveSense reproduction passed 235 Python tests and 69 config checks; SensorTrust passed 27 Python tests and 21 standalone C tests/404 checks. Both regenerated AdaptiveSense metric CSVs matched the pinned originals byte-for-byte. Commands/environment/compiler/hashes remain recorded. `reproduce_baseline.py` writes this fixed directory, so it is not a harmless inspection command.
- [Initial prototype failure](prototype-tests-initial.log), [later prototype log](prototype-tests.log), setup and CI logs retain the failures/corrections described in [validation history](../docs/VALIDATION_HISTORY.md). The old 67-passed count is a historical suite size, not today's total.
- [development-smoke/](development-smoke): original 39-run engineering/CI smoke, not research evidence; the earlier pre-fix run remains in Git history.
- [development/](development), [validation/](validation), [test/](test):5,850/5,850/17,550 scored runs,29,250 total. Per-run metrics, micro/scenario/relationship summaries,2000-replicate seed-paired bootstrap CIs, actual-budget comparisons and plots remain at their original paths. The recorded verification covered 31,500 archive hashes and three deterministic replays.
- At original thresholds, final TAIS/AdaptiveSense Recall was 51.56%/51.56%, operational fault-induced reports 458/652, samples 76,430/101,108 and application requests 47,694/49,816. Actual same-channel-overlap Recall fell 35.28%→30.28%; health fields increased payloads versus plain AdaptiveSense. These numbers do not describe the later SU/G1/G2 cohorts. [Original report](../docs/RESEARCH_REPORT.md), [protocol](../docs/EXPERIMENT_PROTOCOL.md).

Undefined no-event Recall and unmatched conditional delays stay N/A, not zero. Fault-induced counts use study-specific operational windows/counterfactuals rather than proof of physical causality. Local detections, upload requests and decoded receiver edges are distinct. Application bytes are not RF traffic, measured joules or battery life.
