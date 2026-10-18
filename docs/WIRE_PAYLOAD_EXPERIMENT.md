# Wire payload v1: lossless application serialization engineering audit

## Frozen scope before measurement

Code base: `f21bc2f0e1d01d0670ce1c1bd4ab5a2aab7e171d`. New branch: `research/wire-payload-v1`, created from that commit while the existing portfolio branch remains preserved. This is a format-layer review of historically used v0.1 test seeds20–49, not new independent algorithm validation. Target: **at least40% fewer TAIS application bytes than its original JSON**, without changing any business field or detection/sampling/upload behavior. A failed round trip invalidates a compression result, irrespective of size.

The actual `src/tais/replay.py` envelope is exactly `timestamp`, `values`, `environment_active`, `health`; each health entry has `score`, `state`, `flags`. Internal `Decision` scores, interval, reasons, confirmation and recovery diagnostics were **not** in that JSON. Existing finite-value sanitation converts missing/nonfinite measurements to `null`; finite faulty values remain present. Original JSON is `json.dumps(...,sort_keys=True,separators=(',',':'),allow_nan=False).encode()`.

## Complete-frame protocol, version1

This is a custom fixed-schema application format, not a claim of CBOR/SenML interoperability or a deployed LoRaWAN transport. Every frame is independently decodable with its preprovisioned layout; it has no preceding-frame or delta state. Integers use canonical unsigned base128 varints (least-significant group first); signed measurements use signed64 zigzag then varint. Fixed-width fields use network byte order.

| Order | Field | Representation |
| --- | --- | --- |
|1|Magic|2bytes, ASCII `TW`|
|2|Version|1byte, exactly1|
|3|Layout ID|1byte;1=(temperature,humidity),2=(temperature),3=(humidity), ordered immutable registry|
|4|Timestamp kind|1byte:0=uint64 varint,1=IEEE754 binary64|
|5|Timestamp|Original nonnegative number, same unit as input; no time scaling or rounding|
|6|Measurement types|1byte,2bits/channel:0=null,1=binary64,2=signed64 integer,3=invalid|
|7|Event active mask|1byte, one boolean per layout channel|
|8|Health present mask|1byte; absent health stays absent, including AdaptiveSense's empty `{}`|
|9|Measurements|Layout order;8bytes/float, canonical zigzag varint/int,0bytes/null|
|10|Health entries|For each present channel:state uint8(HEALTHY0/DEGRADED1/FAULT2),score uint8(0–100),flags canonical uint32 varint|
|11|Integrity check|4byte CRC32 of all preceding bytes, network order|

Valid types are Python `int`/`float`/`None` for measurements, `int`/`float` for time, exact boolean event flags, and exact integer health score/flags. Booleans are not numeric measurements. Finite binary64 values, subnormals and negative zero retain their exact IEEE bits; integers are never coerced through float. Unsupported ranges/types, unknown or extra business fields, invalid masks/states, noncanonical varints, nonfinite on-wire floats, truncation, trailing data, version/layout mismatch and checksum failure are rejected rather than clamped or ignored. The mapping must match configured channel **order and identity**, not merely a channel count. Partial health maps are representable.

Maximum legal frame56bytes (two channels, longest supported integer fields/flags); minimum13bytes (null values, empty health, short integer timestamp). Real two-float/small-flag frames with integer time128–1799 use30bytes without health,36bytes with two health entries. These are size predictions from the field layout, not the benchmark result. Version/layout IDs cost2bytes in every frame; magic adds2, timestamp kind1, three masks3, CRC4. Channel-name dictionaries are preprovisioned, not repeatedly transmitted. The benchmark separately reports the measured size of a canonical JSON layout descriptor and a hypothetical once-per-run provisioning cost; this is not implemented extra network traffic or included in the policy's upload count.

CRC detects accidental corruption; it is not authentication, replay protection, key management or a complete network protocol. A transport must supply frame boundaries. No radio, packet-delivery, airtime, current, energy or region/data-rate conclusion is inferred.

## Predeclared engineering comparison

Read immutable `results/test/manifest.json`, `metrics.csv`, `summary.csv` and the exact archived `results/traces/test/` files. Check source/config version equality with the original source commit, archive SHA-256, original per-record JSON byte count, per-run metrics, and original group totals **before** reporting savings. If an archive is absent or mismatched, stop; do not silently regenerate it into historical results.

Methods: AdaptiveSense, AdaptiveSense+TrustLog, GateOnly, TAIS. Reuse all45scenarios and30testseeds; native AS/TrustLog have only archived multiplier1, while GateOnly/TAIS retain all0.75/1/1.5 points. Do not invent AS runs at other multipliers. Primary comparison uses1.0. Each actual upload is separately encoded/decoded and checked against the original semantic envelope, including float bits, number types, health and active flags. Only bytes change. Empty-health AS stays empty; diagnostics are not stripped from other methods to improve their result.

Report JSON and Binary for every method/point; total bytes, mean/median/P95/min/max frame size, frame-size histograms, upload and sampling counts, event matches/strict false reports, precision/recall/F1, and field-preservation assertions. P95 uses nearest rank, median the usual midpoint of the two central sizes. Counts aggregate the same records, not resampled datasets. Codec savings, same-encoding policy differences and diagnostic metadata costs are separate. The40% criterion is applied to TAIS at its inherited default; other points and unfavorable comparisons are retained.

Event extraction is reconstructed over the frozen sender sample trace, substituting decoded business fields on uploaded records and retaining unchanged internal states at nonuploaded records. Match with the original upstream matcher and tolerance; compare source report/detection lists and counts. This proves sender behavior invariance; it does **not** pretend an uploaded-only receiver gains untransmitted internal samples. Exact equality of the entire received business-envelope stream also implies identical information for any unchanged receiver. Fault-counterfactual metrics remain the original archived values, justified by unchanged observations/health/report decisions; they are not re-estimated with a new counterfactual policy.

No scheduler, detector, matcher, frozen configuration, old CSV/manifest/trace, OSP module or upstream source is edited. New benchmark outputs use an exclusive new directory. Required tests cover valid round trips, float/integer boundaries and signed zero, all health states/flag combinations, null sanitation, multiple layouts, malformed/corrupt frames and configuration mismatch; then run the whole existing software suite.

## Actual results

Results will be filled only after the codec and full engineering audit have actually run. Existing historical counts are reference checks, not new codec measurements.
