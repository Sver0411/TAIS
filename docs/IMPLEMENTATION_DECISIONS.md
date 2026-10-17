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
