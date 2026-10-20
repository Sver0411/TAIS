# Health diagnostics and C ownership

The pinned C11 implementation remains unchanged. Heuristic health evidence is distinct from environmental truth; direct callers own lifetime and time-range preconditions.

These English notes preserve explanations from PR #2 commit `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` while the linked source is restored byte for byte from `80914638ab1d3d0ccca135a05de76be137779b1a`. They describe existing behavior, not a new implementation or fresh effectiveness evidence.

Related notes: [Core stream contracts](core-stream.md), [Wire protocol and recovery contracts](wire-protocol.md), [Sampling, emission and evidence state](sampling-policies.md), [Synthetic experiments and metric contracts](experiment-evaluation.md), [Frozen source, tool and test contracts](frozen-source-contracts.md).

## `src/tais/trust.py`

[Source](../../src/tais/trust.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Call the pinned SensorTrust C11 implementation through an opaque ctypes context.

The adapter builds a source-hashed shared library under build/ on demand.
Health outputs are heuristic diagnostics, not calibrated fault probabilities;
a stable in-range offset need not receive a dedicated fault flag.

### `Health`

Immutable C11 output: score 0..100, categorical state and fault bitmask.

Flags RANGE/STUCK/SPIKE/DRIFT/MISSING describe diagnostic evidence,
not verified physical causes or environmental event labels.

### `library`

Load and cache the native adapter, compiling it if its source hash is new.

Requires initialized vendor/SensorTrust and a C11 compiler selected by CC
or cc. The three source files determine the cached library name. Compiler
failures propagate; no Python approximation replaces a failed C build.

### `SensorTrust`

Own one native context for one sampled channel; call close() when finished.

No synchronization is supplied for concurrent updates of the same context.

### `SensorTrust.__init__`

Copy configured thresholds into a newly allocated C context.

Invalid C configuration or allocation failure yields ValueError. Native
window parameters count observations; they are not elapsed-time periods.

### `SensorTrust.update`

Advance diagnostics at strictly increasing nonnegative times in seconds.

Finite values become C float; None/nonfinite values pass valid=0 with
a placeholder zero. Timestamps are rounded to uint64 milliseconds.
Callers must keep time in that range and must not update after close().

### `SensorTrust.close`

Free this owned context once; subsequent calls are harmless.

## `src/tais/trust_bridge.c`

[Source](../../src/tais/trust_bridge.c). Restored to the baseline bytes; the explanations below are maintained here.

TAIS-owned ABI shim for the unchanged upstream SensorTrust core.
Python holds an opaque context pointer rather than mirroring the C struct
layout. Each context belongs to one channel; the caller serializes updates.
Health scores/flags are diagnostic evidence, not physical fault truth.

Allocate and initialize an owned context, or return NULL on either failure.
lo/hi/eps/spike use channel measurement units; slope uses the upstream drift
threshold convention (measurement units per second). stuck/drift/missing
are observation-count limits.
Configuration is copied by sensor_trust_init; no caller buffer is retained.

Release a context returned by tais_new. NULL is accepted by free(); the
caller must clear its pointer and must not update or free that context again.

Mutate a live context with one sample. ms is the caller's uint64 millisecond
timestamp; valid=0 marks a missing observation regardless of placeholder value.
All three output pointers must address writable scalar storage. No output
pointer or address of the stack-allocated sample is retained after this call.
