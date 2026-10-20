# Frozen source, tool and test contracts

Exact byte identity includes comments and docstrings. Keep original locks and assertions intact; maintain explanatory prose outside protected source files.

These English notes preserve explanations from PR #2 commit `89c7c404a4b7132bfae84239ecdd74b3a37c7b6b` while the linked source is restored byte for byte from `80914638ab1d3d0ccca135a05de76be137779b1a`. They describe existing behavior, not a new implementation or fresh effectiveness evidence.

[Per-file protection diagnosis](freeze-diagnosis.csv) records all 92 originally annotated files, their protection sources and the restore/retain decision. Earlier snapshots may differ from main; those records remain unchanged. [Audit and validation](../CODE_COMMENTS_AUDIT.md) distinguishes active checks from older archival identities.

Related notes: [Core stream contracts](core-stream.md), [Health diagnostics and C ownership](health-diagnostics.md), [Wire protocol and recovery contracts](wire-protocol.md), [Sampling, emission and evidence state](sampling-policies.md), [Synthetic experiments and metric contracts](experiment-evaluation.md).

## `conftest.py`

[Source](../../conftest.py). Restored to the baseline bytes; the explanations below are maintained here.

### `pytest_sessionstart`

Ensure the exact provenance commit exists only in shallow GitHub Actions runs.

Ordinary local tests never fetch. A full CI checkout missing this object is
an error; no alternate historical base may silently replace the pinned one.

## `scripts/analyze_budget_matched_results.py`

[Source](../../scripts/analyze_budget_matched_results.py). Restored to the baseline bytes; the explanations below are maintained here.

### `select`

Freeze pairs using development/validation resource fields only, never test outcomes.

Preserve fallback and calibration-qualified status when no pair meets the
declared bands. This writes an exclusive selection, not a validation report.

### `common_delays`

Compare delay only for events matched by both methods, resampling whole seeds.

Conditional delay omits events missed by either method; report those misses
separately rather than interpreting this as unconditional detection speed.

## `scripts/analyze_paper.py`

[Source](../../scripts/analyze_paper.py). Restored to the baseline bytes; the explanations below are maintained here.

### `paired`

Compute descriptive pointwise differences with paired whole-seed resampling.

Recompute ratios from cluster counts; these intervals are unadjusted across
the displayed methods/groups/endpoints and do not establish universal superiority.

### `resource`

Write a dimensionless additive cost sensitivity surface from measured software counts.

Byte cost is the reference unit; sample/fixed-send weights are swept and
processing is assumed equal. Break-even processing is an allowable extra
cost, not measured CPU energy. A real radio need not have linear byte cost.

### `main`

Write summaries/figures and qualify saved budget pairs without reselecting points.

This mutates analysis and root summary files; use separate maintenance
outputs instead of running it against a frozen result directory.

## `scripts/analyze_su.py`

[Source](../../scripts/analyze_su.py). Restored to the baseline bytes; the explanations below are maintained here.

### `select`

Freeze the development-selected balanced candidate, retaining qualification status.

If no candidate meets quality gates, the fallback still receives a balanced
cap for interface continuity. The name is not evidence that gates passed.

### `analysis`

Write all fixed-mode summaries, whole-seed intervals and explicit GO/NO-GO checks.

Receiver metrics and age remain separate from sender outcomes. Common-hit
delay compares only events detected by both methods; misses stay separate.

## `scripts/audit_budget_seeds.py`

[Source](../../scripts/audit_budget_seeds.py). Restored to the baseline bytes; the explanations below are maintained here.

### `extract`

Collect declared seed values recursively from recognized metadata key conventions.

This is an inventory heuristic, not proof that arbitrary opaque logs contain
no seeds; coverage must be read together with the audit file lists.

### `parse_text`

Parse accessible JSON/YAML/CSV metadata and report seed-bearing content.

Unsupported or unparseable text cannot establish an unused random stream.

## `scripts/benchmark_joint_optimization.py`

[Source](../../scripts/benchmark_joint_optimization.py). Restored to the baseline bytes; the explanations below are maintained here.

### `replay`

Run JO senders through CoreSender; delegate other methods to legacy replay.

