# Validation history

All counts below are actual local executions on 2026-10-17.

- Upstream AdaptiveSense: 235 passed, 0 failed; config parity 69/69. Regenerated metrics_all.csv and metrics_summary.csv are byte-identical to pinned upstream. Detailed logs in results/baseline/.
- Upstream SensorTrust: Python 27 passed, 0 failed; standalone C 21 tests /404 checks, 0 failed.
- First TAIS run: 60 passed, 1 failed; retained results/prototype-tests-initial.log. Isolated degraded spike caused delayed false event from residual history; fixed channel-local cancellation/reseed and retained regression.
- After correction: 61 passed, 0 failed.
- During adding metrics tests, a collection run failed with ModuleNotFoundError: tais. The editable-install .pth file had macOS UF_HIDDEN set (st_flags=32832, UF_HIDDEN=32768); Python 3.14 site.addpackage skips hidden .pth. Clearing that flag locally temporarily restored the editable import, but the OS subsequently reapplied it. Development/validation launch attempts then failed before any experiments (logs retained in results/setup-failures). Added explicit repository-src bootstrap in scripts and pytest pythonpath so source-checkout commands do not depend on that environment behavior. This was an environment collection failure, not an algorithm result; no test removed. Portable installation instructions use pip editable; on affected macOS clear the flag with `chflags nohidden .venv/lib/python*/site-packages/__editable__*.pth`.
- With metrics tests: 64 passed, 0 failed (results/prototype-tests.log). Includes all 45 scenarios for deterministic/bounded runs, isolation, recovery, sustained events, spike cancellation, bounded confirmation, no-future/no-unsampled access, independent labels, actual upstream scheduler parity, logging-only parity, C replay fixture parity, metric N/A and reconstruction checks.

The original smoke predates the final health-flag reporting correction and remains in Git history. The current smoke is regenerated after the reporting fix and is not used for research conclusions. Full split outputs use the subsequent bootstrap-fix freeze commit (recorded in each manifest), with unchanged algorithm/config from 273758d and supersede the smoke output. No thresholds were chosen on held-out seeds.

- Added the unsampled-observation guard for TAIS as well as fixed replay: final local suite **66 passed, 0 failed**. The added artificial greenhouse audit fixture checks gap/missing statistics only, without claiming access to Hull data.
- GitHub Actions at 78b3a43: Linux/Python 3.14 prototype 65 passed; upstream 235 +27 Python tests, 69 parity checks and 21 C tests /404 checks passed; smoke and summary commands succeeded. The additional guard test is in the later commit and its final CI status is recorded separately.
- Complete development/validation: 5850 scored runs each; respectively 6300 archive hashes and one newly executed deterministic replay checked per split. No threshold adjustment made from these results.

- CI at c1921d1 (run 39010582071) passed 66 prototype tests, all upstream tests/parity/C checks and smoke execution, then failed plot generation with `ValueError: Axis limits cannot be NaN or Inf`. After distinguishing sequential spikes, that small smoke matrix has no actual same-channel overlap group. Fixed the plot to display N/A for an absent group, without altering data or deleting any cases. Added a regression test that runs the summary on that exact incomplete matrix. Final local suite: **67 passed, 0 failed**; summary CLI succeeds. Failed CI log retained in results/github-ci-39010582071.log.

- Full independent test: 17550 scored runs, 18900 trace archives checked and one fresh deterministic replay matched. All 50 seeds /45 scenarios /13 operating points completed: 29250 scored runs, 31500 archived signal/decision hashes verified across three splits and three new replays. Final figures were visually inspected; tables are generated from actual CSVs.
