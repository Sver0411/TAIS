# TAIS — Trust-Aware Importance Scheduler

**A reproducible Python research prototype using the real SensorTrust C11 core.**

Working title: **Trust-Gated Event-Aware Adaptive Sampling under Sensor Faults for Resource-Constrained Agricultural IoT**.

## Offline spatial pilot (separate research branch)

**这是基于真实温室背景和受控干预的离线探索性实验，不是实际在线 LoRaWAN 系统或自然故障诊断的确认性验证。**

The independent `tais_spatial` prototype uses the pinned LoRaWAN Greenhouse-1 workbook, an explicitly assumed reception clock, fixed polling, controlled interventions, and four history/spatial/null controls. It does not change the existing TAIS schedulers. The [pilot protocol](docs/OFFLINE_SPATIAL_PILOT_PROTOCOL.md) and [results/reproduction](results/offline-spatial-pilot/README.md) describe the data governance, all alignment assumptions, costs and limitations. Earlier [formal online NO-GO decisions](docs/REAL_DATA_EXPERIMENT_PREREGISTRATION.md) remain in force. Raw workbooks and full provenance ledgers stay outside Git.

**Held-out coverage failed (target 25.89%, reference quorum 24.12%; both below the predefined 50% gate).** The [actual report](docs/OFFLINE_SPATIAL_PILOT_REPORT.md) retains all outputs, local-event harms, null-control comparisons and added reference costs; this pilot provides no qualified independent evidence of effectiveness.

When one agricultural IoT sensor becomes unreliable, can health-aware scheduling reduce false environmental reports while retaining real events on healthy channels and controlling sampling/application-upload costs? TAIS investigates this question with independent environmental and fault labels. Effectiveness is a hypothesis tested by the results, not assumed by the design.

## BLOCKED rearm repair research branch

The optional `V02-Rearm` strategy fixes cancellation/reset synchronization after an observed reference return. [Design](docs/BLOCKED_REARM_FIX.md), [independent interpretation](docs/BLOCKED_REARM_INTERPRETATION.md), [complete results](docs/BLOCKED_REARM_REPORT.md), and [reproduction](docs/BLOCKED_REARM_REPRODUCIBILITY.md). Final seeds120–149:19,890 runs; full tests192 passed/2 strict expected failures. At multiplier1, main recall450/900→454/900 (difference95% CI includes zero), while deliberately aligned spike-recovery same-channel recall0/60→60/60. Other multipliers can increase false reports. The repair restores a specific v0.1 capability; it does not improve actual same-channel fault/event overlap. Frozen v0.1/v0.2 code/results remain unchanged; no automatic merge.

## v0.2 research branch

The [v0.2 failure analysis](docs/FAILURE_ANALYSIS_V0.1.md), [preimplementation design](docs/V02_DESIGN.md), [pretest review](docs/V02_PRETEST_REVIEW.md), [new report](docs/RESEARCH_REPORT_V0.2.md) and [reproduction record](docs/V02_REPRODUCIBILITY.md) are independent additions. The original [v0.1 report](docs/RESEARCH_REPORT.md), algorithms and result artifacts remain accessible and unchanged.

V0.2 tests one bounded persistent candidate policy and a passive scheduling ablation. All operating points are retained; effectiveness is judged from fresh seeds50–99 after a source/config freeze. See [v0.2 results and safe regeneration commands](results/v0.2/README.md). Fresh final tests show a small, late same-channel gain only at multiplier.75; original thresholds show no same-channel gain, and a blocked-rearm failure remains. This is a conditional research result with extra costs. See the full report for all points and confidence intervals.

## Quick start

Reference environment: Python 3.14.7, macOS arm64, Apple Clang 17. A C11 compiler (`cc`, Clang or GCC) is required. No hardware or credentials are needed after cloning the public sources.

```bash
git clone --recurse-submodules https://github.com/Sver0411/TAIS.git
cd TAIS
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-build-isolation
python -m pytest -q
python scripts/run_experiments.py --split development --smoke
python scripts/summarize_results.py --split development-smoke
```

The lock records the tested Python 3.14 environment; older Python versions may need compatible dependency resolution with `pip install -e .` and are not claimed as verified. Scripts and pytest explicitly locate checkout source. On macOS, hidden editable `.pth` files can prevent interactive imports; see [validation history](docs/VALIDATION_HISTORY.md).

Full reproduction, without changing configuration or selecting a favorable point:

