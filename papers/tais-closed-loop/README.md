# TAIS Closed-Loop & Spatial Reference Manuscript (`IEEEtran`)

This directory contains a standalone, publication-ready manuscript prepared in **IEEE Sensors Journal** double-column format (`\documentclass[journal]{IEEEtran}`) consolidating TAIS Phases 5, 5.5, and 6 without modifying the frozen historical G1/G2 manuscript in `papers/tais/`.

## Contents

- `manuscript.tex` — Complete IEEE double-column LaTeX source (with TikZ architecture diagram, 5 vector PDF empirical figures, 6 `booktabs` tables, and 17 verified BibTeX references).
- `references.bib` — Verified peer-reviewed BibTeX entries (`IEEEtran` bibliography style).
- `manuscript.pdf` — Compiled vector PDF (`tectonic manuscript.tex`).
- `graphical_abstract.pdf` / `graphical_abstract.png` — Mandatory IEEE Sensors Journal Graphical Abstract summarizing the 3D closed-loop C11 controller, E220 hardware traces, and 54-mote spatial identifiability results.

## Rebuild Commands

```sh
cd papers/tais-closed-loop
tectonic manuscript.tex
```

## Pre-Submission Human Checklist

Before submitting to IEEE Sensors Journal or an IEEE IoT conference/journal:
1. Replace the placeholder author block, affiliations, and funding footnote in `manuscript.tex`.
2. Add author biographies/photos if required by the final IEEE journal proof stage.
3. Verify venue-specific AI-assistance disclosure rules and upload `graphical_abstract.png` via the IEEE Author Portal.
