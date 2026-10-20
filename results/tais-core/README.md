# TAIS Core actual integration evidence

Default GateOnly + real SensorTrust C11 + Stateless Binary v1. No new algorithm validation, parameter search, radio/energy or natural-fault claim. All previous NO-GO findings remain.

- [Run commands and input contracts](../../examples/tais-core/README.md).
- [System, actual outcomes, adverse cases and BM-1 review](../../docs/TAIS_CORE_PROTOTYPE.md).
- `acceptance/`: final-code normal, fault+event, known erased-event failure, drift false reports, missed one-second spike, controlled byte-link failures, hand-built CSV and individually flushed JSONL streams; actual TX bytes/RX outputs and source hashes in each journal/manifest/summary.
- `acceptance/standalone-receiver/`: a separate process decoded only the original unimpaired run's TX bytes; does not recover previously lost data.
- `acceptance/normal/terminal.ansi`, `terminal-full.txt`, `terminal-final.txt`: real pseudo-terminal run at `.002` wall seconds per source second. Text exports remove escape codes only; no numbers are edited or fabricated.
- `bm1-review/`: all45 cases, seeds170–199, actual v1 recoding of5400 original runs /191623 uploaded envelopes. All three native Gate points and unfavorable cases remain; TrustLog is a1.0 context comparator, not budget-matched.
- `checks/`: complete local test logs, retained initial failures, historical archive recoding and delivery/source protection checks.

Top-level `normal`, `normal-stream`, `fault-event`, `known-failure`, `drift-failure`, `spike`, `link-failures`, `csv-stream`, `stdin-stream` and `standalone-receiver` are retained development integration probes. They are not additional independent algorithm evidence. The acceptance runs supersede their presentation: the final interface explicitly distinguishes current-sample frame bytes from last-upload frame bytes. No old probe was overwritten. The earliest `normal` smoke preceded new-code hash metadata; it is not the primary acceptance artifact.

Each source row, admitted sample, upload, real frame length/hex and RX decision is separate. Harness transmission IDs exist only in the local journal, not in v1 or receiver state. Source+sample+TX/RX journals include data the input adapter or sender knew; only RX records describe receiver knowledge. Missing or invalid received information is not filled.

Synthetic truth evaluation is offline and applies to sender reports. User CSV/JSONL has no verified truth and no Accuracy/Precision/Recall. The seven-row CSV is explicitly fabricated to exercise the format and recovery; it is not a real sensor dataset. Application payload bytes do not include text journal hex, OS pipe framing, network/radio headers or provisioning; no over-air savings are inferred.

Reproduce into NEW paths using the commands above. The historical review needs the original archived BM-1 run files, whose hashes are pinned by the original public manifest. A fresh clone without that local archive can run the live/CSV/JSONL prototype and full software suite, but cannot claim to have rechecked those original uploads. Existing results refuse overwrite.