```bash
python scripts/reproduce_baseline.py
python scripts/run_experiments.py --split development
python scripts/run_experiments.py --split validation
python scripts/run_experiments.py --split test
python scripts/summarize_results.py --split development
python scripts/summarize_results.py --split validation
python scripts/summarize_results.py --split test
```

Upstream reproduction runs tests/generation/analysis in temporary copies; vendored source and historical results stay unchanged. Full synthetic execution retains all 50 seeds and all 45 scenarios, with 13 operating points each (29,250 scored runs). Allow tens of minutes and several hundred MB of local trace storage; manifests enumerate each trace hash. Signals/labels and sampled decisions are regenerated under ignored `results/traces/`. Committed CSVs, plots, configuration, logs and manifests are the reviewable evidence.

## Implementation and evidence

- Per-channel health and change history; healthy-channel priority cannot be vetoed by another channel's fault.
- Actual pinned AdaptiveSense scorer, hysteresis, ladder primitives and original scheduler baseline.
- Actual pinned SensorTrust C11 through a small opaque-context ctypes adapter; comparison against its original C replay CLI on every upstream dataset fixture.
- Bounded suspicious-reading confirmation, diagnostic sampling, explicit recovery reseeding, health/flag changes and heartbeat uploads.
- Independent latent, noisy and faulted streams; physical-unit event labels and scheduled fault labels; no hidden/future observations in scheduler inputs.
- Fixed 5/10/20/40/60 s, unchanged AdaptiveSense, diagnostic-only trust logging, GateOnly and full TAIS; all three threshold multipliers are reported.
- Channel-aware report matching, local detection counts, false reports, fault attribution, latency, samples, uploads, serialized payload estimates, causal reconstruction and fault diagnosis metrics. Whole-seed paired bootstrap confidence intervals and upload/recall plots.

See [results and actual run status](results/README.md), [research report](docs/RESEARCH_REPORT.md), [protocol](docs/EXPERIMENT_PROTOCOL.md), [algorithm contract](docs/ALGORITHM_SPEC.md), [implementation audit](docs/IMPLEMENTATION_DECISIONS.md) and [validation history](docs/VALIDATION_HISTORY.md). The report is the source for outcome claims.

## Dependencies and attribution

| Dependency | Pinned commit | Use |
| --- | --- | --- |
| [AdaptiveSense](https://github.com/Sver0411/AdaptiveSense) | `f7ec30fd4721aa1a7c308f879050a83936e60067` | Score, state/ladder primitives, baseline and event matcher/physical labels |
| [SensorTrust](https://github.com/Sver0411/SensorTrust) | `2ce98dd043bb01ea99052eda218c68a172499a4c` | Unmodified real C11 health detector |

Both upstream projects and TAIS are MIT licensed. Original licenses and notices remain in submodules. This is an independent sibling repository; AdaptiveSense and SensorTrust are not modified. [Smart-Agriculture-Edge-AI](https://github.com/Sver0411/Smart-Agriculture-Edge-AI) was inspected as an eventual integration reference, not a TAIS dependency or source of performance results. Academic references are in [related work](docs/RELATED_WORK.md) and [BibTeX](references.bib).

## Main limitations

Simulation does not establish field reliability, radio delivery or energy savings. SensorTrust health is heuristic, not a calibrated probability. Valid stable offsets and same-channel event/fault overlap remain ambiguous. Confirmation can cost samples and still miss short events. Reported application requests do not establish successful transport. Diagnostic-demand counts are not automatically additional samples. The synthetic benchmark uses two channels and jointly varied profiles; it is not a complete agriculture fault model.

The [earlier Hull access note](data/README.md) preserves a historical failed download. The subsequent [C0 intake](docs/REAL_DATA_INTAKE_AUDIT.md) obtained the files, but [C1](docs/REAL_DATA_EXPERIMENT_PREREGISTRATION.md) retained formal online NO-GO because date/window semantics remain unresolved. The separate offline pilot uses LoRaWAN Greenhouse-1 under declared proxy-clock assumptions. Neither dataset establishes sub-minute detection, natural-fault diagnosis, firmware performance or measured energy savings. See [limitations](docs/LIMITATIONS.md).

To verify recorded hashes and one fresh held-out replay after full reproduction:

```bash
python scripts/verify_artifacts.py --split test --traces --replay-one
```

After all three summary commands, regenerate the report tables with `python scripts/build_report.py`.