Always release native health contexts and derive local episodes from sampled
activity. This replay returns sender reports; receiver scoring is separate.

### `metrics`

Encode every requested upload and compute offline sender/cost diagnostics.

Raw C11 health is separated from application trend bit 32. Frame lengths
are actual Binary v1 bytes; age/errors assume ideal delivery on the dense
1-Hz grid. Edge delay here means first subsequent frame time; later SU/paper
metrics additionally require the received signature to preserve the edge.

## `scripts/benchmark_paper.py`

[Source](../../scripts/benchmark_paper.py). Restored to the baseline bytes; the explanations below are maintained here.

### `select_thresholds`

Choose each independent threshold on development micro F1 at cap 40 only.

### `calibrate`

Choose closest development sample totals and retain all native schedule points.

This initial cap-only search is historical; calibrate_bounds records the
subsequent development-only minimum-bound search without test reselection.

### `calibrate_bounds`

Search independent interval bounds on development data and preserve the earlier plan.

Within the 5% development budget band prefer F1, then gap and declared
ties; if infeasible choose closest budget. This does not guarantee matching
on held-out data. Write selected points for a separate pre-test freeze.

### `views`

Return labeled native/decorated/common views without feeding changes into schedules.

+C11 adds raw diagnostics; +C11+U also shares TAIS emission. Common view
shares detector/emission at each schedule actual sample time, isolating
scheduling rather than comparing fully independent end-to-end systems.

### `execute`

Write a fresh phase directory using saved schedules and actual encoded frames.

Formal test requires the committed source/parameter lock byte for byte.
Output overrides redirect artifacts but do not bypass that freeze check.

## `scripts/benchmark_su.py`

[Source](../../scripts/benchmark_su.py). Restored to the baseline bytes; the explanations below are maintained here.

### `build_sender`

Map public research mode names to GateOnly, JO-S or SU sender adapters.

### `receiver_result`

Decode emitted frames independently and report only received false-to-true edges.

Assume ordered ideal delivery and require every frame to update receiver
state. Return a scoring view replacing reports, plus the decoded history;
health/local diagnostics remain the original sampled records.

### `extended_metrics`

Keep sender and decoded-receiver scores separate and check sampled edge delivery.

The first later snapshot must carry the same edge signature; later return
to that state cannot recover a missed intermediate edge. Zero edge delay
is sample-to-upload software delay, not physical event latency. Age counts
seconds since the latest decoded sample timestamp, even for null values.

## `scripts/benchmark_transfer.py`

[Source](../../scripts/benchmark_transfer.py). Restored to the baseline bytes; the explanations below are maintained here.

### `policy`

Expose observed rows only, excluding truth, seed, scenario and hidden process state.

### `inherited`

Require exact byte identity for every G1 pre-test source-lock entry.

Comments/docstrings alter these hashes even when executable behavior matches;
this historical guard intentionally does not accept semantic equivalence.

### `check_freeze`

Require inherited/new source hashes, operating points and committed G2 lock to match.

### `worker`

Run one seed with exact counterfactual identities and independent receiver scoring.

Cache keys include clean observations and event labels, avoiding G1-style
relationship/profile assumptions under independently timed G2 interventions.

### `execute`

Write G2 engineering or held-out outputs under fixed inherited operating points.

Formal test checks the original source freeze. Artifact directories are
exclusive; a new source annotation is not permission to overwrite a campaign.

## `scripts/build_report.py`

