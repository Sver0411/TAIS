# Repository and source map

Read [Quick start](QUICKSTART.md) to run the system, [documents](README.md) to choose a research report, [scripts](../scripts/README.md) to choose a command, and [results](../results/README.md) to find its evidence. Paths describe the existing checkout, not a proposed reorganization.

## Directory map

```text
TAIS/
├── README.md                 project home and minimal demo
├── src/
│   ├── tais/                 original policies, Core, codecs and paper controls
│   ├── tais_v02/             separate persistent-candidate research
│   ├── tais_rearm/           separate reference-return repair research
│   └── tais_spatial/         offline spatial pilot; not the Core scheduler
├── examples/tais-core/       actual stream/receiver/viewer entry points
├── configs/                  versioned, experiment-specific frozen settings
├── tests/                    policy, causality, codec and evidence checks
├── vendor/                   pinned AdaptiveSense / SensorTrust submodules
├── scripts/                  campaign, analysis, verification and paper tools
├── docs/                     contracts, protocols, reports and decisions
├── results/                  committed evidence; distinct campaign namespaces
│   ├── traces/               ignored local raw archives
│   └── scratch/              ignored fresh demonstrations / replicas
├── data/                     access note; raw/processed paths are ignored
└── papers/tais/              current manuscript, tables, figures and history
```

`build/`, `.venv/` and caches are generated and ignored. Some real workbooks are outside the repository entirely. Git is the inventory of shipped files; a local directory's existence does not mean a fresh clone contains it.

## Source map

| Need | Start here | Boundary |
| --- | --- | --- |
| Stream input and CLI choices | [run.py](../examples/tais-core/run.py) | Synthetic/CSV/JSONL, fresh output, offline verification |
| Due-time reading, receiver state and local link | [core_stream.py](../src/tais/core_stream.py) | `CoreSender.push` skips unsampled values; `CoreReceiver` consumes decoded frames |
| Original scheduler and GateOnly | [scheduler.py](../src/tais/scheduler.py), [replay.py](../src/tais/replay.py) | GateOnly disables original confirmation; original `TAIS` benchmark name is not the whole current system |
| Real health engine | [trust.py](../src/tais/trust.py), [trust_bridge.c](../src/tais/trust_bridge.c) | ctypes/opaque-context bridge to unchanged SensorTrust C11 |
| JO integration and bounded sampling | [joint_policy.py](../src/tais/joint_policy.py), [joint_sampling.py](../src/tais/joint_sampling.py) | H-layer variants are separate failed research choices |
| Upload U and SU wrappers | [joint_upload.py](../src/tais/joint_upload.py), [su_policy.py](../src/tais/su_policy.py) | U replaces emission decisions; caps 20/30/40 supported by existing API |
| Binary frames and transport auditing | [wire_codec.py](../src/tais/wire_codec.py), [wire_link.py](../src/tais/wire_link.py) | Stateless v1 is Core default; [wire_v2.py](../src/tais/wire_v2.py) is a separate stateful experiment |
| Independent schedules | [paper_baselines.py](../src/tais/paper_baselines.py) | Actual sampled history only; Rao-inspired is not a full paper reproduction |
| Synthetic input construction | [signals.py](../src/tais/signals.py), [transfer_signals.py](../src/tais/transfer_signals.py) | G1/G2 truth definitions differ; generators are not field data |
| Outcome definitions | [metrics.py](../src/tais/metrics.py), [paper_metrics.py](../scripts/paper_metrics.py), [transfer_metrics.py](../scripts/transfer_metrics.py) | Check the campaign before comparing local/sender/receiver or FI counts |

Health and change analysis run on actual samples. Their resulting state determines the next due time and upload decision. The Mermaid loop on the project home follows this causal order; it does not analyze the full source stream before choosing what to sample. A recorded stream demonstrates processed-cycle savings, not physical sensor acquisition control.

## Test and CI map

| Area | Existing checks |
| --- | --- |
| Core inputs, causality, real C11 and receiver | [test_core_stream.py](../tests/test_core_stream.py), [test_prototype.py](../tests/test_prototype.py) |
| Wire bits, validation and stateful recovery | [test_wire_codec.py](../tests/test_wire_codec.py), [test_wire_v2.py](../tests/test_wire_v2.py) |
| JO/SU parity and caps | [test_joint_policy.py](../tests/test_joint_policy.py), [test_su_policy.py](../tests/test_su_policy.py) |
| Independent controls and G2 | [test_paper_baselines.py](../tests/test_paper_baselines.py), [test_transfer_signals.py](../tests/test_transfer_signals.py), [test_transfer_benchmark.py](../tests/test_transfer_benchmark.py) |
| Paper-only qualification | [test_paper_revision.py](../tests/test_paper_revision.py) |
| Separate historical research | `test_v02.py`, `test_rearm.py`, `test_budget_matched.py`, `test_observability.py`, `test_reference_budget.py`, `test_offline_spatial.py` under [tests/](../tests) |

The four existing [GitHub workflows](../.github/workflows) cover full regression/upstream reproduction, G1 evidence plus scratch smoke, G2 evidence plus scratch smoke, and paper-revision checks. CI checkout initializes submodules. Commands and fixed paths stay unchanged by this navigation work, apart from the documented metadata-only allowance below.

## Authority, history and maintenance decisions

The latest paper content is the [major revision](TAIS_PAPER_REVISION_CHANGELOG.md) based on `94a80a1`. Its current [quality review](TAIS_PAPER_QUALITY_REVIEW.md) and [Chinese summary](TAIS_PAPER_SUMMARY_ZH.md) explain the final narrow claims. Original protocols and result files remain authoritative for their own cohort; old maturity ratings/test counts are historical, not live repository status. Reports mentioning a research branch describe where a study ran. They do not mean every strategy is enabled by default.

The navigation snapshot `3fb89be` was based on `docs/tais-paper-major-revision`. The subsequent [main-release audit](MAIN_RELEASE_AUDIT.md) covers the full accumulated change from the old main, rather than just that navigation commit. The release uses the existing integration branch as the PR source and main as the target. Local relative links follow the checked-out version; historical reports keep their original branch and cohort identities. Publication is gated by the final PR's checks and verified merge state, not by this paragraph alone.

The audit found that the old homepage mixed research chronology with setup, the root results index only described v0.1, and the old quick start invoked writers with fixed historical destinations. Navigation now separates current use, frozen cohorts, exploration and NO-GO decisions. No files are moved: frozen manifests, scripts, tests, CI and paper inputs depend on existing paths. `CODEX_HANDOFF.md` is a historical implementation note, not current authorization to develop or push on main.

Updating the root results index requires one narrow compatibility edit in [verify_paper.py](../scripts/verify_paper.py): its pre-paper historical-document allowlist now includes `results/README.md` alongside the already-allowed root `README.md`. The original snapshot/hash inventory remains unchanged; the verifier still lists changed documentation, and every other historical file, algorithm/configuration and result check retains its previous protection. No metric/scoring logic is changed. Do not rerun old one-shot delivery-audit writers to overwrite their records.

The older [results checksum list](../results/SHA256SUMS) likewise binds the previous results index. All 72 other entries match; the navigation file's sole expected mismatch and exact historical-snapshot check are explained in the [results conventions](../results/README.md#files-and-local-only-evidence). The list itself is not rewritten.
