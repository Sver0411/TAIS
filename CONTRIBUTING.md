# Contributing to TAIS

Start with the [repository map](docs/REPOSITORY_GUIDE.md) and [document index](docs/README.md). Use a separate branch and describe the concrete problem, resulting behavior and checks. Do not treat a historical report or handoff note as permission to change a default or publish on main.

## Preserve reproducibility

- Keep pinned AdaptiveSense and SensorTrust source/licenses unchanged; propose upstream changes in their own projects.
- Do not edit frozen protocols, parameters, truth, result CSVs or fingerprints to make an old experiment pass. New research needs a separate, explicit scope and evidence namespace.
- Preserve failures and NO-GO decisions. Separate software correctness from evidence of effectiveness, and local detections from received event edges.
- Put demonstrations and replicas in fresh `results/scratch/` paths. Keep raw data, full archives, environments, caches and secrets out of Git. See [results conventions](results/README.md#files-and-local-only-evidence).
- Generated paper tables should be changed through their builders, with numerical provenance checks. Template conversion needs another PDF visual review.

## Validate an appropriate scope

```sh
python -m pytest tests/test_core_stream.py tests/test_wire_codec.py -q
git diff --check
```

For code changes, run relevant tests and the full suite when their scope requires it. For paper/provenance changes use the checks in [Quick start](docs/QUICKSTART.md#check-evidence-without-rerunning-campaigns). Do not invoke full research campaigns for a documentation edit. Check local Markdown links, current-branch paths and Mermaid syntax when editing navigation. Existing CI provides regression and small smoke coverage.

## Claims and attribution

All main effectiveness results are synthetic. Real-background exploration, an inspired external method, local application bytes and conditional cost models must retain those labels. Do not claim field reliability, natural-fault ground truth, actual radio energy savings or universal superiority. Follow [third-party notices](THIRD_PARTY_NOTICES.md), the [MIT license](LICENSE) and the [paper submission checklist](docs/TAIS_SUBMISSION_CHECKLIST.md) when reusing or publishing material.
