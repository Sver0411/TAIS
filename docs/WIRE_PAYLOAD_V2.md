# Wire Payload v2: stateful health compression and explicit recovery

## Frozen engineering protocol before implementation/results

Base: `b184240226025d86c5e77a74f124c5c788564613`; branch `research/wire-payload-v2`. No detection/configuration/upstream/OSP/v1 output changes. This reuses all historical seeds20–49 and45 scenarios, with native AS/TrustLog1.0 and GateOnly/TAIS0.75/1/1.5; it is not independent algorithm validation. Main period16, sensitivities8/32 are fixed now, without selecting a winner afterwards.

The full uploaded-stream compressibility audit precedes implementation. TAIS1.0:47,694 uploads;46,344 within-run adjacent pairs,95.8528% identical full health; state/score/flag change rates1.7305%/2.0208%/2.0736% over92,688 comparable channel pairs. Raw health values cost286,164 bytes (6/upload). Changed values alone cost5,399 bytes; independent run initialization needs8,100 more. Optimistic savings272,665 bytes exclude all masks, identifiers, sequence, CRC and recovery. Charging one hypothetical bitmap/upload lowers that optimistic saving to224,971. It is a bound, not v2 results. Empty-health AS has nothing to compress. Audit includes all methods, every scenario, state occupancies and all9 transition counts in `results/wire-payload-v2/audit/`.

### Wire definition, no ACK or delivery assumption

Preprovisioned layouts remain exactly the v1 registry. Device IDs are explicit uint32 (nonzero); boot/session counters explicit uint64 (nonzero, strictly increasing per device); logical sequence is uint32, starts0, never wraps within a session. All use canonical unsigned base128 varints. Provisioning/identity authentication is not implemented. The caller must durably allocate nonreused boot IDs; a new Sender with a reused ID is an unsupported deployment error. Sequence exhaustion fails closed and requires a new session. Encoding advances the locally emitted logical stream, **not acknowledged delivery**; even a locally discarded frame counts as loss. No ACK, retry, reverse link or free LoRaWAN sequence is assumed.

Common frame: `TW` (2bytes), version2 (1), layout (1), control (1), device varint, session varint, sequence varint, payload, CRC32 (4, covering all preceding bytes). Each field is paid on every frame.

KEY: control exactly0x80, payload is a complete unmodified **v1 independent frame**, including its inner CRC. This deliberately preserves v1 as the full snapshot/recovery representation. Double framing/checksums are counted. Frames0,16,32,... are KEY for main period; changing periods never changes upload requests. Sender restart begins a new session with a KEY on the next existing upload.

DELTA: control bit7=0; bits0–3 hold2bits/channel measurement type as v1; bits4–5 contain event-active booleans; bit6 is timestamp type0=uint64-varint/1=binary64. Payload: original timestamp, one health bitmap, original measurements, changed health fields. The health byte uses bits6–7 for **current** presence of each channel; lower bits0–2 and3–5 are state/score/flags changed-field masks. New health entries send all3 fields; removed entries are explicitly absent; unchanged entries borrow only from a complete contiguous previous transmitted envelope. Unknown/reserved bits and inconsistent field masks are invalid. Scores remain exact0–100 integers, flags alluint32 bits, measurements/time exact original numeric types/IEEE754 bits, including negative zero and null. No unuploaded samples are encoder history.

A delta carrying every current health field (including explicitly empty health) is self-contained and may initialize/recover without borrowing cache. The rule applies identically to every method. Otherwise a delta requires a synced cache for the same device/session and immediately preceding sequence. The receiver never infers unchanged health after a gap. A KEY is always self-contained. Receiving a complete new snapshot restores **current** state; it cannot restore lost prior measurements/events.

### Receiver rules

Per configured device, keep newest session, highest valid received sequence, complete last applied health (or no usable cache), and last received frame for duplicate/conflict detection. Parse schema/length/CRC before mutation. A newer session invalidates old dependencies, even if its first received packet is a delta. Older sessions are rejected; duplicates/stale out-of-order packets produce no envelope. Same identity/sequence with different valid content is a conflict and invalidates cache. A forward gap clears the cache before applying any dependent fields. A dependent delta without its complete prior state yields `WAIT_KEYFRAME`, envelope=None. Future keys/self-contained deltas can restore current state. No reorder buffer, inferred backfill, retransmission or silent reuse is implemented. Equal/past sequence frames cannot roll state back.

