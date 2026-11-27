# TAIS Closed-Loop & Spatial Reference Manuscript (Official IEEE Sensors Journal Template)

This directory contains the standalone, publication-ready manuscript formatted in the official **IEEE Sensors Journal** template (`\documentclass[journal,twoside,web]{ieeecolor}` + `jsen.sty`), consolidating Studies I--III (TAIS Phases 5, 5.5, and 6) without modifying the frozen historical G1/G2 manuscript in `papers/tais/`.

## Contents

- `manuscript.tex` — Complete 8-page official IEEE Sensors Journal double-column LaTeX source (with TikZ architecture diagram, 5 native-print-width `7.16 in` vector PDF empirical figures, 6 `booktabs` tables, and 31 verified BibTeX references).
- `ieeecolor.cls`, `jsen.sty`, `IEEEtran.bst`, `LOGO-jsen-web.png` — Official IEEE Sensors Journal template assets for self-contained compilation.
- `build_figures.py` — Deterministic figure generator reading frozen saved CSV/JSON outputs and emitting B&W-print-safe IEEE vector figures into `figures/`.
- `build_graphical_abstract.py` — Deterministic 3:2 Graphical Abstract generator aligned with the revised manuscript statistics.
- `figures/fig01_architecture.png` / `.pdf` and `fig02_dynamics_boundary.pdf` .. `fig06_spatial_identifiability.pdf` — Native `7.16 in` double-column IEEE print-ready vector figures.
- `references.bib` — Verified peer-reviewed BibTeX entries (`IEEEtran` bibliography style).
- `manuscript.pdf` — Compiled 8-page vector PDF (`tectonic -X compile manuscript.tex`, zero body overfull/missing/undefined warnings).
- `graphical_abstract.pdf` / `graphical_abstract.png` — Mandatory IEEE Sensors Journal Graphical Abstract.

## Rebuild Commands

```sh
python3 papers/tais-closed-loop/build_figures.py
python3 papers/tais-closed-loop/build_graphical_abstract.py
cd papers/tais-closed-loop && tectonic -X compile manuscript.tex
```
