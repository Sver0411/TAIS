# Phase4: bounded robust and risk-aware sampling

Research base c71e621. This study is additive: no old algorithm, C11 upstream,
MA-1 result, paper metric or default is replaced. All performance evidence is
synthetic host replay with ideal local bytes, not field/wireless/energy evidence.

Completed31,680 final runs:20 held-out seeds ×66 cases ×24 methods. Both new
full candidates are NO_GO_DEFAULT under the predeclared conjunctive criteria.
Risk improves F1 versus native A7 but has no Holm-supported F1 superiority over
A5; Robust saves samples with a detection-quality tradeoff. See the complete
[generic results](../../docs/PHASE4_RESULTS_ZH.md), [frozen protocol](../../docs/PHASE4_PROTOCOL.md)
and [algorithm formulas/state diagrams](../../docs/PHASE4_ALGORITHM_DESIGN.md).
Local checks:942 passed,2 existing strict xfails;43,560 raw archive hashes and
three exact deterministic replays verified. The default remains unchanged.
Initial research delivery was local; publication is a separate user-authorized step.

## Evidence map

| Path | Purpose |
| --- | --- |
| `historical-protection.json` | SHA256 of1,521 original files and pinned submodule identities |
| `seed-audit.json` | Accessible config/manifest and trace-directory audit;920–939 final,940/941 engineering |
| `diagnosis/` | Initial retained attribution pass, exact source and correction note |
| `diagnosis-v2/` | Corrected MA-1 diagnostic event table, miss causes and actual timelines;900–919 only |
| `engineering/` | First completed3,168-run engineering pass, exact source snapshots and all initial outputs |
| `engineering-v2/` | Same3,168 runs after numeric timestamp export repair; metrics identical, proper chronological timelines |
| `freeze.json`, `sources/` | Actual effective code/config/protocol/test/analysis snapshots before independent final evaluation |
| `test/manifest.json` | STARTED/COMPLETE, seeds/cases/methods, packages, source base/hash, raw archive and output identities |
| `test/metrics.csv` | Per-seed/scenario/method raw outcome/resource/health/sampling summaries |
| `test/events.csv` | Every truth event for both sender/decoded receiver, including misses and actual report times |
| `test/forensics.csv.gz` | Per-event timing, gap distribution, actual/proxy candidate scope, gate exposure, miss category and receiver match |
| `test/interval_histograms.csv.gz` | Actual inter-acquisition interval counts, not requested schedule counts |
| `test/timelines.csv` | Predeclared representative seed920, three fixed cases, five fixed methods, actual samples/values/budget |
| `test/inputs.csv`, `archives.json` | Shared signal identities and hashes of full local signals/records/counterfactuals/encoded frames |
| `test/analysis/` | Full summaries, seed distributions,136 prespecified corrected tests, default gates and12 PNG/vector-PDF figures |
| `checks/` | Actual contract/regression/engineering/historical/evidence verification logs |

The initial engineering export sorted numeric timestamps lexicographically.
Raw sampling and computed metrics were correct, but timeline/cumulative plotting
was not chronological. That complete pass and figures remain in engineering/;
its Figure03 is not used for conclusions. Numeric sorting and a regression test
were added before the independent final freeze. All3,168 metric rows match the
repaired engineering-v2 set exactly after key ordering. No algorithm parameter
was changed using engineering performance.

## Methods and fairness

24 methods: all16 MA-1 methods plus Robust/Risk×T0/1×U0/1. A0/A1/A3/A5 are the
fixed20 factorial. A2/A4/A6/A7 use unchanged native AdaptiveSense scheduling;
A7=GateOnly+U. Other native Fixed5/20/60,Delta,Variance,GateOnly,JO-SU20/40 are
retained, including their original distinctions. Independent controls+C11 log
health but do not gate. A0 and Fixed20 have the same sample grid but different
native invalid/recovery handling; do not rename them as the same detector.

All66 cases and seeds are shared exactly within each paired run.54 old cases
are unchanged,12 clean-event cases independently cross amplitude/duration/noise.
Report both cohorts, actual sample counts and the artificial mixture's scope.
U changes only emission. T uses exactly old neutral/raw-C11 health semantics.
New samplers alone have20s diagnostic demand, explicit histories, persistence,
cooldown and at most6 actual fast acquisitions in each open-left120s window.
Holding fast samples bounded does not bound all acquisitions or prove energy savings.

Primary detection deadline=min(event-end+5s,onset+120s), same as MA-1.
Sender/receiver TP/FP/FN/P/R/F1 and native-window counts stay separate.
Successful mean/median/P95 latency uses detected events only; restricted loss
uses actual matched delay or120s for a miss over all events. No missed event is
assigned an invented observed delay. Empty no-event quantities remain N/A.

`C_gate` is actual sampled confirmed candidate suppression; `C_exposure` is
unidentified health/reset exposure, not proof of cause. Other native unrecorded
debounce is unknown. Finite-value age holds across null frames and is distinct
from frame age and correctness. Mean-of-run P95 age is not pooled P95. All
actual Binaryv1 frames are encoded/decoded, ideal link only; receiver match
means reconstructed event edge matching, not physical radio delivery.

## Reproduce

Use the pinned environment/submodules and C11 compiler from the root quick start.
Choose a new output basename for each complete replica; raw archives use that name.

```sh
# One independent final-batch replica using the saved source/config freeze:
python scripts/benchmark_phase4.py replicate --out results/scratch/p4-replica-01 --workers 4

# One statistics/12-figure command from SAVED observations, without policy replay:
python scripts/analyze_phase4.py
# For the fresh replica:
python scripts/analyze_phase4.py --root results/scratch/p4-replica-01

# Read-only shipped-evidence / optional full local archives and3 deterministic replays:
python scripts/verify_phase4.py
python scripts/verify_phase4.py --archives --replay
python -m pytest tests/test_phase4_sampling.py -q
```

Initial construction used engineering→freeze→test. The engineering directory
name is centrally configured as engineering-v2; phase directories are exclusive.
Raw records/signals/frames are under ignored results/traces/phase4 and can be
reconstructed by the full batch; they are not silently assumed present in a
fresh clone. The saved CSV/CSV.gz observations suffice to regenerate ALL final
statistics/figures. Historical diagnosis needs actual MA-1 sample archives,
unlike final statistical regeneration. Source/parameter hashes must match the
saved freeze; no silent upgrade to different algorithms or scoring.

Inference clusters whole seeds. Pooled micro estimates and seed-mean effects
are different;95% bootstrap CIs are descriptive, with Holm over136 specified
sign-flip tests under symmetry/exchangeability assumptions. No subset of cases
or successful delays is substituted for all outcomes. Default recommendation
requires every predeclared gate; no automatic default replacement occurs.
Personalized reports are managed outside all Git checkouts and are absent from
this public result namespace.

In Figures01/02/11 each small point is a whole-seed metric; the larger point is
the arithmetic mean of seed metrics, not pooled micro F1. Figure09 intervals
cluster whole seeds over only the balanced12-case supplement. Figure04 compares
actual acquisition opportunities; no interpolation supplies unseen samples.
