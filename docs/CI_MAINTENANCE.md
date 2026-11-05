# Historical evidence checks and additive studies

The CI run for commit `1a09fab48887952402e61c68345c10791b7dab9e`
failed in `verify_transfer.py` and `verify_paper_revision.py`. Their broad
`git diff --name-only BASE` guards treated committed MA-1/Phase4 additions as
changes to inherited experimental files. Untracked additions had not appeared
in earlier local checks, so those checks did not establish post-commit CI parity.
The other four workflows passed for that commit.

Both guards now exclude added paths from the historical comparison. Modified,
deleted, renamed and type-changed inherited paths still fail. The existing
byte-exact source locks, evidence digests, manuscript bindings and numerical
consistency checks remain in force. New research files are covered by their own
campaign locks and tests.

This is verifier maintenance, not a new experimental campaign. No algorithms,
frozen configurations, source snapshots, raw results or analysis outputs were
changed. The original 1,521-file protection ledger is preserved byte for byte in
`results/phase4/maintenance/historical-protection-original.json`. Its active
counterpart retains the original hashes for 1,519 files and explicitly delegates
the two verifier replacements to `maintenance/ci-guards.json`, which records
both original and current SHA-256 digests. `verify_phase4.py` checks that these
two sets reconstruct the complete original ledger with no omitted files or
changed original hashes. It permits only these two named replacements and
reports the maintenance count separately from unchanged files. The
59 effective experiment source files retain their original freeze hashes.

Regression tests use a real temporary Git repository containing committed
additions. They also require inherited source, configuration and result changes
to fail for modification, deletion, rename and file-type replacement. Separate
tests ensure that the maintenance ledger cannot exempt runtime files, change
original hashes or accept unexpected replacement content.

Run the checks from the repository root:

```sh
python -m pytest tests/test_historical_guards.py -q
python scripts/verify_paper_revision.py
python scripts/verify_transfer.py
python scripts/verify_ablation.py
python scripts/verify_phase4.py
```

Run `python -m pytest -q` for the full test suite. Existing CI workflows execute
these evidence verifiers and the full regression suite without skipping checks
or rewriting historical evidence.

Local validation of this maintenance change: 975 tests passed with two existing
expected failures; all four evidence verifiers above passed. A fresh G2 smoke
run completed 448 runs and verified 592 archive digests and 55,068 frame
round trips. All 59 frozen experiment source files matched their saved hashes.
