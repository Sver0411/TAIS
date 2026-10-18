# TAIS research portfolio

Materials for an initial discussion with a graduate-school supervisor in information science, IoT, sensor networks, or edge computing. Author identifier: **Sver0411**; undergraduate background: Internet of Things Engineering. This is an unpublished research portfolio, not a deployed agricultural system or a peer-reviewed paper.

| Reading purpose | Material |
| --- | --- |
| Two-page Japanese overview | [日本語概要](RESEARCH_SUMMARY_JA.md) / [printable A4 PDF](RESEARCH_SUMMARY_JA.pdf) |
| Detailed technical evidence | [English report](TECHNICAL_REPORT_EN.md) / [A4 PDF](TECHNICAL_REPORT_EN.pdf) |
| Check every main number | [Results provenance](RESULTS_PROVENANCE.md), [selected source records](VERIFIED_RESULTS.json), [SHA-256 input manifest](SOURCE_MANIFEST.json) |
| Inspect or reuse figures | [Figure index](FIGURE_INDEX.md), [SVG and PNG files](figures/) |
| Examine weaknesses and editorial decisions | [Simulated academic review](REVIEW_NOTES.md) |

**Central finding:** reliability gating changes a tradeoff, rather than dominating the baselines. The v0.1 default preserves pooled synthetic recall while increasing application bytes; v0.2 has a small late benefit at one declared point; Rearm fixes a specific recovery transition. OSP-1 has local exploratory effects, null-control similarities, local-event harms and added reference cost, but **held-out target/reference coverage25.89%/24.12% fails the50%gate**. There is no qualified independent spatial-effectiveness evidence.

Synthetic experiments, semi-synthetic real-background exploration, implementation tests, and unconfirmed deployment hypotheses remain separate. A passed software test is not a field result; application bytes are not radio energy. All frozen results, original protocols and formal-online NO-GO decisions remain unchanged. These materials interpret the evidence snapshot `f21bc2f0e1d01d0670ce1c1bd4ab5a2aab7e171d` on branch `docs/tais-research-portfolio`.

## Read-only figure reproduction

No raw workbook, sensor hardware, credentials, parameter search, or effect rerun is required. From the repository root, use the existing locked numerical/plotting environment:

```bash
.venv/bin/python docs/research-portfolio/build_figures.py
```

This regenerates only portfolio SVG/300-dpi PNG files, selected-result JSON and input fingerprints. It reads archived metrics and saved diagnostic trajectories, retaining the original default, three-stratum view and specified historical failures. It does not overwrite old plots. Complete original operating points remain linked from the provenance ledger; the figures are not new threshold selection.

## PDF reproduction and checks

`render_reports.py` reads the Markdown and corresponding PNG figures, embeds fonts, uses A4 margins, live source links, page numbers and section bookmarks. Markdown comments `<!-- PAGEBREAK -->` encode the intended reading sequence. PDF changes are editorial only.

Create a separate document environment if necessary (do not change the research dependency lock):

```bash
python3 -m venv /tmp/tais-portfolio-docs
/tmp/tais-portfolio-docs/bin/python -m pip install reportlab Pillow pypdf
export TAIS_JA_FONT='/absolute/path/to/embeddable-Japanese-TrueType-font.ttf'
/tmp/tais-portfolio-docs/bin/python docs/research-portfolio/render_reports.py
```

The delivered files use locally installed Arial Unicode for Japanese and ReportLab Vera for Latin text; no original font file is redistributed. On another system supply an appropriately licensed, embeddable Japanese TTF. A font missing required characters causes a failure rather than silent substitution. The authoring environment is recorded in `DOCUMENT_CHECKS.json`; exact PDF bytes may differ with fonts, image backend, metadata timestamps and ReportLab versions. The underlying CSV values and source hashes must not change.

Use Poppler to render every page for visual inspection, then the verifier for source/number/link/font/page/scope checks. Keep temporary page images outside Git:

```bash
mkdir -p /tmp/tais-portfolio-review
pdftoppm -r 110 -png docs/research-portfolio/RESEARCH_SUMMARY_JA.pdf /tmp/tais-portfolio-review/ja
pdftoppm -r 110 -png docs/research-portfolio/TECHNICAL_REPORT_EN.pdf /tmp/tais-portfolio-review/en
/tmp/tais-portfolio-docs/bin/python docs/research-portfolio/verify_portfolio.py
git diff --check
```

The verifier uses the evidence snapshot's Git objects and committed sources; it does not execute existing CI experiments or rewrite research results. This documentation branch is committed with `[skip ci]` to avoid triggering the repository's baseline/smoke experiment workflow. Report CI as skipped for this branch; the historic215passed/2xfails result belongs to the source snapshot's [actual successful CI](https://github.com/Sver0411/TAIS/actions/runs/39097996830).
