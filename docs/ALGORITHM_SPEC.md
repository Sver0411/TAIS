# TAIS v0.1 executable specification

The implementation is `src/tais/scheduler.py`. This rule policy is a research hypothesis.

## Reuse boundary

`ChangeAnalyzer`, `analyzer_config`, `transition`, `hysteresis_bounds`, `next_rung`, `ladder`, and `confirmations` are imported from the pinned AdaptiveSense submodule without source edits. Each channel has its own ChangeAnalyzer, state and ladder position. Updating with only that channel gives its own deviation/STD/ROC score and debounce; a node-wide maximum is never substituted for another channel's score.

Default score = max(previous-EMA deviation, population STD over 30 s, mean absolute ROC over 10 s) / channel noise floor. EMA tau is 60 s; floors are 0.15 C / 0.8 %RH. Event score >8 for >=10 s is distinct from ALERT entry >=12 (8 with 50% hysteresis). State transition and ladder semantics are exactly upstream primitives. Configured sweep scales stable/active/event thresholds together by 0.75, 1, 1.5; floors and physical truth thresholds do not change.

Original AdaptiveSense is run by its actual AdaptiveScheduler. Its diagnostic-only comparator makes identical decisions; a separate C context logs health. TAIS refactors arbitration per channel, so it is an extension, not a claim of byte-identical node scheduling.

## Health bridge

`trust_bridge.c` allocates an opaque SensorTrust context on the host and calls its real C11 API. Python never reproduces detector equations. Source-content-hashed build output is compiled with C11, warnings as errors, and no fast-math. Each channel uses increasing millisecond timestamps. All upstream dataset fixtures are compared with the original C replay CLI in tests.

Default SensorTrust windows and penalties remain upstream defaults, with configured temperature/humidity ranges and spike thresholds. A health score is a heuristic, not a probability. The first two invalid samples can return HEALTHY because missing_limit=3; TAIS still excludes their values immediately.

## Channel decisions

1. **HEALTHY:** score current sampled finite reading and allow its debounced event and state to request priority. If confirmation is pending from a suspicious excursion, require value persistence against the last sampled pre-candidate reading as well as debounce and confirmation count. An EMA residual alone cannot confirm a returned spike.
2. **DEGRADED, TAIS:** score locally as candidate evidence. If score reaches ALERT entry and is not blocked, start a confirmation episode. Require >=2 sampled observations, >=10 s debounce, and value displacement > event threshold times noise floor relative to pre-candidate reading. Until confirmed, environmental priority is zero and confirmation requests the minimum interval. At 120 s or failed persistence, cancel. A continuously high suspicious score cannot renew confirmation after expiry; it must first drop below entry. Failure of value persistence reseeds this channel's analyzer, removing spike history. Confirmation is observational persistence, not proof of a true physical event.
3. **DEGRADED, GateOnly:** environmental priority and event are suppressed; no confirmation sampling. Its analyzer still receives finite values. This ablation can retain residuals after trust recovers, which results expose.
4. **FAULT / invalid:** environmental score and event are zero; request 60 s diagnostics. On first usable reading after either case, replace that channel's analyzer and ladder state. Seed from the current reading, without comparing it to stale pre-fault history. SensorTrust's own history is never silently reset. Recovery warmup can miss events already in progress.

## Shared cycle and reporting

Choose the minimum required interval across eligible channel ladders, ongoing confirmation and diagnostic requests; clamp to [5,60] s. A faulty channel contributes no node-wide veto. Only current sampled values enter update(t, values). No labels, hidden values or trace references enter the scheduler.

Uploads are application requests on first observation, confirmed event onset, health state **or fault-flag** change, channel scheduler state change, shared interval change, trusted delta >=2 floors, or heartbeat >=60 s. Co-occurring reasons produce one envelope. Healthy numeric delta can request uploads while an event is not yet debounced. Fault/health metadata and environmental active flags are separate fields. An active event's first requested upload is its report onset. Successful wireless delivery is not modeled.

The envelope includes current values, health and environmental flags. Finite faulty values remain visible with their health annotation; they cannot authorize an environmental event by themselves. Byte counts use canonical compact UTF-8 JSON serialization of the actual simulated envelope. They exclude headers, acknowledgements and retries. No energy claim.

Threshold proximity is **not implemented** in v0.1 and is excluded from its hypotheses/results. It remains optional future work; no dummy switch or claimed ablation is supplied.