Receiver restart clears volatile state; subsequent dependent frames wait for a snapshot. Authentic replay rejection across receiver restart would need persisted high-water marks plus authenticated identities; this prototype does not promise it. CRC detects accidental corruption only. Limits:32-bit device,64-bit boot,32-bit sequence, registered layouts, frame boundaries supplied externally; no deployed end-to-end protocol claim.

### Predeclared link experiments

Every archived run is a fresh receiver, sender device1/session1; these are declared one-byte identifiers, not metadata omitted from the budget. Unit tests cover at least3 interleaved devices and nontrivial/max-width identifiers. Each period sees the same original business envelopes and link masks. Profiles, fixed before results:

- `loss0`: no loss, all emitted records must decode exactly.
- `loss1`, `loss5`, `loss10`: nested Bernoulli masks from SHA256 of link seed2026101807, original seed, scenario and upload timestamp; no algorithm labels or future records. Common time opportunities share the mask across policies/periods/formats. These are controlled assumptions, not measured radio rates.
- `burst`: drop original upload indices5–8 and21–24 inclusive in every run where present.
- `sender_restart`: no loss; restart device1 into session2 immediately before existing upload index20, if present. No extra business upload is invented; changed framing costs are counted.
- `receiver_restart`: no loss; erase receiver cache immediately before index20, if present.

All7 profiles ×3 periods ×8 method/points, comparing v1 and v2 on exactly the same delivery schedule. V1 has no cache or application sequence metadata; the simulator knows missing records from its injection log, not from a claimed v1 continuity detector. Random/normal/burst profiles have identical sent bytes because there is no ACK-driven retransmission. Restart cases show their distinct costs. Reorder, duplicate, missing initialization, malformed frames/config, delayed old sessions and reset/interleaving are additional software tests, not fabricated radio observations.

One trace row records each logical sent frame, its bytes/hash/sequence/session/type, injected discard or reception, decoded/wait/recovery outcome for both codecs. Full large event logs are reproducibly generated under ignored `results/traces/wire-payload-v2/`, not mixed with old archives. Versioned summaries/manifests record their SHA256 and rows; a small public excerpt retains examples. Dropped vs received-but-unreconstructed records are separate. Every successfully reconstructed envelope must be bit/type-exact; any wrong complete envelope aborts the benchmark.

Recovery waits start at the first missing/unreconstructed logical record until the next fully reconstructed current record, measured in emitted-frame indices and original application seconds. Report completed episode mean/P95/max, and separately right-censored/end-of-run unresolved episodes; never assign zero delay to unresolved tails. Also report receiver-visible continuity gaps separately from simulator-known physical drops. No backwards reconstruction: all missing business records remain permanently unavailable in this no-retransmission experiment, even after current state recovers.

### Acceptance and cost analysis

Required: loss0 exact reconstruction of every envelope; unchanged sender samples/upload decisions/health/reports/matches; compare every method v1/v2; all initialization, identity/sequence/checksum/periodic refresh bytes paid. Report challenge TAISv2<1,455,208 honestly, main period16 irrespective of sensitivity results. If missed, stop instead of tuning old data. If recovery losses are severe, no overall superiority claim from loss0 savings.

Report full frame distributions and key/delta counts; synchronization metadata; initialization key bytes; actual key minus hypothetical same-record field-change delta size (refresh premium, not a valid alternative budget without snapshots). State-dependent health-only bounds are distinct from actual v2 totals. Uncertainty: paired seed-level differences and deterministic percentile bootstrap95% CIs, clustering all scenarios by original seed (30clusters). Used data remain historical. Protocol overhead sensitivity for longer identifiers is a declared arithmetic cost bound, not a new tuned protocol.

Sender P/R/F1 and original fault/reconstruction metrics remain frozen; link losses do **not** imply receiver P/R/F1 unchanged. No receiver algorithm is implemented/evaluated. Next physical tests would require actual transport framing, identity/session persistence, authentication, link traces and measured radio/current evidence. No energy/packet/airtime claim is made here.

## Actual implementation, results and reproduction

To be filled from executed checks and benchmarks, including negative targets and all recovery losses.
