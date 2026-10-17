# v0.2 added/modified file inventory

Full tracked delivery inventory relative to v0.1 main68af4b6. Raw large traces are ignored and enumerated by each split manifest. Only README.md and docs/LIMITATIONS.md modify preexisting v0.1 files; legacy policy/config/scripts/results/report and both submodules are unchanged.


## New research modules

- [src/tais_v02/__init__.py](../src/tais_v02/__init__.py)

- [src/tais_v02/config.py](../src/tais_v02/config.py)

- [src/tais_v02/evidence.py](../src/tais_v02/evidence.py)

- [src/tais_v02/forensics.py](../src/tais_v02/forensics.py)

- [src/tais_v02/replay.py](../src/tais_v02/replay.py)

- [src/tais_v02/scheduler.py](../src/tais_v02/scheduler.py)


## Analysis, experiment and publication tools

- [scripts/inspect_v02_results.py](../scripts/inspect_v02_results.py)

- [scripts/publish_research_branch.py](../scripts/publish_research_branch.py)

- [scripts/v02_forensics.py](../scripts/v02_forensics.py)

- [scripts/v02_identifiability.py](../scripts/v02_identifiability.py)

- [scripts/v02_report.py](../scripts/v02_report.py)

- [scripts/v02_run.py](../scripts/v02_run.py)

- [scripts/v02_seed_audit.py](../scripts/v02_seed_audit.py)

- [scripts/v02_summarize.py](../scripts/v02_summarize.py)

- [scripts/v02_verify.py](../scripts/v02_verify.py)


## Tests including retained known failure

- [tests/test_v02.py](../tests/test_v02.py)


## Frozen new configuration

- [configs/v02.yaml](../configs/v02.yaml)


## Research documents

- [docs/FAILURE_ANALYSIS_V0.1.md](../docs/FAILURE_ANALYSIS_V0.1.md)

- [docs/LIMITATIONS.md](../docs/LIMITATIONS.md)

- [docs/RESEARCH_REPORT_V0.2.md](../docs/RESEARCH_REPORT_V0.2.md)

- [docs/V02_DESIGN.md](../docs/V02_DESIGN.md)

- [docs/V02_FILES.md](../docs/V02_FILES.md)

- [docs/V02_INTERPRETATION.md](../docs/V02_INTERPRETATION.md)

- [docs/V02_PRETEST_REVIEW.md](../docs/V02_PRETEST_REVIEW.md)

- [docs/V02_REPRODUCIBILITY.md](../docs/V02_REPRODUCIBILITY.md)


## Entry point

- [README.md](../README.md)


## Actual outputs, metadata and logs

- [results/v0.2/FREEZE.json](../results/v0.2/FREEZE.json)

- [results/v0.2/README.md](../results/v0.2/README.md)

- [results/v0.2/SHA256SUMS](../results/v0.2/SHA256SUMS)

- [results/v0.2/baseline-reproduction-command.txt](../results/v0.2/baseline-reproduction-command.txt)

- [results/v0.2/baseline-reproduction.log](../results/v0.2/baseline-reproduction.log)

- [results/v0.2/baseline/AdaptiveSense-0.log](../results/v0.2/baseline/AdaptiveSense-0.log)

- [results/v0.2/baseline/AdaptiveSense-1.log](../results/v0.2/baseline/AdaptiveSense-1.log)

- [results/v0.2/baseline/AdaptiveSense-2.log](../results/v0.2/baseline/AdaptiveSense-2.log)

- [results/v0.2/baseline/AdaptiveSense-3.log](../results/v0.2/baseline/AdaptiveSense-3.log)

- [results/v0.2/baseline/SensorTrust-0.log](../results/v0.2/baseline/SensorTrust-0.log)

- [results/v0.2/baseline/SensorTrust-1.log](../results/v0.2/baseline/SensorTrust-1.log)

- [results/v0.2/baseline/SensorTrust-2.log](../results/v0.2/baseline/SensorTrust-2.log)

- [results/v0.2/baseline/manifest.json](../results/v0.2/baseline/manifest.json)

