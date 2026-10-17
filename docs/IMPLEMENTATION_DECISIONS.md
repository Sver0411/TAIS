# Implementation decisions and audit

Audit date: 2026-10-17 (Asia/Shanghai).

- Original checkout: /Users/mac/Documents/AdaptiveSense, clean main at 6e0d086cf14c81d2fb5dba8305e13a7dff2dae3b. It was not on the expected design branch and is left untouched.
- Migrated specification from AdaptiveSense research/tais-design at 6cc40db8f6291a7c28dfd85d23c0467848fc1b6b. Original source remains preserved upstream.
- AdaptiveSense pinned to f7ec30fd4721aa1a7c308f879050a83936e60067; SensorTrust pinned to 2ce98dd043bb01ea99052eda218c68a172499a4c. Both equal remote main at audit; both MIT. Submodules preserve license and history.
- Smart-Agriculture-Edge-AI inspected at 6c28bd612be2bf1618d1b42fb0930b70dafc26ff. Its integration manifest uses older AdaptiveSense 6e0d086 and SensorTrust fad43a4. It is an integration reference, not a dependency or TAIS performance source.
- The old handoff's in-repository implementation and branch-only rules are superseded by the current user instruction. Independent sibling directory, main branch.
- Upstream ChangeAnalyzer returns overall, per-channel scores, debounced event. Never substitute overall for channel scores. Reuse actual scorer and transition/ladder functions.
- Upstream baseline has event threshold 8 and duration 10 s, ALERT entry 8*(1+.5)=12, distinct concepts. STABLE ladder 20/40/60, ACTIVE 15/10/5, ALERT 5. Preserve them.
- SensorTrust STUCK needs 20 valid samples; DRIFT 24-sample slope with 24 consecutive verdicts, slope units/second. Default missing limit 3; the first two invalid samples may still be HEALTHY. TAIS excludes invalid observations immediately regardless of that state. Health is heuristic, not probability.
- Upstream generator build() hardcodes seed 42 plus scenario CRC and exposes no seed argument. Baseline reproduction keeps it unchanged. TAIS uses a separate explicitly seeded generator and upstream physical-unit label_events(). No monkeypatching of the upstream seed.
- Old 244 byte payload was representative firmware telemetry with different contents. TAIS estimates bytes by serializing its own application envelope, shared across methods; neither measure is radio energy.
- Lu et al. arXiv v1 now says accepted IEEE ISSC 2026. Cite accepted manuscript; no proceedings DOI yet verified.

## First implementation validation

Initial TAIS test run: 60 passed, 1 failed (results/prototype-tests-initial.log). A returning isolated spike remained in the change-score history and later produced a false onset. Fixed by reseeding only that channel's analyzer when value persistence fails during confirmation; the regression test is retained. Following run: 61 passed. This was fixed before any held-out evaluation.

No hyperparameter search is performed in v0.1. Threshold multipliers 0.75, 1, 1.5 are all reported. Seeds 0–9 / 10–19 / 20–49 remain unchanged. No seed reduction. Two channels (temperature/humidity) are used for the TAIS fault benchmark; the separately reproduced original benchmark retains all its original channels. The baseline within TAIS uses the same two-channel configuration and identical upstream code. Invalid fields are omitted before upstream update (which has no missing-value contract); TAIS additionally gates them immediately. Logging-only has exactly the same sample/upload decisions, but its health metadata increases its payload size.

Output definitions: local detections use the same channel debounce as AdaptiveSense; reported detections occur at the first upload request during each active episode. Main recall matches reported onsets, not a silently assumed successful radio delivery. Health/fault state changes and environment_active are separate envelope fields. Full reconstruction uses causal zero-order hold over finite samples or requested uploads, against latent signal; errors retain channel units. Untrusted finite readings are retained in this common naive reconstruction. Diagnostic sample counters describe cycles with diagnostic demand; they are not automatically extra cycles. Actual incremental sample cost is the paired TAIS–GateOnly count difference.

The Smart-Agriculture-Edge-AI firmware SensorTrust C source was fetched and compared by SHA-256: `84ff663157edb012af0290cf9f0f1d6400cee382f47ea272e8ec2089e59a2b90`, identical to the selected SensorTrust core. Its integration manifest still records an older full repository SHA; identical core source does not imply identical whole-project experiments.

`configs/experiment.yaml` retains HEALTHY/DEGRADED/FAULT spellings and `rewarm_after_fault: true` as descriptive metadata. They do not redefine the upstream C enum or enable unsafe history reuse. All effective scoring/hysteresis/ladder/upload-delta parameters load from the audited upstream YAML. Sampling limits/heartbeat/confirmation/diagnostics and synthetic interventions are TAIS config values.

## Publication transport

Initial repository/docs/implementation pushes used normal authenticated `gh repo create ... --push` and `git push`. A later Git transport attempt failed with an HTTP/2 framing error; HTTP/1.1 retry could not connect to github.com:443, while api.github.com remained reachable. Used a one-off official Git Data API publisher via `gh api`: create missing blobs, base-tree updates, exact author/committer/message/parents, then non-forcing ref update. Every blob, tree and commit SHA was asserted equal to its existing local Git object before updating main, and the remote ref was read back. No history rewriting or fabricated link. First recovered publication: c1921d151ab7a27e18c533358c1878032fa342ac. See results/publication-transport.json and results/publish-api.log. Remote remains the ordinary public GitHub URL for future cloning/pushing.

The audited fallback is retained as scripts/publish_exact_git_objects.py, with a repository-relative root and explicit destination guard. It uses existing gh authentication and refuses SHA mismatches or non-fast-forward history. It is an optional publication command, not part of experiment execution.

CSV artifacts retain csv.DictWriter's CRLF line endings explicitly through .gitattributes. Git whitespace review treats CR-at-EOL as valid and never rewrites result bytes to silence a check; recorded SHA-256 stays tied to the actual generated artifact.