[Source](../../scripts/build_report.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Verify recorded metric digests and replace only the report results-marker section.

This is a report writer, not a read-only validator; do not invoke it merely
to inspect historical numbers during maintenance.

## `scripts/diagnose_joint_history.py`

[Source](../../scripts/diagnose_joint_history.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Inspect selected archived BM-1 reports to diagnose JO development bottlenecks.

Runs at import time and writes bottlenecks/upload-reasons outputs relative to
the working directory. These used historical seeds are not new validation.

## `scripts/greenhouse.py`

[Source](../../scripts/greenhouse.py). Restored to the baseline bytes; the explanations below are maintained here.

### `audit`

Write a source audit and optional explicit-mapping fixed-period reconstruction.

Require supplied time format and monotonic unique source timestamps. Never
interpolate within gaps or treat control state as event/fault ground truth.
Reconstruction error compares available observations, not a latent field.

## `scripts/import_joint_csv.py`

[Source](../../scripts/import_joint_csv.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Import explicitly verified numeric-second columns and write a provenance sidecar.

Refuse existing outputs and unsorted/duplicate/nonfinite time. Supplied
time-semantics text records caller evidence; it cannot validate that
evidence automatically. No natural event/fault labels are invented.

## `scripts/offline_spatial.py`

[Source](../../scripts/offline_spatial.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Dispatch preparation, fixed-plan pilot, analysis or gated test-freeze creation.

Freeze requires both development and validation exploration gates; a NO-GO
must not open held-out evaluation. Code hashes include annotation bytes,
so later maintenance does not match the original frozen experiment source.

## `scripts/paper_metrics.py`

[Source](../../scripts/paper_metrics.py). Restored to the baseline bytes; the explanations below are maintained here.

### `metrics`

Add independent receiver matching, edge preservation and pooled age histograms.

Counterfactual receiver reports come from separately decoded clean frames.
No-health methods have unavailable diagnostic metrics rather than implied
zero-error health capability. Event delays condition on detected events.

## `scripts/publish_blocked_branch.py`

[Source](../../scripts/publish_blocked_branch.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Historical exact-object publisher pinned to research/blocked-rearm-fix.

Execution/import performs remote writes with gh authentication. Branch and
object checks protect that target; this is not a generic publishing API.

## `scripts/publish_exact_git_objects.py`

[Source](../../scripts/publish_exact_git_objects.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Historical publisher targeting main through the GitHub Git Data API.

Executing or importing this file can update remote main without a PR. It is
not a generic maintenance upload helper. Object identities and non-forcing
ancestry are checked, but release authorization must come from the caller.

## `scripts/publish_research_branch.py`

[Source](../../scripts/publish_research_branch.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Historical exact-object publisher pinned to research/v0.2-same-channel-recall.

Execution/import performs remote writes with gh authentication. Branch and
object checks protect that target; this is not a generic publishing API.

## `scripts/rearm_run.py`

[Source](../../scripts/rearm_run.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Run the two declared repair suites without overwriting an existing split directory.

Require committed inputs; formal test checks original source/config hashes.
Those byte identities include comments, separately from behavior equivalence.

## `scripts/rearm_verify.py`

[Source](../../scripts/rearm_verify.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Audit exact source/CSV identities and optional archive hashes or representative replays.

The source byte guard runs even when no replay is requested; annotation
changes alone therefore invalidate original-source identity.

## `scripts/run_budget_matched_experiment.py`

[Source](../../scripts/run_budget_matched_experiment.py). Restored to the baseline bytes; the explanations below are maintained here.

### `protect_original_sources`

Require original blob identities and clean pinned submodules before the historical campaign.

This is a byte freeze, not a semantic-equivalence test; comments change its
source identity. Do not weaken it or refresh recorded experiments for maintenance.

### `worker`

Archive one seed policy matrix and score against paired clean observations.

Record independent input/result fingerprints, actual Binary lengths and
sender event matches. TrustLog must preserve the raw baseline schedule.

## `scripts/run_experiments.py`

[Source](../../scripts/run_experiments.py). Restored to the baseline bytes; the explanations below are maintained here.

### `canonical`

Serialize dataclasses and nonfinite observations deterministically for archives.

Nonfinite floats become null; canonical JSON bytes are separate from gzip
container hashes and from actual encoded communication costs.

### `main`

Write the configured split matrix, sampled replays and clean counterfactual scores.

Legacy output paths are reused if present; run in an isolated checkout or
redirect ROOT explicitly for maintenance checks to avoid replacing evidence.
Smoke reduces seeds/cases but retains the same policy interfaces.

## `scripts/summarize_results.py`

[Source](../../scripts/summarize_results.py). Restored to the baseline bytes; the explanations below are maintained here.

### `aggregate`

Sum detection/resource counts by group; undefined recall becomes NaN.

This legacy summary averages per-run MAE/RMSE, unlike later duration-
weighted budget_eval aggregation. Do not silently mix those estimands.

### `paired`

Bootstrap paired per-seed metric differences, retaining scenarios within seeds.

These legacy intervals average seed-level ratios; later paper tools also
report ratios recomputed from pooled counts. Both are descriptive, and
neither treats individual seconds as independent experiments.

## `scripts/transfer_metrics.py`

[Source](../../scripts/transfer_metrics.py). Restored to the baseline bytes; the explanations below are maintained here.

### `diagnostics`

Score any-flag and type-bit fault hits separately on half-open injected episodes.

Stable offset has no supported C11 type bit; a coincident flag is not
correct type identification. Delay is undefined for undetected episodes.

### `event_details`

Attach offline support/overlap and finite sampling opportunities to event rows.

Replacement support identifies lost information, not successful reconstruction
when an unrelated report happens to match an overwritten event label.

### `metrics`

Extend frozen paper scoring with G2 fault/channel and clearing-edge diagnostics.

## `scripts/v02_run.py`

[Source](../../scripts/v02_run.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Write a versioned split matrix with recorded source identities and separate archives.

Require committed executable inputs and exact frozen bytes for final test.
Smoke cannot preview test seeds; existing completed manifests are protected.

## `scripts/v02_verify.py`

[Source](../../scripts/v02_verify.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Verify saved v0.2 bytes and optionally perform one deterministic replay.

Original source hashes include comments/docstrings; preserving experiment
artifacts does not imply the annotated source still has its original hash.

## `scripts/verify_artifacts.py`

[Source](../../scripts/verify_artifacts.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Verify a legacy split, optionally checking archives and replaying one case.

The source check requires original bytes, including comments, for current
TAIS source paths. It is stricter than runtime behavior equivalence and
can fail after source additions or annotation-only maintenance.

## `scripts/verify_independent_reference_budget.py`

[Source](../../scripts/verify_independent_reference_budget.py). Restored to the baseline bytes; the explanations below are maintained here.

### `check_ledger`

Recompute admitted individual reads and exact JSON upload charges from the ledger.

Verify observed values correspond to charged A/B reads and never exceed caps.
No scheduler or physical power model is run during this accounting check.

### `verify_chunk`

Read bounded cached archive chunks and independently recompute offline metrics.

Restore event objects for matching; no online policy is rerun or tuned.

### `history`

Require archived tracked/ignored byte hashes and external raw-file stat signatures.

Source files are included, so comments can fail this guard without changing
experiment data. Preserve the guard as the original identity record.

## `scripts/verify_su.py`

[Source](../../scripts/verify_su.py). Restored to the baseline bytes; the explanations below are maintained here.

### `main`

Check exact frozen sources and archived SU frames/metrics, then write a new proof.

The final proof uses exclusive creation. This archival tool is not a
read-only smoke command and must not overwrite an existing verification.

## `tests/test_offline_spatial.py`

[Source](../../tests/test_offline_spatial.py). Restored to the baseline bytes; the explanations below are maintained here.

### `fake_dataset`

Construct a dense artificial calibration/development cache for engineering tests.

This fixture is not the source workbook and does not establish field coverage.

## `tests/test_paper_baselines.py`

[Source](../../tests/test_paper_baselines.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Engineering fixtures for independent sampled decisions, adapters and actual wire counts.

Used seeds exercise causality and recovery; they are not new held-out evidence.

## `tests/test_prototype.py`

[Source](../../tests/test_prototype.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

Legacy gate engineering regression against pinned upstream behavior and synthetic fixtures.

## `tests/test_reference_budget.py`

[Source](../../tests/test_reference_budget.py). Restored to the baseline bytes; the explanations below are maintained here.

### `fake_scheduler`

Supply deterministic candidate activity to isolate reference-support bookkeeping.

This test double does not replace SensorTrust in production policy execution.

## `tests/test_transfer_benchmark.py`

[Source](../../tests/test_transfer_benchmark.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

G2 engineering parity, hidden-input guards, receiver metrics and exact freeze checks.

The byte-freeze assertion also rejects annotation-only source changes.

## `tests/test_transfer_signals.py`

[Source](../../tests/test_transfer_signals.py). Restored to the baseline bytes; the explanations below are maintained here.

### `Module`

G2 fixture checks separating reproducible process streams, injection and truth support.
