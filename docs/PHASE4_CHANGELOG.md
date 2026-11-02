# Phase4 change inventory

Base c71e621. New files only; no old tracked file or upstream submodule changed.
At initial research delivery the changes were local and unstaged. Publication is
a separate user-authorized step. No history rewrite or default replacement.

| Area | Added files / purpose |
| --- | --- |
| Samplers | `src/tais/adaptive/sampling.py`: bounded median/MAD and causal trend-risk samplers; actual rolling budget, persistence and cooldown |
| Integration | `src/tais/adaptive/policy.py`: optional Phase4Policy/CoreSender composition, original C11/detector/U/codec reused |
| Metrics | `src/tais/adaptive/sampling_metrics.py`: actual gap distributions, pre-event coverage and fast-cycle diagnostics |
| Conditions | `configs/phase4.json`, `scripts/phase4_support.py`: centralized parameters, audited cohorts, old54+balanced12 cases,24-method matrix |
| Diagnosis | `scripts/diagnose_phase4.py`: old MA-1 actual sampled-time candidate replay and scope-aware miss categories |
| Batch | `scripts/benchmark_phase4.py`: exclusive engineering/freeze/test/replica outputs, exact source snapshots and hashes |
| Statistics | `scripts/analyze_phase4.py`: saved-observation analysis,136 Holm-corrected comparisons, predefined recommendation gates,12 PNG/PDF figures |
| Validation | `scripts/verify_phase4.py`, `tests/test_phase4_sampling.py`: pairing/wire/protection/replay checks and36 new executable tests |
| Reporting | `scripts/report_phase4.py`: audience-neutral Chinese result report only, bound to actual table hashes |
| Generic docs | `PHASE4_AUDIT.md`, `PHASE4_ALGORITHM_DESIGN.md`, `PHASE4_PROTOCOL.md`, `PHASE4_RESULTS_ZH.md` and result index |
| Evidence | `results/phase4/`: diagnosis, both engineering attempts, final observations/statistics/plots, immutable source snapshots, checks and protection ledger |
| CI | `.github/workflows/phase4.yml`: contracts, original MA-1 evidence, final Phase4 evidence and fresh engineering/plot smoke |
| Management | `AGENTS.md`: historical research protection and outside-Git personalized-report policy |

Personalized reports and their templates are deliberately absent from this
inventory and the repository. Generic results and code contain no new named
professor-specific narrative. Existing historical evidence is retained.

## Verification actually performed

- 942 root tests passed,2 existing strict expected failures;36 new Phase4 tests.
- Original AdaptiveSense upstream tests run separately; exact output in checks/.
- G1,G2,MA-1 evidence checks pass with frozen originals unchanged.
- All31,680 final run identities and99,840 per-event rows verified, plus43,560 raw
  archive hashes and3 exact deterministic policy/codec replays.
- All12 final PNGs visually inspected; matching vector PDFs saved.
- Numeric timestamp sorting defect repaired before final; two engineering
  datasets have identical3,168 metric rows. Initial records/sources/figures retained.

## Outcome and limits

Both new algorithms bound fast acquisitions and improve F1 versus native A7
with prespecified corrected support. Risk has higher F1 than Robust with more
sampling/communication; its F1 superiority versus A5 is not supported. Robust
saves samples but fails the quality gate. Both fail default-replacement criteria.
No field deployment, hardware energy or embedded timing validation was done.
