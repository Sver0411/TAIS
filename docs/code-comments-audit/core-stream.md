# Core stream contracts

Actual samples flow through health/event decisions, emitted frames and an independently decoded receiver. Local reports do not establish receipt.

These English notes preserve explanations from PR #2 commit `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` while the linked source is restored byte for byte from `80914638ab1d3d0ccca135a05de76be137779b1a`. They describe existing behavior, not a new implementation or fresh effectiveness evidence.

Related notes: [Health diagnostics and C ownership](health-diagnostics.md), [Wire protocol and recovery contracts](wire-protocol.md), [Sampling, emission and evidence state](sampling-policies.md), [Synthetic experiments and metric contracts](experiment-evaluation.md), [Frozen source, tool and test contracts](frozen-source-contracts.md).

## `examples/tais-core/historical_review.py`

[Source](../../examples/tais-core/historical_review.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Audit archived BM-1 encodings and write historical descriptive comparisons.

All selected original seed/scenario rows are retained. GateOnly threshold
points are not resource-matched to TrustLog; no policy is replayed or tuned.
Raw archives must already exist and output directories must be new.

## `examples/tais-core/receiver.py`

[Source](../../examples/tais-core/receiver.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Consume inspection hex lines into a fresh receiver and exclusively write outputs.

Invalid hex text is counted separately from invalid binary frames. No
sender journal or truth is available to reconstruct omitted transitions.

## `examples/tais-core/run.py`

[Source](../../examples/tais-core/run.py). Restored to the baseline bytes; the explanations below are maintained here.

### `csv_rows`

Yield parsed rows plus original CSV line provenance without sorting or filling.

Numeric seconds and all configured channel columns are required. Blank/null
cells become None; parsing errors identify the source line. Sender-side
validation subsequently enforces time ordering and sampled value constraints.

### `stdin_rows`

Yield one current JSON object and its line number, rejecting nonfinite JSON tokens.

Do not infer event/fault labels from user-provided stream fields.

### `evaluation`

Score synthetic sender reports after EOF; never called for unlabeled user data.

Any C11 flag during an injected fault is a diagnostic hit, not type proof.
Receiver event performance must be computed independently from decoded frames.

### `main`

Run the selected sender, local byte link and receiver, writing an exclusive journal.

Synthetic truth is confined to optional offline evaluation/verification.
CSV/JSONL streams retain unknown truth metrics. Pace changes wall time only;
source timestamps drive scheduling. Always flush held frames and close C
contexts; failures are retained in the journal and summary.

### Additional invariants

- balanced is the saved candidate (currently SU30), not a claim its quality gate passed.
- SU40 remains available via SUSender/API and benchmarks, not a separate CLI choice.

## `examples/tais-core/verify_delivery.py`

[Source](../../examples/tais-core/verify_delivery.py). Restored to the baseline bytes; the explanations below are maintained here.

### `verify_run`

Recompute recorded frames, byte totals and receiver outcomes from a saved journal.

Require the exact source bytes recorded by that run, including comments.
A source-hash mismatch is a provenance difference, not a metric comparison.

### `protect`

Compare inherited tracked blobs, vendor commits and local archives byte for byte.

This historical freeze deliberately rejects annotation-only source edits too;
it does not distinguish source equivalence from original source identity.

## `examples/tais-core/view_run.py`

[Source](../../examples/tais-core/view_run.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Read a bounded tail of recorded receiver transitions without replaying the policy.

## `src/tais/core_stream.py`

[Source](../../src/tais/core_stream.py). Restored to the baseline bytes; the explanations below are maintained here.

### `timestamp`

Validate source time in seconds against the C11 millisecond range.

Reject booleans, nonfinite values and negatives; ordering is checked by push().

### `CoreSender.push`

Consume one strictly increasing source row; return None before sampling is due.

Only timestamps are read on skipped rows. On a sampled row, update health
and event state, then optionally encode a complete Binary v1 snapshot.
The result contains the local record, first-upload reports and optional
frame/envelope; these local reports do not prove receiver delivery.
Sparse inputs use the first row at or after the deadline, without filling.
Invalid time or unsupported measurement types raise ValueError.

### `CoreSender.close`

Release owned C health contexts; safe to call repeatedly.

### `CoreReceiver.receive`

Decode a frame and apply it only if its timestamp advances receiver state.

Return status, decoded envelope and sampled state transitions. Invalid
frames produce an error result; stale, duplicate or conflicting frames
never roll back latest. A new snapshot restores current state only,
not intermediate events lost in transit. Score-only changes are retained
in latest but are not entries in the bounded transition timeline.

### `LocalLink.send`

Count an emission and apply configured loss, corruption or pair reversal.

Deliveries call the receiver and emit journal records synchronously.
There is no acknowledgement, retry or feedback into the sampling policy.

### `LocalLink.flush`

Deliver the held tail frame after pair reversal at end of input.
