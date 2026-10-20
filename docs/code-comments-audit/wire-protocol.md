# Wire protocol and recovery contracts

Stateless v1 snapshots and stateful v2 health deltas provide different continuity requirements. Restoring current state does not recover lost history or establish radio guarantees.

These English notes preserve explanations from PR #2 commit `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` while the linked source is restored byte for byte from `80914638ab1d3d0ccca135a05de76be137779b1a`. They describe existing behavior, not a new implementation or fresh effectiveness evidence.

Related notes: [Core stream contracts](core-stream.md), [Health diagnostics and C ownership](health-diagnostics.md), [Sampling, emission and evidence state](sampling-policies.md), [Synthetic experiments and metric contracts](experiment-evaluation.md), [Frozen source, tool and test contracts](frozen-source-contracts.md).

## `src/tais/wire_codec.py`

[Source](../../src/tais/wire_codec.py). Restored to the baseline bytes; the explanations below are maintained here.

### `_number`

Encode null, binary64 or signed ZigZag integer while preserving numeric type.

Timestamp integers are unsigned and retain caller units; this codec never
rescales seconds to milliseconds. Booleans and nonfinite floats are rejected.

### `encode`

Encode the complete four-field envelope as an independent v1 byte frame.

Channel order is provisioned by layout_id. Values and event booleans must
cover every channel; health may omit channels, distinctly from a null
measurement. Invalid types, ranges or schema raise WireError. len(return)
is the measured application byte cost, excluding real network overhead.

### `_Reader.varint`

Read a bounded canonical unsigned base-128 integer or raise WireError.

Reject redundant high zero groups so one integer has one wire encoding.

### `decode`

Validate framing, schema and CRC, then return a complete business object.

No previous frame or sender object is needed. Reject unknown layouts,
noncanonical integers, truncation and trailing data with WireError. A valid
later snapshot restores only its current state; the format has no sequence
numbers, retransmission or mechanism to reconstruct lost event history.

### Additional invariants

- Two type bits per value; independent masks retain event and health presence.

## `src/tais/wire_link.py`

[Source](../../src/tais/wire_link.py). Restored to the baseline bytes; the explanations below are maintained here.

### `exact`

Compare envelopes recursively, including exact binary64 bit patterns.

### `discarded`

Choose deterministic synthetic losses keyed by scenario, seed and timestamp.

Hash-based profiles do not consume generator randomness or inspect labels;
burst losses use emission indices rather than elapsed-time outages.

### `encode_stream`

Encode already emitted envelopes, optionally restarting before index 20.

This transport study cannot change the original sampling/upload policy.

### `_Waits`

Track unrestored-state episodes with an explicit right-censored EOF tail.

## `src/tais/wire_v2.py`

[Source](../../src/tais/wire_v2.py). Restored to the baseline bytes; the explanations below are maintained here.

### `_delta`

Pack current measurements/events and changed health fields only.

Health presence bits are separate from changed-field bits: an absent
entry removes health, whereas present unchanged fields depend on continuity.
Timestamp values retain v1 numeric types and units; they are not time deltas.

### `Sender.restart`

Start a greater persisted session and force the next emission to be a key.

A receiver cannot infer reboot continuity from sequence wraparound.

### `Sender.encode`

Validate against v1, return one frame and advance local emission history.

A periodic key embeds an intact v1 snapshot. Other frames omit unchanged
health fields, so dropping the returned frame can invalidate later deltas.
Sequence exhaustion raises WireError rather than wrapping.

### `Parsed`

Structurally validated packet independent of any receiver history.

self_contained means all present health fields can be reconstructed without
a predecessor; this can hold for a full-health delta as well as a key.

### `Received`

Receiver outcome; envelope=None means no complete business state was restored.

gap counts missing sequence positions, not lost environmental events.

### `Receiver.reset`

Erase volatile continuity and replay high-water marks for every device.

### `Receiver.receive`

Parse first, then update only the provisioned device continuity cache.

Stale/duplicate packets do not advance applied state. A conflicting sequence
invalidates cached health; after a gap, dependent deltas wait for a
self-contained packet. Recovery restores current state only. Malformed or
unprovisioned packets raise WireError; CRC is not authentication.

### Additional invariants

- Emission continuity, not matching timestamps, authorizes cached health reuse.

## `tests/test_wire_codec.py`

[Source](../../tests/test_wire_codec.py). Restored to the baseline bytes; the explanations below are maintained here.

### `exact`

Assert semantic equality plus numeric type, signed zero and binary64 bit identity.

### `audit_fixture`

Build a tiny archival scoring fixture with explicit episodes and upload intent.

These constructed counts validate the auditor, not field detection quality.

## `tests/test_wire_v2.py`

[Source](../../tests/test_wire_v2.py). Restored to the baseline bytes; the explanations below are maintained here.

### `stream`

Construct emitted envelopes and frames for loss/restart tests, without a live link.
