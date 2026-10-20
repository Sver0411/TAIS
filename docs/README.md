# Documentation map

New reader: [project home](../README.md) → [Quick start](QUICKSTART.md) → [Core interface](TAIS_CORE_PROTOTYPE.md) → [current paper summary / 中文](TAIS_PAPER_SUMMARY_ZH.md). Use the [source map](REPOSITORY_GUIDE.md), [script index](../scripts/README.md) and [result index](../results/README.md) for implementation and reproduction.

**Status key:** **Current** = current interface or interpretation; **Frozen** = completed, version-specific evidence/protocol; **Exploratory** = limited or reused-data investigation; **Historical** = an earlier design/report; **Blocked / NO-GO** = the stated evidence gate failed or formal work could not start. A frozen study can have a negative decision. Neither a document's filename nor a branch name implies it is the current default.

## Getting started and system use

| Read | Purpose | Status |
| --- | --- | --- |
| [Quick start](QUICKSTART.md) | Install, run and inspect fresh Gate/SU demos; distinguish CLI presets from SU40 API | Current |
| [Repository and source map](REPOSITORY_GUIDE.md) | Find source, tests, CI and authoritative versions without scanning every file | Current |
| [Detailed Core commands](../examples/tais-core/README.md) | Input units/time, JSONL, independent receiver and controlled link examples; SU choices are clarified in Quick start | Current interface |
| [Contributing](../CONTRIBUTING.md) | Preserve evidence, use fresh paths and check an appropriate scope | Current |

## Architecture and algorithm design

| Read | Purpose / prerequisite | Status |
| --- | --- | --- |
| [Core system](TAIS_CORE_PROTOTYPE.md) | Actual due-time sender → Binary v1 → receiver; start after Quick start | Current default interface; frozen acceptance evidence |
| [Original executable specification](ALGORITHM_SPEC.md) | Per-channel scheduler, scores, thresholds and original confirmation behavior; not a universal description of every later mode | Historical v0.1 contract |
| [Implementation audit](IMPLEMENTATION_DECISIONS.md) | Reuse/attribution and original engineering decisions | Historical |
| [JO protocol](TAIS_JO_PROTOCOL.md) and [results](TAIS_JO_RESULTS.md) | H/S/U decomposition; full replacement failed, H costs remain visible | Frozen / NO-GO for default replacement |
| [SU protocol](TAIS_SU_PROTOCOL.md) and [results](TAIS_SU_RESULTS.md) | Frozen JO-S+U, Gate+U and cap20/30/40; balanced replacement failed | Frozen; Current supported options |

## Core interfaces and payloads

| Read | Purpose / result entry | Status |
| --- | --- | --- |
| [Stateless Binary v1](WIRE_PAYLOAD_EXPERIMENT.md) | Complete field-preserving serialization; [wire results](../results/wire-payload/README.md) | Frozen engineering study; Current Core codec |
| [Stateful Wire v2](WIRE_PAYLOAD_V2.md) | Health delta/keyframes and loss/recovery costs; [v2 results](../results/wire-payload-v2/README.md) | Frozen separate experiment; not Core default |
| [Core evidence](../results/tais-core/README.md) | Actual journals, byte/receiver acceptance and preserved failures | Frozen software evidence |

## Protocols and main results

