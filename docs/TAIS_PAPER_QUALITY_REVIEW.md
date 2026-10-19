# Paper reviewer audit and revisions

Judgment: **B — draft/evidence complete, key external-validity experiments still recommended.** This is a systems simulation study, not a new detector/theoretical optimality paper. The judgment does not presume publication acceptance.

| Reviewer question | Audit result / resulting manuscript treatment |
|---|---|
| 1. Clear novelty? | Explicitly limited to reproducible integration, separated evaluation and conditional tradeoff evidence. Prior art rules out a broad first-joint-optimizer claim. |
| 2. Only weak self baselines? | Six fixed periods and three independently implemented adaptive ideas; original native high-frequency curves and development-selected resource-bound points all retained. These still do not replace a faithful suitable literature reproduction. |
| 3. Reasonable independent parameters? | Highest development F1 among disclosed candidates; no held-out tuning. Failed cap-only matching retained; minimum-bound refinement disclosed before freeze. Native minimum5s curves remain visible. |
| 4. More samples for Recall? | Actual counts, two approximate budgets and explicit final ±5% flags; no equality claim outside qualification. Native and common-detector results kept separate. |
| 5. Favorable scenarios only? | Every original45 scenario and all20 test seeds retained, with all fault/profile/channel/no-event groups. Stable offset, drift and masking failures remain. |
| 6. Local/receiver conflation? | Sender-on-upload, local detections and independently decoded receiver false→true edges separately scored. Conditional delays interpreted with misses and matched-in-both supplementary table. |
| 7. Application bytes called energy? | Removed any such interpretation. Dimensionless additive sensitivity only; unknown processing cost and nonlinear radio dependence disclosed. |
| 8. Synthetic faults called natural faults? | Title/abstract/methods/limitations explicitly simulation; no field efficacy or natural-fault robustness claim. |
| 9. Inspired called reproduction? | Rao-inspired consistently named. Four-point fit and all missing CS/APDT/dual-prediction components documented. No faithful external full-method success asserted. |
| 10. References verifiable? | Eight DOI registration records/hashes archived; citation keys and bibliography cross-checked. Detailed Rao source read; other inspected-source scope explicit. No invented direct quotations. |
| 11. Code/figures/text consistent? | Source freeze before test; actual encode/decode; per-run and aggregate fingerprints; tables/numerical paragraphs generated from CSV; cell audit and LaTeX compile/render checks. |
| 12. Failures retained? | Initial cap-only budget failure, all final adverse comparisons, historical H net harm and SU balanced-default NO-GO retained. No algorithm/results adjusted to improve the manuscript. |

Manuscript revisions: remove broad “new algorithm” language; distinguish functional inequivalence of health-free payloads; include common-detector schedule isolation, all independent budget contrasts and uncertainty; emphasize fault/offset/short-event groups; report received-state metrics and normal-data age; explain U's reuse on external schedules; move information-loss, synthetic-generator, link and energy limitations into the formal section. The paper explains the main research evolution (H failure and SU tradeoff) without narrating every historical branch.

Remaining submission weaknesses: a single synthetic family with narrow temporal geometry, temperature-only fault injection, detector sharing, lack of a faithful applicable literature-method reproduction, no natural annotated field data, no MCU or wireless energy measurements. A second independently specified generator and a reproducible suitable paper algorithm would be the most direct additions for a stronger comparative submission. Hardware experiments are necessary only for hardware/energy claims, which the present paper does not make.
