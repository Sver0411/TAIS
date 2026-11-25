# TAIS Closed-Loop & Spatial Reference Manuscript (`IEEEtran`)

This directory contains a standalone, publication-ready manuscript prepared in **IEEE Sensors Journal** double-column format (`\documentclass[journal]{IEEEtran}`) consolidating Studies I--III (TAIS Phases 5, 5.5, and 6) without modifying the frozen historical G1/G2 manuscript in `papers/tais/`.

## Contents

- `manuscript.tex` — Complete 8-page IEEE double-column LaTeX source (with TikZ architecture diagram, 5 native-print-width `7.16 in` vector PDF empirical figures, 6 `booktabs` tables, and 17 verified BibTeX references).
- `build_figures.py` — Deterministic figure generator reading frozen saved CSV/JSON outputs and emitting B&W-print-safe IEEE vector figures into `figures/`.
- `figures/fig02_dynamics_boundary.pdf` .. `fig06_spatial_identifiability.pdf` — Native `7.16 in` double-column IEEE print-ready vector figures (no redundant report suptitles, serif 7.5--8.5 pt typography, distinct markers & hatches).
- `references.bib` — Verified peer-reviewed BibTeX entries (`IEEEtran` bibliography style).
- `manuscript.pdf` — Compiled 8-page vector PDF (`tectonic manuscript.tex`, zero overfull/missing/undefined warnings).
- `graphical_abstract.pdf` / `graphical_abstract.png` — Mandatory IEEE Sensors Journal Graphical Abstract.

## Rebuild Commands

```sh
python papers/tais-closed-loop/build_figures.py
cd papers/tais-closed-loop && tectonic manuscript.tex
```

## Pre-Submission Human Checklist

Before submitting to IEEE Sensors Journal or an IEEE IoT conference/journal:
1. Replace the placeholder author block, affiliations, and funding footnote in `manuscript.tex`.
2. Add author biographies/photos if required by the final IEEE journal proof stage.
3. Verify venue-specific AI-assistance disclosure rules and upload `graphical_abstract.png` via the IEEE Author Portal.
