# TAIS manuscript: final academic revision

The current source incrementally revises the G1/G2 study at `db23a95ef95fd025553b70754625af7b42b5682e` on branch `docs/tais-paper-major-revision`. Scientific scope is **conditional tradeoffs across two differently defined synthetic tasks**, including different event-truth windows. No algorithm, generator, old result, protocol or archive changes in this revision. The maturity judgment A means venue selection and submission preparation can begin; it is not an acceptance prediction. Human author details/approval and venue-specific requirements remain pending.

The main text has one quality table, one resource/qualification table, the implemented architecture, and two grayscale-safe result figures. Full operating points, adverse diagnostics and post-hoc budget sensitivity remain in readable appendices and the frozen CSV artifacts. The generated abstract has 187 words. Rao-inspired remains an explicitly incomplete adaptation; +C11 and public +U extensions are distinguished.

## Build without new simulations

From the repository root, after installing the locked dependencies and editable project:

```sh
.venv/bin/python scripts/build_paper.py
cd papers/tais
tectonic manuscript.tex --keep-logs
```

Then, from the repository root:

```sh
.venv/bin/python scripts/check_paper_artifacts.py
.venv/bin/python scripts/verify_paper_revision.py
.venv/bin/python scripts/verify_paper.py
.venv/bin/python scripts/verify_transfer.py
.venv/bin/python -m pytest -q
```

`build_paper.py` preserves the G1/G2 numerical bindings and invokes `paper_review_artifacts.py`. That script calls `analyze_budget_sensitivity.py`, reads only saved summaries/intervals/event groups, and writes new outputs under `results/tais-paper-review/` plus presentation files in this directory. It does not replay data, calibrate parameters or rewrite old results. The 2/5/10% sensitivity analysis is post hoc; 5% reproduces the historical qualification rule. All 60 existing independent+C11 control-target pairs remain, without choosing a new operating point.

Numerical provenance: original `tables/data_audit.csv` and `transfer_data_audit.csv`, plus new `review_data_audit.csv` and `review_source_fingerprints.json`. New source/data protection, build-repeatability, regression and PDF evidence live in `results/tais-paper-review/`; old `results/tais-paper/` and `results/tais-transfer/` checks remain historical and immutable. The G2 verifier selects the new current-PDF evidence instead of rewriting its historical PDF fingerprint. This changes no experimental scoring.

## Review and submission materials

- `docs/TAIS_PAPER_REVISION_CHANGELOG.md`: responses and exact old/new wording.
- `docs/TAIS_PAPER_LAYOUT_AUDIT.md`: actual rendered-page review and suspect-defect verdicts.
- `docs/TAIS_PAPER_QUALITY_REVIEW.md`: final fourteen-question review.
- `docs/TAIS_PAPER_SUMMARY_ZH.md`: current Chinese synopsis.
- `docs/TAIS_SUBMISSION_CHECKLIST.md`: real author/affiliation/funding, human verification, AI-use rules, anonymity, template and venue checks.

Eight verified scientific DOI entries are retained; only acronym casing protection is corrected. AI tool assistance is transparently identified as a draft disclosure requiring human verification and venue adaptation, not a fabricated approval. Figures are deterministic plots of saved data and a code-based architecture diagram.

## Historical materials

The original G1-only twelve-page PDF/root source are retained in `history/` and commit `0170196...`. The G1+G2 nineteen-page draft and complete original figure/table layout remain at `db23a95...`. Original replay/reproduction commands remain documented in those snapshots; they are not invoked for this paper-only revision. Raw archives and frozen outcomes remain available with their existing fingerprints. No new simulation campaign is required to reproduce this revision's statistical or presentation changes.
