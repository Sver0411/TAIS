# Non-semantic engineering notes

The formal campaign ran once after commit3f3991a with no semantic/source/parameter changes. All frozen generator, runtime, scoring and analysis fingerprints remain unchanged.

A later strengthening of the read-only verifier compared the root overall summary with the overall subset of the full group CSV. Pandas infers pooled-age columns as integer when all rows are finite and as float when other groups contain N/A. An initial full replica completed all12,880 replays and its analysis, then this new verification assertion rejected the **dtype** difference (`int64` versus `float64`), before final CSV digest comparison. This did not indicate unequal values or a generator/scoring failure.

The verifier now compares with `check_dtype=False, check_exact=True`, while checking count sums and ratios independently. No CSV or original result was rewritten. The successful post-check resumes the already complete replica (`--resume-root`) and revalidates every archive/frame and exact official/replica output digest; no additional simulation trial or tuning is needed. The original reproduction stdout log is retained alongside the resumed verification log/result. Full reproduction from fresh scratch remains the default one-command behavior.

Earlier pre-commit verification correctly refused an uncommitted freeze. LaTeX commands invoked from the wrong working directory failed to locate the root input and were rerun from `papers/tais`; successful final compilation/render evidence binds the actual delivered PDF. Neither issue changed empirical data.
