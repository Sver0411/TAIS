# Synthetic experiments and metric contracts

Observed inputs, hidden signals and intervention labels have separate roles. Counts, matching, attribution, budget qualification and uncertainty follow the named experiment implementation.

These English notes preserve explanations from PR #2 commit `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` while the linked source is restored byte for byte from `80914638ab1d3d0ccca135a05de76be137779b1a`. They describe existing behavior, not a new implementation or fresh effectiveness evidence.

Related notes: [Core stream contracts](core-stream.md), [Health diagnostics and C ownership](health-diagnostics.md), [Wire protocol and recovery contracts](wire-protocol.md), [Sampling, emission and evidence state](sampling-policies.md), [Frozen source, tool and test contracts](frozen-source-contracts.md).

## `src/tais/budget_eval.py`

[Source](../../src/tais/budget_eval.py). Restored to the baseline bytes; the explanations below are maintained here.

### `aggregate`

Sum counts first, then compute micro ratios and duration-weighted errors.

Undefined denominators return None. Mean conditional delay excludes misses;
raw sample/upload/byte totals are software counts, not measured energy.

### `paired_rows`

Pair by seed/scenario and reject unequal keys or unequal input fingerprints.

### `paired_bootstrap`

Resample paired whole seeds, keeping all scenarios within each seed together.

Recompute micro ratios from resampled counts. Return TAIS-minus-Gate point
estimates, percentile intervals and the supplied family-size adjustment.
Finite draws only are used for undefined ratios; seconds within a run are
not independent replicates. Results depend on this synthetic seed population.

### `robustness`

Recompute the declared fault/recall rule after deleting each cluster or group.

### `decision`

Apply the saved calibration, test-budget, uncertainty and robustness gates.

A fallback point remains a failed calibration even if a later metric looks
favorable; this function cannot select a new operating point from test truth.

### `absolute_bootstrap`

Compute descriptive whole-seed percentile intervals for one operating point.

These are pointwise intervals without a multiple-comparison correction.

## `src/tais/config.py`

[Source](../../src/tais/config.py). Restored to the baseline bytes; the explanations below are maintained here.

### `load`

Read a pathlib.Path YAML input or the default experiment configuration.

Validate sampling bounds in seconds, confirmation constraints and disjoint
seed partitions; malformed bounds raise ValueError. This is not a full
schema validator and ordinary missing-key errors are allowed to propagate.

### `baseline`

Copy the vendored AdaptiveSense configuration without modifying its files.

Enable configured channels and scale three decision thresholds for an
explicit operating point; noise floors and remaining upstream rules persist.

## `src/tais/metrics.py`

[Source](../../src/tais/metrics.py). Restored to the baseline bytes; the explanations below are maintained here.

### `evaluate`

Score sender reports and local episodes against synthetic trace truth.

Use the upstream one-to-one event matcher and configured tolerance in
seconds. Recall is None without true events; conditional latency excludes
misses. Fault-induced false reports are unmatched reports in a fault/recovery
window absent from the optional clean counterfactual, an operational
attribution rather than proof of physical causation. With no counterfactual,
the comparison list is empty. Stable offset has no dedicated type bit.

Resource counts are sample cycles, requested uploads and recorded JSON
bytes. Reconstruction errors hold sampled/uploaded values offline only;
that reconstruction is not a source of online observations. Duration uses
the generator one-second grid length, not arbitrary irregular CSV time.

## `src/tais/observability_eval.py`

[Source](../../src/tais/observability_eval.py). Restored to the baseline bytes; the explanations below are maintained here.

### `extra_metrics`

Add offline health/event joint outcomes and clean-world cost differences.

Any health flag and a correct fault-type bit are separate outcomes; neither
is an environmental detection. Event support is inclusive, fault support
half-open. Missing counterfactual counts default to zero in this helper.

### `event_rows`

Return per-truth-event sender matching and sampled opportunity diagnostics.

Delays are conditional on matched reports and never fill missed events.

## `src/tais/observability_signals.py`

[Source](../../src/tais/observability_signals.py). Restored to the baseline bytes; the explanations below are maintained here.

### `specification`

Resolve registered fault/event timing offsets without duplicating defaults.

Offsets are seconds from fault onset to planned environmental onset.

### `generate`

