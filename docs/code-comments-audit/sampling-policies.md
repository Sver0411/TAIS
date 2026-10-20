# Sampling, emission and evidence state

Idle caps are not fixed periods. Upload suppression cannot feed back into frozen sampling state. Candidate persistence is sampled evidence rather than a physical-cause proof.

These English notes preserve explanations from PR #2 commit `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` while the linked source is restored byte for byte from `80914638ab1d3d0ccca135a05de76be137779b1a`. They describe existing behavior, not a new implementation or fresh effectiveness evidence.

Related notes: [Core stream contracts](core-stream.md), [Health diagnostics and C ownership](health-diagnostics.md), [Wire protocol and recovery contracts](wire-protocol.md), [Synthetic experiments and metric contracts](experiment-evaluation.md), [Frozen source, tool and test contracts](frozen-source-contracts.md).

## `src/tais/joint_policy.py`

[Source](../../src/tais/joint_policy.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Trend`

Bounded robust sampled-history predictor for the experimental H layer.

Trend suspicion is heuristic ambiguity, not a physical fault diagnosis.
Forecasts use past samples only; missing values erase the fit history.

### `Trend.update`

Return (previous suspicion, current suspicion, causal forecast).

Time is in seconds; configured slope is measurement units per second.
The current value is appended only after fitting the past history.

### `JointPolicy`

Compose GateOnly with bounded rechecks and optional H/U layers.

JO-S disables H and U; JO-HS enables H; JO-Full also replaces emission
with Upload. These historical variants remain available independently
of their experimental performance.

### `JointPolicy.update`

Update the shared gate, then refine interval, event state and emission.

Idle cap is an upper bound, not a fixed period: diagnostic and recheck
requests can be faster. H may suppress smooth-trend event evidence and
sets application bit 32 separately from raw C11 flags in diagnostics.

### `JointSender`

Reuse CoreSender framing while exposing experimental JO diagnostics.

### Additional invariants

- JO-S is the sampling-only ancestor used by SU; do not re-enable H here.

## `src/tais/joint_sampling.py`

[Source](../../src/tais/joint_sampling.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Rechecks`

Allow at most three meaningful fast rechecks per 120-second window.

Windows renew lazily at a sampled timestamp; no timer reads hidden data.

### `Rechecks.interval`

Consume one recheck if meaningful; otherwise return no interval override.

Both t and minimum use seconds. The caller combines this request with
its other sampling bounds; this object does not schedule reads itself.

## `src/tais/joint_upload.py`

[Source](../../src/tais/joint_upload.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Upload`

Decide emission from last-sent values, event edges and health state/flags.

Each emitted snapshot still carries the current score; score-only changes
do not force a send. Suppression saves application bytes but can age
ordinary receiver data. No radio energy or delivery model is implied.

### `Upload.decide`

Return send reasons and commit last-sent state only when reasons exist.

Called at actual sample times in seconds. None/nonfinite readings share
explicit null semantics; validity changes force an emission. Deadbands
are twice each channel noise floor in measurement units. The heartbeat
is checked only here, so sparse sampling can postpone its deadline.

### Additional invariants

- Accumulate displacement against the last emission, not the last suppressed sample.

## `src/tais/scheduler.py`

[Source](../../src/tais/scheduler.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Decision`

Sample-time policy output; interval is seconds until the next requested read.

Health is C11 diagnostic metadata, active is detected event state and
onsets are local rising edges. Neither is physical ground truth.
Upload expresses sender intent; it carries no delivery guarantee.

### `Scheduler.__init__`

Allocate per-channel C11 diagnostics and upstream ChangeAnalyzer state.

confirmation=False selects GateOnly. With confirmation enabled, degraded
channels can open bounded persistence candidates. Thresholds and ladders
come from the vendored baseline plus the supplied TAIS configuration.

### `Scheduler.update`

Mutate policy state using only this actual sample at time t in seconds.

Timestamps must be finite, nonnegative and strictly increasing. Missing
or nonfinite values and FAULT channels request diagnostic sampling.
Recovery reseeds the affected analyzer instead of replaying hidden data.
Per-channel requests compete by minimum interval, bounded by configuration;
a faulty channel does not veto a usable channel. Returned upload reasons
refer to this policy, and may later be replaced by an explicit U wrapper.

### Additional invariants

- Recovered values start new evidence; a fault-hidden event cannot be reconstructed.
- Honor the fastest usable/diagnostic request without exceeding configured bounds.

## `src/tais/su_policy.py`

[Source](../../src/tais/su_policy.py). Restored to the baseline bytes; the explanations below are maintained here.

### `SUPolicy`

Wrap frozen JO-S or GateOnly sampling with the common Upload module.

JO-S caps 20/30/40 are maximum idle intervals in seconds, not fixed
periods. The GateOnly variant keeps its original sampling schedule.
H remains disabled and U never feeds back into the underlying scheduler.

### `SUPolicy.update`

Replace only the final upload decision; retain original reasons for audit.

### `SUSender`

CoreSender adapter exposing SU bookkeeping alongside unchanged v1 frames.

## `src/tais_rearm/__init__.py`

[Source](../../src/tais_rearm/__init__.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Minimal reference-return rearm variant; historical policy behavior is otherwise reused.

## `src/tais_rearm/config.py`

[Source](../../src/tais_rearm/config.py). Restored to the baseline bytes; the explanations below are maintained here.

### `load`

Load the repair overlay and preserve its declared split and multiplier grid.

### `suite_config`

Copy configuration with only the named suite synthetic overrides and case list.

## `src/tais_rearm/evidence.py`

[Source](../../src/tais_rearm/evidence.py). Restored to the baseline bytes; the explanations below are maintained here.

### `ReturnedReferenceEvidence`

Clear the legacy latch only on an observed unconfirmed return to its reference.

### `ReturnedReferenceEvidence.step`

Delegate persistence, then synchronize reference-return cancellation with reseeding.

Require a prior PENDING episode and a later finite usable sample. The
cancellation sample itself stays inactive: its old raw debounce must not
be mistaken for a newly confirmed event. Other block/release paths persist.

## `src/tais_rearm/replay.py`

[Source](../../src/tais_rearm/replay.py). Restored to the baseline bytes; the explanations below are maintained here.

### `run`

Use the repair only for V02-Rearm; preserve comparator dispatch and disabled fallback.

The temporary scheduler patch is process-local and requires serial use.

## `src/tais_rearm/scheduler.py`

[Source](../../src/tais_rearm/scheduler.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Scheduler`

Inject the repaired evidence type only while constructing the frozen scheduler.

The scoped class patch is process-local, so construction is not thread-safe.

## `src/tais_v02/evidence.py`

[Source](../../src/tais_v02/evidence.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Episode`

Signed displacement candidate retaining its creation-time reference in native units.

### `Evidence`

One bounded persistence candidate plus a post-cancellation BLOCKED latch.

Persistence is sampled evidence, not proof that a change is environmental.
The legacy latch can remain through health recovery until score falls.

### `Evidence.step`

Return (event, pending, lifecycle actions) and mutate candidate/latch state.

Time uses seconds; threshold is noise-normalized and floor has measurement
units. Missing/FAULT input cancels and clears the latch. A degraded change
can create a candidate whose sign/reference stay fixed. Confirmation needs
sample count, duration and raw detector activity; expiry/return/release
can block recreation. HEALTHY raw activity is admitted only when unblocked.

## `src/tais_v02/scheduler.py`

[Source](../../src/tais_v02/scheduler.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Historical v0.2 scheduler fork with explicit persistence evidence.

Runtime equations retain the legacy scoring, transitions, ladders and C11
components. Later annotation-only maintenance may change source bytes; the
frozen experiment records remain the authority for original source hashes.

### `DecisionV02`

Legacy sampled decision extended with per-channel evidence lifecycle diagnostics.

### `Scheduler`

Replace legacy candidate logic with Evidence and optional faster confirmation reads.

### `Scheduler.update`

Update health/scoring on actual samples, then combine evidence interval requests.

Capture the pre-update EMA reference before scoring. A displacement-return
cancellation reseeds the analyzer; accelerated=False removes the fast
confirmation request but preserves evidence and deadline handling.

### Additional invariants

- Preserve the pre-sample baseline before the scorer updates its EMA.