| Read | Purpose / cohort | Status |
| --- | --- | --- |
| [Research question](RESEARCH_QUESTION.md) and [original protocol](EXPERIMENT_PROTOCOL.md) | Original hypothesis, truth and metric definitions; definitions are study-specific | Historical / Frozen v0.1 |
| [Original report](RESEARCH_REPORT.md) | v0.1 results and ablations; [original evidence](../results/README.md#original-v01-evidence) | Frozen, not current test status |
| [JO results](TAIS_JO_RESULTS.md) → [JO evidence](../results/tais-joint/README.md) | Seeds520–549, full H/S/U costs and failures | Frozen |
| [SU results](TAIS_SU_RESULTS.md) → [SU evidence](../results/tais-su/README.md) | Seeds570–599, seven methods, all caps and receiver-edge diagnostics | Frozen |
| [Resource cost model](TAIS_RESOURCE_COST_MODEL.md) | Conditional sensitivity on software counts; no measured joules/battery life | Exploratory model |

## Independent baselines and cross-task evaluation

| Read | Purpose / result entry | Status |
| --- | --- | --- |
| [Paper protocol](TAIS_PAPER_PROTOCOL.md) | G1 development selection, native/common views and independent controls | Frozen |
| [Paper evidence](TAIS_PAPER_EVIDENCE.md) | Full G1/G2 tables and provenance; read its revision notice before older stage ratings | Frozen results with revision pointer |
| [G2 protocol](TAIS_CROSS_GENERATOR_PROTOCOL.md) and [report](TAIS_CROSS_GENERATOR_REPORT.md) | Zero-retuning second synthetic task; [G2 results](../results/tais-transfer/README.md) | Frozen; final wording in paper revision |
| [Current Chinese interpretation](TAIS_PAPER_SUMMARY_ZH.md) | G1/G2 truth differences, CI crossing zero, Fixed20/Variance and shared U | Current |
| [Budget sensitivity](../results/tais-paper-review/budget_sensitivity.csv) | All60 saved control-target pairs at2/5/10%; no point reselection | Current post-hoc analysis |

G1 and G2 are project-defined synthetic tasks with different truth windows as well as different dynamics/faults/timing. They are not two field populations, and their totals must not be pooled. Delta/Variance are original engineering controls; Rao-inspired is an explicitly incomplete literature adaptation. The common-detector view compares schedules and is not an independent full-system comparison.

## Real-data intake and offline spatial exploration

| Read | Purpose / result entry | Status |
| --- | --- | --- |
| [Initial data-access note](../data/README.md) → [C0 intake audit](REAL_DATA_INTAKE_AUDIT.md) | The initial403 is historical; C0 later obtained five files outside Git and audited their semantics | Historical access failure → Frozen intake |
| [C1 time-semantics draft](REAL_DATA_EXPERIMENT_PREREGISTRATION.md) | Unresolved availability clocks prevent the proposed formal online experiment; not a completed preregistration | Blocked / NO-GO |
| [C1.1 dataset selection](C1_1_DATASET_SELECTION.md) | Conditional candidate assessment; not effectiveness evidence | Historical feasibility decision |
| [Offline pilot protocol](OFFLINE_SPATIAL_PILOT_PROTOCOL.md) and [report](OFFLINE_SPATIAL_PILOT_REPORT.md) | Real-background controlled interventions under explicit proxy-clock assumptions; [pilot evidence](../results/offline-spatial-pilot/README.md) | Exploratory / held-out coverage NO-GO |

The offline pilot does not repair C1's formal online validity gap. It is not natural-fault ground truth, an online LoRaWAN system or qualified held-out effectiveness evidence.

## Paper and review

| Read | Purpose | Status |
| --- | --- | --- |
| [Manuscript and build guide](../papers/tais/README.md) | Current17-page [PDF](../papers/tais/manuscript.pdf), [LaTeX](../papers/tais/manuscript.tex), tables and figures | Current major revision |
| [中文概要](TAIS_PAPER_SUMMARY_ZH.md) | Research question, three systems contributions, adverse results and limits | Current |
| [Novelty and related work](PAPER_NOVELTY_AND_RELATED_WORK.md) | Verified literature scope and known-technology attribution; old [related work](RELATED_WORK.md) is background | Current synthesis |
| [Revision changelog](TAIS_PAPER_REVISION_CHANGELOG.md) | Exact wording changes and reviewer responses | Current |
| [Quality review](TAIS_PAPER_QUALITY_REVIEW.md) and [layout audit](TAIS_PAPER_LAYOUT_AUDIT.md) | Narrow A rating and actual rendered-PDF findings; not peer review or acceptance | Current |
| [Submission checklist](TAIS_SUBMISSION_CHECKLIST.md) | Real authors, human review, venue/template and AI-use requirements still to confirm | Current preparation checklist |
| [Paper-revision evidence](../results/tais-paper-review/README.md) | PDF/build fingerprints, numeric bindings, read-only sensitivity and actual check logs | Frozen revision evidence |

## History and negative results

Read these to understand boundaries, not to enable every past mechanism. No failure report or evidence directory has been removed.

| Read | What it explains | Status |
| --- | --- | --- |
| [v0.1 failure analysis](FAILURE_ANALYSIS_V0.1.md) | Drift, same-channel masking and missed events behind later research | Historical analysis |
| [v0.2 design](V02_DESIGN.md), [report](RESEARCH_REPORT_V0.2.md), [interpretation](V02_INTERPRETATION.md), [reproduction](V02_REPRODUCIBILITY.md) | Persistent candidate study, narrow conditional gains and unresolved latch failure; [results](../results/v0.2/README.md) | Frozen separate policy |
| [Rearm repair](BLOCKED_REARM_FIX.md), [interpretation](BLOCKED_REARM_INTERPRETATION.md), [report](BLOCKED_REARM_REPORT.md), [reproduction](BLOCKED_REARM_REPRODUCIBILITY.md) | Specific reference-return cancellation repair, not recovery of erased events; [results](../results/blocked-rearm/README.md) | Frozen separate policy |
| [BM-1 protocol](BUDGET_MATCHED_EXPERIMENT_PREREGISTRATION.md) and [report](BUDGET_MATCHED_EXPERIMENT_REPORT.md) | Matched-budget confirmation did not clear its value gate; [results](../results/budget-matched/README.md) | Frozen / NO-GO |
| [FO-1 protocol](FAULT_EVENT_OBSERVABILITY_PREREGISTRATION.md) and [report](FAULT_EVENT_OBSERVABILITY_REPORT.md) | Timing-dependent benefits/harms and identical-input ambiguity; [results](../results/fault-event-observability/README.md) | Frozen boundary study |
| [ReferenceGate protocol](INDEPENDENT_REFERENCE_BUDGET_PREREGISTRATION.md) and [report](INDEPENDENT_REFERENCE_BUDGET_REPORT.md) | Same-quantity reference under shared budgets failed nine main comparison gates; [results](../results/independent-reference-budget/README.md) | Frozen / NO-GO |
| [Research decision](NEXT_RESEARCH_DECISION.md), [limitations](LIMITATIONS.md), [validation history](VALIDATION_HISTORY.md) | Earlier reasoning, known boundaries and retained engineering failures; counts refer to their recorded dates | Historical |

Pretest reviews, forensic artifacts and file inventories remain alongside these reports and are linked from their study-specific documents. The indices prioritize reading order rather than listing every Markdown file.