- [results/v0.2/baseline/metrics_all.csv](../results/v0.2/baseline/metrics_all.csv)

- [results/v0.2/baseline/metrics_summary.csv](../results/v0.2/baseline/metrics_summary.csv)

- [results/v0.2/cases-audit.log](../results/v0.2/cases-audit.log)

- [results/v0.2/cases/50-drift_same_long-0.75.json.gz](../results/v0.2/cases/50-drift_same_long-0.75.json.gz)

- [results/v0.2/cases/50-drift_same_long-0.75.png](../results/v0.2/cases/50-drift_same_long-0.75.png)

- [results/v0.2/cases/91-spike_same_long-1.json.gz](../results/v0.2/cases/91-spike_same_long-1.json.gz)

- [results/v0.2/cases/91-spike_same_long-1.png](../results/v0.2/cases/91-spike_same_long-1.png)

- [results/v0.2/cases/README.md](../results/v0.2/cases/README.md)

- [results/v0.2/cases/changed_events.csv](../results/v0.2/cases/changed_events.csv)

- [results/v0.2/checksum-verification.log](../results/v0.2/checksum-verification.log)

- [results/v0.2/ci-39013521047-failure.log](../results/v0.2/ci-39013521047-failure.log)

- [results/v0.2/ci-39013800827-success.log](../results/v0.2/ci-39013800827-success.log)

- [results/v0.2/development-run.log](../results/v0.2/development-run.log)

- [results/v0.2/development-summary.log](../results/v0.2/development-summary.log)

- [results/v0.2/development-verification.log](../results/v0.2/development-verification.log)

- [results/v0.2/development/by_fault_type.csv](../results/v0.2/development/by_fault_type.csv)

- [results/v0.2/development/by_information_class.csv](../results/v0.2/development/by_information_class.csv)

- [results/v0.2/development/by_profile.csv](../results/v0.2/development/by_profile.csv)

- [results/v0.2/development/by_relationship.csv](../results/v0.2/development/by_relationship.csv)

- [results/v0.2/development/by_scenario.csv](../results/v0.2/development/by_scenario.csv)

- [results/v0.2/development/confidence_intervals.csv](../results/v0.2/development/confidence_intervals.csv)

- [results/v0.2/development/events.csv](../results/v0.2/development/events.csv)

- [results/v0.2/development/faultfalse_recall.png](../results/v0.2/development/faultfalse_recall.png)

- [results/v0.2/development/manifest.json](../results/v0.2/development/manifest.json)

- [results/v0.2/development/metrics.csv](../results/v0.2/development/metrics.csv)

- [results/v0.2/development/paired_bootstrap.csv](../results/v0.2/development/paired_bootstrap.csv)

- [results/v0.2/development/recall_uploads.png](../results/v0.2/development/recall_uploads.png)

- [results/v0.2/development/summary.csv](../results/v0.2/development/summary.csv)

- [results/v0.2/environment.txt](../results/v0.2/environment.txt)

- [results/v0.2/forensics-run.log](../results/v0.2/forensics-run.log)

- [results/v0.2/forensics/drift_same_long-AdaptiveSense.json.gz](../results/v0.2/forensics/drift_same_long-AdaptiveSense.json.gz)

- [results/v0.2/forensics/drift_same_long-GateOnly.json.gz](../results/v0.2/forensics/drift_same_long-GateOnly.json.gz)

- [results/v0.2/forensics/drift_same_long-TAIS.json.gz](../results/v0.2/forensics/drift_same_long-TAIS.json.gz)

- [results/v0.2/forensics/drift_same_long.png](../results/v0.2/forensics/drift_same_long.png)

- [results/v0.2/forensics/events.csv](../results/v0.2/forensics/events.csv)

- [results/v0.2/forensics/identifiability.json](../results/v0.2/forensics/identifiability.json)

- [results/v0.2/forensics/manifest.json](../results/v0.2/forensics/manifest.json)

- [results/v0.2/forensics/missing_same_long-AdaptiveSense.json.gz](../results/v0.2/forensics/missing_same_long-AdaptiveSense.json.gz)

