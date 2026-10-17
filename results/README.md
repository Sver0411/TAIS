# Evidence and result provenance

This directory contains **actual upstream reproduction output** and **new TAIS synthetic experiments**. They use different signal suites and must not be conflated.

- [Baseline reproduction](baseline/manifest.json): AdaptiveSense 235 Python tests, 69 config checks; SensorTrust 27 Python tests plus 21 standalone C tests /404 checks. All passed. Both regenerated AdaptiveSense metric CSVs byte-identical to pinned originals. Commands, compiler, Python/dependencies and SHA-256 are recorded.
- [Prototype tests](prototype-tests.log): current local result. [Initial failed test](prototype-tests-initial.log) is retained, with correction explained in [validation history](../docs/VALIDATION_HISTORY.md). No failing test was deleted.
- `development-smoke/`: final 39-run smoke for quick-start/CI verification; not used for research conclusions. The earlier pre-fix smoke remains in Git history.
- `development/`, `validation/`, `test/`: 5850 /5850 /17550 new scored runs, completed and verified. Each includes per-run `metrics.csv`, manifests, micro summaries, scenario/relationship tables, 2000-replicate paired seed bootstrap CIs, nearest actual budget comparison and upload/recall curves. All three split manifests and metrics exist and verification succeeded.
- `traces/<split>/<seed>/<scenario>/`: ignored local canonical gzip signals (latent/noisy/faulted, independent event/fault labels) and method decisions/reports. Every archive is enumerated in the committed split manifest. Reproduce them with the README commands; original raw greenhouse data is never included.
- [Greenhouse access status](greenhouse-access.json): landing metadata and license verified, raw APIs returned 403; no original CSV audit or greenhouse TAIS result.

Main report: [RESEARCH_REPORT.md](../docs/RESEARCH_REPORT.md). A no-event row has blank/N/A recall. Delays have blank/N/A when no event is matched or no fault is detected. Reported events mean first application upload request while a channel episode is active; local detections are separately recorded. Success on a physical radio link is not modeled.

Counterfactual fault-attribution, reconstruction, diagnostic-demand counts and paired extra sampling have the precise definitions in [protocol](../docs/EXPERIMENT_PROTOCOL.md). Application uploads/bytes are not joules, RF traffic or battery life. No significance/superiority claim follows from an attractive single operating point.

All **29250** scored runs are complete. All **31500** archive hashes and three fresh deterministic replays passed verification. At original thresholds, independent-test TAIS/AdaptiveSense recall both 51.56%; operational fault false reports 458/652; samples 76430/101108; requests 47694/49816. Actual same-channel overlap recall falls from 35.28% to 30.28%. Health metadata increases bytes versus plain AdaptiveSense. Confirmation has mixed outcomes; see the full ablation and CIs. Final local test suite: **67 passed, 0 failed**. The earlier one-test failure and later CI plotting failure are retained and explained.
