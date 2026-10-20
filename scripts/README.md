# Script navigation

Run commands from the repository root in the [installed environment](../docs/QUICKSTART.md). This index is based on the scripts' entry points, not their names alone. **Read-only checks**, **writers** and **full campaigns** have different effects. Keep frozen destinations intact and use fresh ignored scratch paths where the CLI supports them. No full campaign is needed to try TAIS or read its results.

## Daily runs and demonstrations

The daily entry points live in `examples/`, rather than duplicating the interface here.

| Entry | Arguments / input | Output and scope |
| --- | --- | --- |
| [run.py](../examples/tais-core/run.py) | `--scenario`/`--csv`/`--stdin`, `--policy`, `--pace`, `--ui`, required `--out`; synthetic `--verify` | New run directory, actual byte/receiver journal and summary; [mode guide](../docs/QUICKSTART.md#mode-selection) |
| [view_run.py](../examples/tais-core/view_run.py) | Run directory, `--tail N` | Read-only display of received history; no detector replay |
| [receiver.py](../examples/tais-core/receiver.py) | Hex lines on stdin, required `--out`, optional `--layout` | New received-frame journal; standalone local consumer, no network server |
| [historical_review.py](../examples/tais-core/historical_review.py) | Required `--archive`, `--out` | **Local BM-1 archive required**; reads/encodes old runs into new review output, not fresh effectiveness evidence |

## Experiment runners

These are **writers**. Full phases can take minutes to hours and create large trace archives. Selection/freeze phases are historical provenance, not instructions to tune again. Use the existing selections for reproduction.

| Entry | Important interface | Inputs → outputs / caution |
| --- | --- | --- |
| [benchmark_paper.py](benchmark_paper.py) | Positional `smoke`/`test`, `--workers`, `--output-root`, `--archive-root`; also historical `thresholds/calibrate/bounds/development/freeze` | Frozen G1 configuration/operating points → phase metrics/events/manifests and gzip archives; full final73,800 scored runs |
| [benchmark_transfer.py](benchmark_transfer.py) | Positional `smoke`/`test`, `--workers`, `--output-root`, `--archive-root`; historical `freeze` | Same frozen policies on G2 → metrics/events/faults/age data and archives; full final12,880 runs |
| [benchmark_su.py](benchmark_su.py) | Required `--phase engineering/development/validation/test`, both root overrides, `--workers` | Seven fixed SU-1 systems → phase metrics, actual frames and archives; not Core CLI selection |
| [benchmark_joint_optimization.py](benchmark_joint_optimization.py) | Required `--phase development/validation/test`, `--workers` | Frozen JO plan → fixed `results/tais-joint` and local trace destinations; do not rerun in place |
| [run_experiments.py](run_experiments.py) | Required `--split development/validation/test`, optional `--smoke` | Original v0.1 matrix → **fixed** `results/<split>` or `<split>-smoke` and `results/traces`; may overwrite files, no output-root flag |

For a separate small paper smoke, choose both roots explicitly:

```sh
python scripts/benchmark_paper.py smoke --workers 1 \
  --output-root results/scratch/paper-smoke-01 \
  --archive-root results/scratch/paper-smoke-01-archives
python scripts/analyze_paper.py --phase smoke --root results/scratch/paper-smoke-01
python scripts/verify_paper.py --phase smoke --root results/scratch/paper-smoke-01
```

This is engineering smoke, not new held-out research. The original fixed-destination runner is retained for its historical study/CI, but is intentionally absent from the homepage demo.

## Summaries and analysis

These commands read saved runs but **write derived artifacts**; they are not passive validators.

| Entry | Arguments | Inputs → outputs |
| --- | --- | --- |
| [analyze_paper.py](analyze_paper.py) | `--phase smoke/development/test`, `--root` | G1 metrics/events → `phase/analysis` summaries, paired intervals and literal-point plots |
| [analyze_transfer.py](analyze_transfer.py) | `--phase smoke/test`, `--root` | G2 metrics/events/faults/age → grouped summaries and seed-paired intervals |
| [analyze_su.py](analyze_su.py) | `--phase`, `--root`; historical `--select` | SU-1 metrics → new analysis directory; selection option writes a lock and is not part of reproduction |
| [summarize_results.py](summarize_results.py) | Required `--split` | Original v0.1 metrics → fixed summary/CI/budget CSVs and plots under that split |
| [analyze_budget_sensitivity.py](analyze_budget_sensitivity.py) | No arguments | Frozen G1/G2 totals →60 qualification rows/manifest under fixed `results/tais-paper-review`; post-hoc2/5/10%, not parameter matching |
| [analyze_joint_optimization.py](analyze_joint_optimization.py) | Study-specific entry in [JO results](../results/tais-joint/README.md) | JO phase results → selection/analysis; retain original decisions |

[paper_metrics.py](paper_metrics.py) and [transfer_metrics.py](transfer_metrics.py) are shared scoring helpers, not top-level experiment commands. Figure/report builders (`paper_publication_figures.py`, `transfer_figures.py`, `build_paper_report.py`, `build_transfer_report.py`, `build_report.py`) regenerate presentation at their fixed study paths; use their campaign instructions before invoking them.

## Reproduction and validation

### Summary checks without a full campaign

```sh
python scripts/check_paper_artifacts.py
python scripts/verify_paper_revision.py
python scripts/verify_paper.py
python scripts/verify_transfer.py
```

| Entry | Options / scope | Required input and side effects |
| --- | --- | --- |
| [check_paper_artifacts.py](check_paper_artifacts.py) | No arguments | Committed paper numeric bindings, DOI metadata, source fingerprints and PDF presence; prints checks |
| [verify_paper_revision.py](verify_paper_revision.py) | No arguments | Current paper/PDF QA, protected sources/results and saved sensitivity; prints checks |
| [verify_paper.py](verify_paper.py) | `--root`, `--phase`; optional `--archives`, `--write-report` | Default checks saved G1 summaries; archive option needs complete original/replica paths; write-report explicitly writes verification JSON |
| [verify_transfer.py](verify_transfer.py) | `--root`, `--phase smoke/test`, `--archives none/sample/full` | Default checks saved G2 summaries; archive options load/roundtrip actual raw frames, no new policy campaign |
| [reproduce_transfer.py](reproduce_transfer.py) | `--check-only` | Existing G2 tests plus summary/source checks; no full replay |

Use Git history, not a source-only zip, for verifiers that compare a recorded base. Optional raw archive checks are more expensive than CSV checks and often need local-only files.

### Full replicas and historical audits

| Entry | Interface | Cost / destination |
| --- | --- | --- |
| [reproduce_paper.py](reproduce_paper.py) | `--output NEW_PATH`, `--workers` | **Full G1 campaign**, analysis and archive check; refuses existing output; no test recalibration |
| [reproduce_transfer.py](reproduce_transfer.py) | `--workers`; optional `--resume-root COMPLETE_REPLICA` | **Full G2 campaign** in automatically fresh scratch unless check-only/resume; compares all saved CSV hashes |
| [reproduce_baseline.py](reproduce_baseline.py) | No output override | Upstream code runs in temporary copies, but logs/manifests are written to **fixed `results/baseline/`**; historical/CI writer, not a passive integrity check |
| [verify_artifacts.py](verify_artifacts.py) | `--split`, optional `--traces`, `--replay-one` | Original v0.1 source/archive contract; later added source modules make a matching historical checkout important |
| [verify_su.py](verify_su.py), [verify_joint_delivery.py](verify_joint_delivery.py), [Core delivery audit](../examples/tais-core/verify_delivery.py) | One-shot historical entry points, no safe relocation flags | Require extensive local archives and original-history protection; create audit JSON exclusively, so an existing audit is expected to refuse rerun. Read existing checks instead |

Exact full-reproduction commands and assumptions belong to each [result namespace](../results/README.md), not a combined all-studies command.

## Paper construction and review

| Entry | Input → output | Effect |
| --- | --- | --- |
| [build_paper.py](build_paper.py) | Saved G1/G2 data → original and revised numeric paragraphs/tables, bindings, figures and sensitivity | **Writer**; calls `build_transfer_paper.py` and `paper_review_artifacts.py`; no simulations |
| [paper_review_artifacts.py](paper_review_artifacts.py) | Saved summaries/intervals → current review tables,187-word abstract and two plots | Presentation generator; normally called by build_paper |
| [build_transfer_paper.py](build_transfer_paper.py) | Saved G2 data → G2 presentation fragments/bindings | Called by build_paper; not a separate algorithm |
| [verify_paper_references.py](verify_paper_references.py) | Crossref requests → literature audit/BibTeX at frozen paths | **Network writer**, not the routine offline citation check; do not regenerate frozen metadata for navigation maintenance |

Compile from `papers/tais/` with `tectonic manuscript.tex --keep-logs`. Follow [paper build instructions](../papers/tais/README.md); a changed PDF needs a fresh render/QA fingerprint, without replacing historical audits. Tectonic is optional for reading the committed PDF and is not required for the Core demo.

## Separate historical and real-data tools

| Family / entry | Actual interface and purpose | Boundary |
| --- | --- | --- |
| `v02_*`, `inspect_v02_results.py` | Separate v0.2 run/summarize/forensics/verification; [recorded workflow](../docs/V02_REPRODUCIBILITY.md) | Fixed study paths; not current Core initialization |
| `rearm_*` | Separate repair matrix, diagnostics and report; [reproduction](../docs/BLOCKED_REARM_REPRODUCIBILITY.md) | Specific repair, no erased-event recovery |
| [run_budget_matched_experiment.py](run_budget_matched_experiment.py) | `--phase`, `--results-root`, `--archive-root`, optional `--selection`; paired confirmation-budget study | Full campaigns; [BM-1 NO-GO](../results/budget-matched/README.md) |
| [run_fault_event_observability.py](run_fault_event_observability.py) | `--phase`, both root overrides, `--workers`; timing/identifiability matrix | [FO-1](../results/fault-event-observability/README.md), not a new detector |
| [run_independent_reference_budget.py](run_independent_reference_budget.py) | `--phase calibrate/development/validation/test`, both roots, `--workers` | [ReferenceGate NO-GO](../results/independent-reference-budget/README.md); no new selection |
| [benchmark_wire_codec.py](benchmark_wire_codec.py) | `--archive`, `--output`, optional `--smoke` | **Existing v0.1 archive required**; encoded-frame audit, not new sensing evidence |
| [benchmark_wire_v2.py](benchmark_wire_v2.py) / [audit_wire_health.py](audit_wire_health.py) | `--archive`, `--output`; benchmark also `--log-dir`, `--smoke` | Large historical stateful/loss experiments; [wire-v2 record](../results/wire-payload-v2/README.md) |
| [greenhouse.py](greenhouse.py) | `download --url --output [--sha256]`; `audit FILE --output [--mapping] [--time-format]` | Real local CSV audit/reconstruction; explicitly supplied semantics, not inferred causal clocks |
| [import_joint_csv.py](import_joint_csv.py) | `--input`, `--output`, required `--time-semantics`; column options | Validate/import local CSV without invented time resolution |
| [offline_spatial.py](offline_spatial.py) | `prepare/run/analyze/freeze`, required `--output`; workbook/cache/split/freeze options | **Local workbook required**; separate [OSP-1](../results/offline-spatial-pilot/README.md), failed held-out coverage |

Each research family keeps its analyzer, report, seed-audit and verifier alongside its runner. Those tools can write locks/check records or depend on an exact historical state; use the linked study instructions. `publish_*.py` scripts are historical **remote publication writers**, some with hardcoded destinations. They are not setup/reproduction commands and must not be invoked casually.
