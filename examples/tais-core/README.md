# TAIS core: run the actual stream

Default: **frozen GateOnly, real SensorTrust C11, stateless Binary v1**. No confirmation, ReferenceGate, spatial rule or Wire v2. This is local software integration, not a new superior algorithm, natural-fault validation, LoRaWAN/MQTT system or energy experiment.

From the repository root (Python environment plus `cc`/clang/gcc and initialized pinned submodules):

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation

# Fresh output path required. About 18 wall seconds at this replay speed.
.venv/bin/python examples/tais-core/run.py --scenario missing_cross_long \
  --seed 20 --pace .01 --ui live --verify --out results/scratch/core-live-01

# Inspect the actual received health/event history after the run.
.venv/bin/python examples/tais-core/view_run.py results/scratch/core-live-01 --tail 80

# CSV format example: these seven rows are manually constructed, NOT device data.
.venv/bin/python examples/tais-core/run.py --csv examples/tais-core/example.csv \
  --pace 0 --ui log --out results/scratch/core-csv-01

# One CURRENT JSON row per line; keep the pipe open for continuous input.
# Sender reads only when due; producer acquisition itself is not controlled here.
printf '%s\n' '{"timestamp":0,"temperature":24.0,"humidity":45.0}' \
  '{"timestamp":20,"temperature":24.1,"humidity":45.2}' | \
  .venv/bin/python examples/tais-core/run.py --stdin --pace 0 --ui log \
  --out results/scratch/core-stdin-01

# Controlled byte-link faults: does NOT change sender decisions or add retries.
.venv/bin/python examples/tais-core/run.py --scenario missing_cross_long \
  --pace 0 --ui log --drop-every 7 --corrupt-every 11 --reorder-pairs --verify \
  --out results/scratch/core-link-faults-01
```

Choose any existing scenario with `--scenario`; examples include `clean_none`, `spike_same_long`, `drift_none_long`, `missing_cross_long`, `range_cross_long`. **Known failure: `range_same_long` erases A's true event**; GateOnly correctly excludes the FAULT reading but misses that physical event. `drift_none_long` also exposes false environmental reports. Seed20 is an already-used software demonstration seed, not new independent evidence.

CSV and JSONL require numeric `timestamp` **seconds**, strictly increasing and nonnegative, plus the configured channels. No timezone/date conversion, sorting, interpolation or future fill. Blank CSV cells/null/NaN/inf are invalid measurements and become on-wire null, retaining the frozen health handling; raw CSV strings remain in the source journal. JSONL must use valid JSON and null. Timestamps must fit C11 uint64 milliseconds; supported integer measurements fit signed64. Layout1 is `(temperature,humidity)`,2 temperature only,3 humidity only. Use `--layout 2` or3 for single-channel CSV/JSONL; synthetic demonstrations use the original two-channel configuration.

Temperature uses Celsius and humidity uses %RH, as required by the frozen configuration. No automatic unit inference/conversion is provided. The C11 health score is heuristic, not a calibrated fault probability. Source-file provenance hashes are independent bookkeeping; no hash or truth label enters the scheduler.

`--pace 1` approximates recorded-time playback; `.01` speeds the source clock up100×; `0` runs fast. Processing/terminal overhead adds wall time; no hard real-time guarantee. For live stdin use `--pace 0` and let the producer control arrival. EOF completes, Ctrl-C stops with partial evidence, malformed or nonmonotonic data fails with its partial journal retained. Existing run directories are never overwritten.

The interface separates source time, sender sample time, sender upload time and receiver latest decoded sample/age. Receiver state is retained **with its timestamp/age**, never silently presented as a new measurement after loss. Its last12 transitions are bounded in memory; full source/sample/TX/RX/health-event history is appended and flushed to `journal.jsonl`. `view_run.py` reads that history without replaying a detector. Local sender health is explicitly not receiver knowledge. Health warnings/recovery are heuristic C11 state/flag transitions, not proof of a physical failure or repair.

The scheduler is updated at the first source row at/after its requested due time. For sparse CSVs it cannot manufacture the requested5–10s data. Sample counts mean **processed multi-channel sample cycles**, consistent with original replay; source rows and channel counts are separate. An already-recorded input stream does not demonstrate reduced physical sensor acquisition. A future hardware driver can consult `CoreSender.next_sample`; no such driver is implemented here.

`journal.jsonl` contains real TX hex bytes and their exact lengths, original semantic envelopes, and RX results. Hex is a journal representation; byte counters use binary lengths. `harness_tx_id` exists only for local audit, not in the v1 frame or receiver API. There is no free sequence number, ACK or retransmission. Loss cannot be inferred reliably from v1 alone. Pair reversal is an explicit simulator delay until another frame/EOF, not a measured link model. CRC detects accidental corruption, **not identity or security authentication**. Framing/routing/layout are preprovisioned locally; transport/network/radio headers and schema negotiation are not implemented or claimed as free deployed features.

Each valid received frame is independently decoded. Older valid frames remain in the journal but cannot roll back current state; equal-timestamp duplicates/conflicts do not overwrite state; invalid CRC/version/layout frames are rejected. A fresh receiver can start at any later valid v1 frame. Missing frames are permanently absent unless an external system retransmits them; no receiver guesses health values.

For complete synthetic runs, `--verify` compares the actual sender records and report sequence to unchanged `tais.replay.run(...,'GateOnly',1.0)` **after EOF** and re-encodes every received valid envelope to check exact wire bits. Synthetic truth is evaluated only offline. User CSV/JSONL have no verified labels: truth-dependent metrics remain N/A; extra label-looking columns are not treated as truth. No natural Accuracy/Precision/Recall is invented.

Historical BM-1 review (requires its original local archive; refuses output overwrite):

```sh
.venv/bin/python examples/tais-core/historical_review.py \
  --archive /absolute/path/to/results/traces/budget-matched/test \
  --out results/scratch/core-bm1-review-01
```

This reads all45 frozen scenarios and seeds170–199, checks and actually encodes/decodes archived uploads for TrustLog1 and GateOnly.75/1/1.5. It never runs a scheduler, selects thresholds or creates new validation evidence. The three native Gate operating points are retained. TrustLog is not budget-matched to GateOnly. Paired whole-seed Bootstrap intervals are descriptive historical summaries; other old cohorts/formats are not mixed in.

An independent process can also receive actual v1 frames, without C11 or a scheduler instance:

```sh
# Extract only actual TX bytes from an UNIMPAIRED run, not decoded fields.
.venv/bin/python -c 'import json,sys; [print(e["frame_hex"]) for e in map(json.loads,sys.stdin) if e["kind"]=="tx"]' \
  < results/scratch/core-live-01/journal.jsonl | \
  .venv/bin/python examples/tais-core/receiver.py --out results/scratch/core-rx-01
```

This is a separate ideal pipe replay of transmitted frames, not recovery of previously lost frames. The line-hex consumer can stay open until EOF. Hex/newline are inspection framing, not a claimed production binary transport. For original controlled-loss reception use the original run's `rx` journal entries; do not feed dropped TX frames back and call them recovered.

See [system/evidence report](../../docs/TAIS_CORE_PROTOTYPE.md) and [actual outputs](../../results/tais-core/README.md).