Reuse G1 injection and truth rules with only the registered event delay changed.

### `metadata`

Describe offline injection timing and actual truth-window overlap.

Planned event onset may differ from amplitude-qualified scoring onset.

## `src/tais/paper_baselines.py`

[Source](../../src/tais/paper_baselines.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Independent causal sampling decisions with explicit shared experiment adapters.

IndependentSampler does not inherit TAIS gating or JO-SU state machines.
The adapters below reuse fixed replay, ChangeAnalyzer, C11 and optional U;
those decorated versions must not be described as unmodified external systems.
Only sampled (t, values) enter decisions, normalized by public noise floors.
Rao-inspired is an engineering adaptation, not a reproduction of CS+prediction.

### `IndependentSampler`

Bounded Delta, elapsed-time EWMA Variance or Rao-inspired mode switching.

Intervals are seconds, constrained to minimum..cap within 5..60. Delta
uses normalized displacement/rate; Variance uses a 60-second EWMA timescale;
Rao-inspired fits up to four sampled points against configured center bands.
All restore sparse sampling by doubling after sampled stable periods.
No health labels, event labels or unsampled values enter these decisions.

### `IndependentSampler.update`

Advance sampled history and return the next requested interval in seconds.

Reject nonfinite, negative or nonincreasing timestamps. A validity change
can trigger fast sampling; missing values do not update volatility/history.
The 20-second rate normalization, 60-second stability period and band
hysteresis are implementation choices, not claimed Rao paper parameters.

### `episodes`

Reconstruct local active episodes and their first requested-upload reports.

These reports describe emission intent, not independent receiver decoding.

### `run_independent`

Replay one independent schedule; fixed periods delegate to frozen replay.

Read values only when due, run the shared detector on those values and
request every-sample uploads. Resource/receiver accounting is added later.

### Additional invariants

- Separate displacement and rate evidence; dt is actual sampled elapsed time.
- Elapsed-time decay keeps irregular sample gaps meaningful.

## `src/tais/reference_metrics.py`

[Source](../../src/tais/reference_metrics.py). Restored to the baseline bytes; the explanations below are maintained here.

### `evaluate_reference`

Score candidate and reference-supported reports separately under synthetic truth.

ReferenceGate environmental metrics use support; comparators use candidates.
Any health flag is a run-level fault claim for confusion counts, not a
verified fault mechanism. Check ledger equality including both A and B reads.
The received terminology assumes ideal admitted-envelope delivery here.

### `aggregate`

Aggregate support, unresolved coverage, fault claims and resource counts.

Use None for undefined ratios and unsupported comparator-only capabilities;
absence of support must not silently become a successful negative diagnosis.

## `src/tais/reference_policy.py`

[Source](../../src/tais/reference_policy.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Budget`

Admission ledger for individual sensor reads, uploads and exact JSON bytes.

Each A/B read costs one unit. Rejected operations are logged but uncharged;
these hard caps do not model radio packets or actual electrical energy.

### `Budget.read`

Admit and charge one sensor read if capacity remains, then log the decision.

### `Budget.upload`

Return (accepted, proposed JSON size); charge upload/bytes only if admitted.

Even a denied proposal reports its would-be size for accounting diagnostics.

### `run`

Replay hard-budget main sensing with optional sampled reference support.

A reference baseline, candidate read and delayed follow-up must all fit
the same read budget. Missing/flat/inconsistent B leaves the candidate
undecided rather than claiming a physical fault or erasing the candidate.
Only admitted envelopes generate reports; support is a separate label.
The link here is ideal admitted JSON transport, not Binary v1 or radio.

## `src/tais/reference_signals.py`

[Source](../../src/tais/reference_signals.py). Restored to the baseline bytes; the explanations below are maintained here.

### `scenario_specs`

Enumerate the fixed IRB same-quantity reference and stress interventions.

### `equivalence_pairs`

Identify worlds with identical observations but different physical event labels.

### `generate`

Return an IRB trace and offline metadata for main/reference temperature.

Reference B responds to environmental displacement by alpha and has its
own seeded noise and modeled bias/missingness. Alpha=0 matched-ramp twins
deliberately expose nonidentifiability: observations alone cannot decide
which physical cause produced them. Labels never enter ReferenceGate.

## `src/tais/replay.py`

[Source](../../src/tais/replay.py). Restored to the baseline bytes; the explanations below are maintained here.

### `run`

Replay one observed trace through a named policy at actual sample times.

Fixed-N reads at its requested N-second interval and uploads every sample.
AdaptiveSense+TrustLog adds C11 metadata without gating baseline decisions;
TAIS and GateOnly use the trust gate with and without confirmation.
Detectors see sampled usable values only; labels are unused here.
Return local episodes, first-upload reports and sampled records. Reports
are sender intentions, not decoded receiver edges. payload_bytes counts
serialized JSON envelope bytes; Binary studies encode records separately.

## `src/tais/signals.py`

[Source](../../src/tais/signals.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Trace`

Offline experiment container separating latent, noisy and observed streams.

latent includes environmental interventions, noisy adds observation noise,
and observed additionally applies faults. events/faults are scoring labels
and must not enter online policy decisions.

### `Fault`

Synthetic channel intervention on the half-open interval [start_s, end_s).

### `generate`

Build the G1 one-second grid and return observations plus separate truth.

Noise and fault timing have separate seeded RNGs. Event timing is prescribed
relative to fault start, so this is not independent natural event timing.
Upstream label_events scores the driven physical deviation rather than
detector output; its inclusive event endpoints differ from fault support.
Fault replacement affects observed only, preserving noisy for counterfactuals.

## `src/tais/transfer_signals.py`

[Source](../../src/tais/transfer_signals.py). Restored to the baseline bytes; the explanations below are maintained here.

### `stream`

Derive an independent reproducible RNG stream from the seed and stream name.

### `generate`

Build G2 mean-reverting background, correlated noise, events and faults.

Environment/noise/event/fault RNG names isolate their random draws. Events
have independently placed exogenous support, represented as inclusive
1-Hz truth endpoints [start, end-1]; faults use half-open intervals.
latent includes noise-free events; noisy adds noise; observed applies
fault replacement. Hidden schedules and parameters are offline metadata,
never online inputs. This generator differs from G1 in truth rules as well
as signal dynamics, so comparisons do not isolate a single distribution shift.

## `src/tais_spatial/analysis.py`

[Source](../../src/tais_spatial/analysis.py). Restored to the baseline bytes; the explanations below are maintained here.

### `bootstrap`

Return a mean and percentile interval over independent date-level differences.

### `summarize`

Write fixed-plan summaries and date-cluster paired comparisons, then plot.

Average paired node differences within each date before bootstrap sampling.
The coverage gate admits informative exploration, including harm; passing
it alone is not evidence of superiority. Refuse an existing summary.csv.

### `update_checksums`

Refresh this output directory manifest after artifact generation.

This mutates the manifest; it is not a read-only historical verifier.

## `src/tais_spatial/data.py`

[Source](../../src/tais_spatial/data.py). Restored to the baseline bytes; the explanations below are maintained here.

### `proxy_timestamp`

Parse workbook date/time into rounded seconds on a naive proxy axis.

This deterministic axis has no verified acquisition/arrival-time semantics;
no timezone inference or interpolation is performed.

### `prepare`

Verify the source hash and exclusively create a provenance ledger/cache.

Keep every nonempty source row in the ledger, including unusable cells.
Sort cache rows stably on the explicit proxy axis and quarantine all values
sharing duplicate timestamps. Invalid measurements become NaN; no gaps are
filled. Existing output directories and substituted workbooks are rejected.

### `Dataset`

Verified cached source rows queried under explicit reception-clock assumptions.

### `Dataset.open`

Verify workbook identity and cache bytes before loading non-pickle arrays.

### `Dataset.asof`

Return (value, source row, assumed arrival) for past available rows only.

query/max_age/shift use proxy seconds; shift changes assumed availability.
Rows beyond max_age or preceding the first arrival return NaN/-1/-1.
An available row can itself contain NaN; availability is not measurement
validity. No interpolation or future-row lookup is allowed.

### `Dataset.calibration`

Return per-node finite medians from the declared half-open calibration period.

Fewer than 100 values yields NaN rather than a validation/test-derived fill.

## `src/tais_spatial/interventions.py`

[Source](../../src/tais_spatial/interventions.py). Restored to the baseline bytes; the explanations below are maintained here.

### `schedule`

Describe a controlled intervention on unlabeled real background in proxy seconds.

These labels identify imposed perturbations, not natural field faults/events.

### `apply_target`

Apply synthetic target perturbations on source-row times, preserving NaNs.

local_slow intentionally shares drift-only observations despite a different
physical interpretation; no detector can recover that distinction alone.

### `apply_references`

Apply common events or reference interventions before detector evaluation.

Negative controls omit common-event response; missingness follows query
time while value perturbations use the recorded source-row proxy time.

## `src/tais_spatial/io.py`

[Source](../../src/tais_spatial/io.py). Restored to the baseline bytes; the explanations below are maintained here.

### `gzip_text`

Exclusively create deterministic gzip text with zero mtime and no filename header.

Close all nested streams on context exit; existing files raise FileExistsError.

### `safe_json`

Recursively map nonfinite Python floats to explicit JSON null diagnostics.

## `src/tais_spatial/methods.py`

[Source](../../src/tais_spatial/methods.py). Restored to the baseline bytes; the explanations below are maintained here.

### `trailing_median`

Use past fresh values only; require three finite entries for a reference.

The current sample is excluded to avoid absorbing its own displacement.

### `features`

Build causal displacement, fresh-row jumps and trailing trend evidence.

Repeated cached rows do not become new observations. All trend arrays use
current/past polls only; no intervention labels enter this function.

### `detect`

Emit onset-only reports with sampled hysteresis and optional trend suppression.

Missing/stale samples leave active unchanged. HistoryExtended, Spatial and
NullSpatial choose different trend features; a fresh large jump bypasses
suppression. A report is detector output, not verified physical truth.

## `src/tais_spatial/pilot.py`

[Source](../../src/tais_spatial/pilot.py). Restored to the baseline bytes; the explanations below are maintained here.

### `packet_residual`

Center target/reference values by calibration medians and require a quorum.

Return residual and finite reference count; absent quorum yields NaN.

### `episode_inputs`

Assemble target/reference as-of rows and calibration-only negative controls.

Availability masks are shared across real and null reference conditions.

### `materialize`

Apply label-defined perturbations offline, then clip to declared physical bounds.

Clipping can remove a requested observation opportunity; labels are kept
separate from detector features and are never passed to detect().

### `costs`

Count assumed polling/RPC requests and modeled application bytes.

Reference replies are assumed 36 bytes and event reports 18 bytes. These
are conditional payload assumptions, not encoded Binary frames, measured
wireless traffic, physical fresh reads or measured electrical energy.

### `run_split`

Exclusively write fixed-plan paired interventions, metrics and provenance.

Calibration medians and donors never read held-out values. Smoke is
development-only. Scoring uses controlled window/counterfactual outcomes
on an unlabeled real background; it is not natural event precision.
No adaptive Core runtime, live network or actual energy validation occurs.

## `src/tais_v02/__init__.py`

[Source](../../src/tais_v02/__init__.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Historical v0.2 research package; legacy runtime behavior is reused explicitly.

## `src/tais_v02/config.py`

[Source](../../src/tais_v02/config.py). Restored to the baseline bytes; the explanations below are maintained here.

### `load`

Load the v0.2 overlay, validate time/sample bounds and reject overlapping seed sets.

Return (merged runtime configuration, experiment specification). No file is
rewritten; this interface does not select parameters from experiment outcomes.

## `src/tais_v02/forensics.py`

[Source](../../src/tais_v02/forensics.py). Restored to the baseline bytes; the explanations below are maintained here.

### `inspect_run`

Observe legacy analyzer calls and candidate lifecycle without changing returns.

Return (original replay result, offline evidence). Temporary module patches
are restored on exit and require single-threaded use. Baseline-only methods
are instrumented after replay at their actual sampled times.

## `src/tais_v02/replay.py`

[Source](../../src/tais_v02/replay.py). Restored to the baseline bytes; the explanations below are maintained here.

### `run`

Dispatch V02/V02-Passive through a scoped scheduler-factory patch.

Passive keeps evidence but omits accelerated confirmation. Disabled v0.2
falls back to legacy TAIS; other method names keep their original dispatch.
The process-local patch is unsuitable for concurrent threads.