- [results/v0.2/forensics/missing_same_long-GateOnly.json.gz](../results/v0.2/forensics/missing_same_long-GateOnly.json.gz)

- [results/v0.2/forensics/missing_same_long-TAIS.json.gz](../results/v0.2/forensics/missing_same_long-TAIS.json.gz)

- [results/v0.2/forensics/missing_same_long.png](../results/v0.2/forensics/missing_same_long.png)

- [results/v0.2/forensics/probe_samples.csv](../results/v0.2/forensics/probe_samples.csv)

- [results/v0.2/forensics/range_cross_short-AdaptiveSense.json.gz](../results/v0.2/forensics/range_cross_short-AdaptiveSense.json.gz)

- [results/v0.2/forensics/range_cross_short-GateOnly.json.gz](../results/v0.2/forensics/range_cross_short-GateOnly.json.gz)

- [results/v0.2/forensics/range_cross_short-TAIS.json.gz](../results/v0.2/forensics/range_cross_short-TAIS.json.gz)

- [results/v0.2/forensics/range_cross_short.png](../results/v0.2/forensics/range_cross_short.png)

- [results/v0.2/forensics/range_same_long-AdaptiveSense.json.gz](../results/v0.2/forensics/range_same_long-AdaptiveSense.json.gz)

- [results/v0.2/forensics/range_same_long-GateOnly.json.gz](../results/v0.2/forensics/range_same_long-GateOnly.json.gz)

- [results/v0.2/forensics/range_same_long-TAIS.json.gz](../results/v0.2/forensics/range_same_long-TAIS.json.gz)

- [results/v0.2/forensics/range_same_long.png](../results/v0.2/forensics/range_same_long.png)

- [results/v0.2/forensics/spike_same_short-AdaptiveSense.json.gz](../results/v0.2/forensics/spike_same_short-AdaptiveSense.json.gz)

- [results/v0.2/forensics/spike_same_short-GateOnly.json.gz](../results/v0.2/forensics/spike_same_short-GateOnly.json.gz)

- [results/v0.2/forensics/spike_same_short-TAIS.json.gz](../results/v0.2/forensics/spike_same_short-TAIS.json.gz)

- [results/v0.2/forensics/spike_same_short.png](../results/v0.2/forensics/spike_same_short.png)

- [results/v0.2/forensics/stable_offset_none_long-AdaptiveSense.json.gz](../results/v0.2/forensics/stable_offset_none_long-AdaptiveSense.json.gz)

- [results/v0.2/forensics/stable_offset_none_long-GateOnly.json.gz](../results/v0.2/forensics/stable_offset_none_long-GateOnly.json.gz)

- [results/v0.2/forensics/stable_offset_none_long-TAIS.json.gz](../results/v0.2/forensics/stable_offset_none_long-TAIS.json.gz)

- [results/v0.2/forensics/stable_offset_none_long.png](../results/v0.2/forensics/stable_offset_none_long.png)

- [results/v0.2/forensics/stuck_none_long-AdaptiveSense.json.gz](../results/v0.2/forensics/stuck_none_long-AdaptiveSense.json.gz)

- [results/v0.2/forensics/stuck_none_long-GateOnly.json.gz](../results/v0.2/forensics/stuck_none_long-GateOnly.json.gz)

- [results/v0.2/forensics/stuck_none_long-TAIS.json.gz](../results/v0.2/forensics/stuck_none_long-TAIS.json.gz)

- [results/v0.2/forensics/stuck_none_long.png](../results/v0.2/forensics/stuck_none_long.png)

- [results/v0.2/git-push-failure.txt](../results/v0.2/git-push-failure.txt)

- [results/v0.2/identifiability.log](../results/v0.2/identifiability.log)

- [results/v0.2/integrity-command-initial.log](../results/v0.2/integrity-command-initial.log)

- [results/v0.2/integrity-final.json](../results/v0.2/integrity-final.json)

- [results/v0.2/legacy-matrix-equivalence.json](../results/v0.2/legacy-matrix-equivalence.json)

