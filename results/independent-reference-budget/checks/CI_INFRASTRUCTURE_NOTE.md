# Post-experiment CI history prerequisite

The first push workflow at `fe032a4a09542e35021a4ec0486af4f0cb697f12` failed:
[run 39196825553](https://github.com/Sver0411/TAIS/actions/runs/39196825553).
Actual result: **608 passed, 1 failed, 2 expected failures**; the baseline and smoke steps were skipped, not passed. Full failure output is retained in `ci-first-failure.log`.

The 87-case old-seed-20 integration fixture calls the frozen `fingerprints()` function, which enumerates the provenance tree at `89aa8341181aa42791f9a4de80739bb7c10fa9e5`. The unchanged Actions checkout uses depth 1, so that commit's tree was unavailable. It raised `fatal: not a tree object` before the fixture could perform its fingerprint check. The local pre-experiment full checkout passed all 609 tests.

A new root `conftest.py` provides this missing **test environment prerequisite only**: inside GitHub Actions, if the exact commit is absent and the checkout is shallow, fetch that fixed SHA with depth 1 and verify its presence. No branch is moved; no alternate SHA or fallback fingerprint is allowed. Ordinary local tests perform no network operation. A missing commit in a full CI checkout fails explicitly. Fetch failure remains a failure, not a skip.

The existing workflow, frozen test assertions, runner, generator, C11 implementation, policy, labels, metric and statistical code, configuration, caps and calibration/final locks are unchanged. This is not a policy/generator/label/protocol/statistical correction; the affected operation is Git-object availability in CI. Final seeds are not rerun. All frozen outputs retain their original hashes and the first failure is preserved. Independent verification previously recomputed all 46,980 final rows from 87,300 artifacts. The prior confirmation and current reference NO-GO decisions remain unchanged.

Validation after the setup addition: a real depth-1 temporary clone initially lacked the base commit, successfully fetched exactly that SHA, left every branch ref unchanged, and made the second setup call a no-op (`ci-shallow-clone-check.log`). The full local suite again passed **609 tests, 2 unchanged strict xfails, 0 failures in 72.95s** (`pytest-after-ci-setup.txt`). A second full-byte historical check still passed for 657 original files and 236,199 old ignored files, both upstreams and external raw-file stat signatures (`post-ci-setup-history.json`). All frozen source/cap/calibration hashes and the original report SHA remain unchanged. Only new infrastructure/evidence files are added.
