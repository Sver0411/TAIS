# Frozen cross-generator campaign (G2)

Protocol: [TAIS_CROSS_GENERATOR_PROTOCOL](../../docs/TAIS_CROSS_GENERATOR_PROTOCOL.md). Algorithm/dependency/parameter freeze is inherited from G1; G2 generator and all formal scoring/analysis semantics were committed before execution in `3f3991aa26cf1ac7f8f8cd0fe188136b0311c9bd`.

- `seed-audit.json`: accessible structured metadata, archive identities, all-ref historical metadata; final700–719 and engineering690/691 were unused. Hundreds of thousands of archive names are represented by count + SHA256 instead of redundant individual rows.
- `selection.json`: source hashes, exact old operating points, engineering metrics digest.
- `smoke/`: engineering checks (2 seeds ×16 cases ×14 methods), not parameter selection.
- `test/`: single formal run,20 ×46 ×14 =12,880 system runs. Separate event and per-episode health records, exact age histograms, compressed-archive manifest, source commit and fingerprints.
- `test/analysis/`: all groups, paired20-seed intervals, actual budget gaps, duration/coverage/masking outcomes, dual-generator direction comparisons. No pooled G1/G2 inference.
- `summary.csv`: overall G2 methods only; G1 remains untouched in `results/tais-paper/`.
- `figures/`: presentation from committed outputs, fixed declared example traces. No smoothing.
- `checks/`: verification, regression and PDF inspection evidence.

The full signal/sample/frame/counterfactual/receiver archives are ignored under `results/traces/tais-transfer/`, enumerated by hash in the manifest and deterministically regenerable. Nonfinite JSON samples use the frozen canonical serializer's null conversion; fault schedule distinguishes invalid NaN from missing None.

Reproduction after installing locked dependencies and editable project:

```sh
.venv/bin/python scripts/reproduce_transfer.py --workers 4
```

This runs causality/injection tests, verifies the committed campaign, reruns all20 seeds in a fresh scratch directory, recalculates paired analysis, validates every archive/frame, and requires byte-identical CSVs. `--check-only` skips the expensive replication. Every-sample C11 baseline variants carry the same full Binary v1 layout; Rao-inspired remains an explicitly incomplete literature adaptation with fixed24°C/45%RH priors. The inherited `payload_bytes` CSV column is a legacy JSON diagnostic, not used for any communication comparison; `binary_v1_bytes` is the authoritative actual frame count. No measured power, field data or real radio link is claimed.