- [results/v0.2/legacy-tests.log](../results/v0.2/legacy-tests.log)

- [results/v0.2/legacy-verification.log](../results/v0.2/legacy-verification.log)

- [results/v0.2/legacy_source_hashes.json](../results/v0.2/legacy_source_hashes.json)

- [results/v0.2/publication-pretest.log](../results/v0.2/publication-pretest.log)

- [results/v0.2/report-build.log](../results/v0.2/report-build.log)

- [results/v0.2/seed-audit.log](../results/v0.2/seed-audit.log)

- [results/v0.2/seed_audit.json](../results/v0.2/seed_audit.json)

- [results/v0.2/test-run.log](../results/v0.2/test-run.log)

- [results/v0.2/test-summary.log](../results/v0.2/test-summary.log)

- [results/v0.2/test-verification.log](../results/v0.2/test-verification.log)

- [results/v0.2/test/by_fault_type.csv](../results/v0.2/test/by_fault_type.csv)

- [results/v0.2/test/by_information_class.csv](../results/v0.2/test/by_information_class.csv)

- [results/v0.2/test/by_profile.csv](../results/v0.2/test/by_profile.csv)

- [results/v0.2/test/by_relationship.csv](../results/v0.2/test/by_relationship.csv)

- [results/v0.2/test/by_scenario.csv](../results/v0.2/test/by_scenario.csv)

- [results/v0.2/test/confidence_intervals.csv](../results/v0.2/test/confidence_intervals.csv)

- [results/v0.2/test/events.csv](../results/v0.2/test/events.csv)

- [results/v0.2/test/faultfalse_recall.png](../results/v0.2/test/faultfalse_recall.png)

- [results/v0.2/test/manifest.json](../results/v0.2/test/manifest.json)

- [results/v0.2/test/metrics.csv](../results/v0.2/test/metrics.csv)

- [results/v0.2/test/paired_bootstrap.csv](../results/v0.2/test/paired_bootstrap.csv)

- [results/v0.2/test/recall_uploads.png](../results/v0.2/test/recall_uploads.png)

- [results/v0.2/test/summary.csv](../results/v0.2/test/summary.csv)

- [results/v0.2/tests-final.log](../results/v0.2/tests-final.log)

- [results/v0.2/tests-initial.log](../results/v0.2/tests-initial.log)

- [results/v0.2/tests-portable.log](../results/v0.2/tests-portable.log)

- [results/v0.2/validation-run.log](../results/v0.2/validation-run.log)

- [results/v0.2/validation-summary.log](../results/v0.2/validation-summary.log)

- [results/v0.2/validation-verification.log](../results/v0.2/validation-verification.log)

- [results/v0.2/validation/by_fault_type.csv](../results/v0.2/validation/by_fault_type.csv)

- [results/v0.2/validation/by_information_class.csv](../results/v0.2/validation/by_information_class.csv)

- [results/v0.2/validation/by_profile.csv](../results/v0.2/validation/by_profile.csv)

- [results/v0.2/validation/by_relationship.csv](../results/v0.2/validation/by_relationship.csv)

- [results/v0.2/validation/by_scenario.csv](../results/v0.2/validation/by_scenario.csv)

- [results/v0.2/validation/confidence_intervals.csv](../results/v0.2/validation/confidence_intervals.csv)

- [results/v0.2/validation/events.csv](../results/v0.2/validation/events.csv)

- [results/v0.2/validation/faultfalse_recall.png](../results/v0.2/validation/faultfalse_recall.png)

- [results/v0.2/validation/manifest.json](../results/v0.2/validation/manifest.json)

- [results/v0.2/validation/metrics.csv](../results/v0.2/validation/metrics.csv)

- [results/v0.2/validation/paired_bootstrap.csv](../results/v0.2/validation/paired_bootstrap.csv)

- [results/v0.2/validation/recall_uploads.png](../results/v0.2/validation/recall_uploads.png)

- [results/v0.2/validation/summary.csv](../results/v0.2/validation/summary.csv)
