# Validation history

All counts below are actual local executions on 2026-10-17.

- Upstream AdaptiveSense: 235 passed, 0 failed; config parity 69/69. Regenerated metrics_all.csv and metrics_summary.csv are byte-identical to pinned upstream. Detailed logs in results/baseline/.
- Upstream SensorTrust: Python 27 passed, 0 failed; standalone C 21 tests /404 checks, 0 failed.
- First TAIS run: 60 passed, 1 failed; retained results/prototype-tests-initial.log. Isolated degraded spike caused delayed false event from residual history; fixed channel-local cancellation/reseed and retained regression.
- After correction: 61 passed, 0 failed.
- During adding metrics tests, a collection run failed with ModuleNotFoundError: tais. The editable-install .pth file had macOS UF_HIDDEN set (st_flags=32832, UF_HIDDEN=32768); Python 3.14 site.addpackage skips hidden .pth. Clearing that flag locally temporarily restored the editable import, but the OS subsequently reapplied it. Development/validation launch attempts then failed before any experiments (logs retained in results/setup-failures). Added explicit repository-src bootstrap in scripts and pytest pythonpath so source-checkout commands do not depend on that environment behavior. This was an environment collection failure, not an algorithm result; no test removed. Portable installation instructions use pip editable; on affected macOS clear the flag with `chflags nohidden .venv/lib/python*/site-packages/__editable__*.pth`.
- With metrics tests: 64 passed, 0 failed (results/prototype-tests.log). Includes all 45 scenarios for deterministic/bounded runs, isolation, recovery, sustained events, spike cancellation, bounded confirmation, no-future/no-unsampled access, independent labels, actual upstream scheduler parity, logging-only parity, C replay fixture parity, metric N/A and reconstruction checks.

The smoke experiment predates the final health-flag reporting correction and is retained as development history only. Full split outputs use the subsequent bootstrap-fix freeze commit (recorded in each manifest), with unchanged algorithm/config from 273758d and supersede the smoke output. No thresholds were chosen on held-out seeds.
