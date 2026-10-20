# Paper-only major revision evidence

Base: `db23a95ef95fd025553b70754625af7b42b5682e`; branch: `docs/tais-paper-major-revision`.

No algorithm, generator, operating-point selection, old CSV, truth archive or frozen result fingerprint was changed. No large simulation campaign was run. The existing campaigns remain in `results/tais-paper/` and `results/tais-transfer/`.

- `budget_sensitivity.csv`: all 60 actual native independent+C11 control-target pairs, with post-hoc 2/5/10% qualification. These thresholds change eligibility labels only. `budget_sensitivity_focus.md` shows the 11 discussion pairs; neither output changes selection or performance.
- `budget_sensitivity_manifest.json`: source/output hashes and exact qualification rule.
- `protection.json`: 202 baseline source/configuration/result hashes, plus the baseline PDF identity. Vendor Git links are protected by the unchanged Git diff; no submodule updates were made.
- `build_manifest.json`, `build-repeatability.json`: current numerical presentation binding and 64 byte-identical files after a second build. Generated review numbers have 506 source/row/column bindings in `papers/tais/tables/review_data_audit.csv`; the old G1/G2 bindings remain checked separately.
- `abstract.json`: 187-word current abstract.
- `pdf-validation.json`, `pdf-geometry.json`, `latex.log`: current 17-page PDF, source/render hashes, all-page visual and geometry review, final compiler log. Historical PDF audits remain unchanged in their original directories. Rendered pages themselves are ignored scratch files.
- `regression.log`: actual full regression result, 892 passed and 2 expected failures. No new simulation campaign was invoked by the paper revision; regression tests use the existing small fixtures.
- `check_paper_artifacts.json`, `verify_paper_revision.json`, `verify_paper.json`, `verify_transfer.json`: successful final read-only checks. The last two verify saved campaigns, not newly run campaigns. Their zero archive/frame counters accurately indicate that optional raw-archive replay checks were not repeated in this revision.

Rebuild from frozen CSVs with `.venv/bin/python scripts/build_paper.py`; compile from `papers/tais/` using `tectonic manuscript.tex --keep-logs`. Run the four verification scripts above and `.venv/bin/python -m pytest -q`. See `papers/tais/README.md` for the complete command sequence. A newly compiled PDF can differ in creation metadata; any replacement PDF needs a fresh render and current-PDF QA fingerprint, without changing the historical checks.
