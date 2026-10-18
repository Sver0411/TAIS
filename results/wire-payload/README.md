# Wire payload v1 engineering outputs

This is a lossless serialization review of the **existing v0.1 historical test archive**, not a new independent algorithm experiment. Protocol, measured findings and commands: [WIRE_PAYLOAD_EXPERIMENT.md](../../docs/WIRE_PAYLOAD_EXPERIMENT.md).

- `test/summary.csv`: every native method/point × JSON/Binary; original metrics, application bytes and frame distributions.
- `test/per_run.csv`: all10,800 runs, original metrics, envelope/binary/health hashes and source archive hashes.
- `test/by_seed.csv`, `by_scenario.csv`: all points and all cases, without favorable filtering.
- `test/comparisons.csv`: encoding-only, same-encoding policy, diagnostic-cost and explicitly mixed-encoding comparisons.
- `test/frame_size_histogram.csv`: exact per-frame distributions.
- `test/bytes_comparison.png`, `.svg`: native1.0 four-policy byte figure.
- `test/verification.json`: aggregate hard invariants and goal verdict.
- `test/manifest.json`: original source/config/archive provenance, frozen codec implementation and output checksums.
- `checks/`: actual local software/upstream logs, environment and original-file protection verification.

Primary TAIS: **12,804,006 → 1,678,512 bytes (−86.8907%)**, unchanged47,694 uploads and76,430 samples. Binary AdaptiveSense is1,455,208 bytes: TAIS remains15.3452% larger under the same encoding. No radio energy or actual network-packet claims.

Source archives are deliberately outside tracked outputs. Default benchmark verifies their frozen hashes, refuses existing output directories, and never runs a scheduler. See the report for safe reconstruction in a separate disposable original-source checkout if needed; never rerun the old experiment writer inside this research checkout to populate historical result paths.
