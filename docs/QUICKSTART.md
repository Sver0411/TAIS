# Run TAIS locally

This guide runs existing software on new scratch paths. It does not recalibrate policies or replace frozen evidence. For the shortest install command block, start at the [project home](../README.md#quick-start).

## Environment and installation

The reference local environment is Python 3.14.7 on macOS arm64 with Apple Clang 17; GitHub Actions uses Python 3.14 on Ubuntu. `pyproject.toml` declares Python >=3.10, but the exact dependency lock is tested on 3.14, not every declared Python version. Use a checkout with initialized submodules and a writable `build/` directory. The C bridge needs a working `cc` (or set `CC=clang` / `CC=gcc`) and compiles a cached shared library on first use. macOS users need Command Line Tools; Linux users need their distribution's C compiler/development tools. Windows/MSVC is not verified.

```sh
git submodule update --init --recursive
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-build-isolation
python -m pytest tests/test_core_stream.py tests/test_wire_codec.py -q
```

Run all commands below from the repository root with this environment active. Scripts locate checkout source themselves. Keep the checkout and pinned submodules together: the package reads repository configuration and upstream code, so this is not a standalone wheel deployment.

## Minimal end-to-end run

```sh
python examples/tais-core/run.py --scenario missing_cross_long --seed 20 \
  --pace 0 --ui quiet --verify --out results/scratch/quickstart-01
python examples/tais-core/view_run.py results/scratch/quickstart-01 --tail 12
```

The first command runs the original synthetic demonstration through the actual sender, Binary v1 bytes and independent local receiver. `--verify` compares the sender's samples/reports with its frozen replay after EOF and checks encoded/decoded bytes. It is not a test on new independent seeds. Expect `status: COMPLETE`, true selected-policy parity, positive sample/upload counts and a received history.

| File in the new run directory | Meaning |
| --- | --- |
| `manifest.json` | Policy, input provenance, configuration/source hashes and link assumptions |
| `summary.json` | Sender/receiver counters, offline synthetic metrics and verification |
| `journal.jsonl` | Source rows, actual sampled decisions, TX bytes and RX history |

Output paths must not exist. Pick another suffix instead of deleting evidence to rerun. All suggested paths are under ignored `results/scratch/`; no historical result is overwritten. `--pace .01 --ui live` gives a fast terminal display (about 18 source-clock replay seconds plus overhead); `--pace 0` runs as fast as processing permits. UI logs and frame hex are inspection output, not additional wire bytes.

## Mode selection

Append the policy flags to `run.py`; the following examples use different fresh paths:

```sh
python examples/tais-core/run.py --policy gateonly-u \
  --scenario missing_cross_long --seed 20 --pace 0 --ui quiet --verify \
  --out results/scratch/quickstart-gate-u-01
python examples/tais-core/run.py --policy tais-su --su-mode high \
  --scenario clean_short --seed 20 --pace 0 --ui quiet --verify \
  --out results/scratch/quickstart-su20-01
python examples/tais-core/run.py --policy tais-su --su-mode balanced \
  --scenario clean_short --seed 20 --pace 0 --ui quiet --verify \
  --out results/scratch/quickstart-su30-01
```

`high` is SU20. The committed [SU selection](../results/tais-su/selection.json) has `balanced_cap: 30` and `development_quality_qualified: false`; `balanced` is a historical candidate name, not a quality endorsement. SU30/SU40 lose detections relative to SU20 in SU-1. GateOnly remains default. See [SU results](TAIS_SU_RESULTS.md) for all three caps and adverse cases.

**SU40 has no dedicated Core CLI preset.** Its existing [SUSender API](../src/tais/su_policy.py) accepts `cap=40`; this minimal API replay exercises the same sender and receiver without adding a mode or changing a parameter:

```sh
python - <<'PY'
from tais.config import load
from tais.signals import generate
from tais.su_policy import SUSender
from tais.core_stream import CoreReceiver

cfg = load()
sender, receiver = SUSender(cfg, cap=40), CoreReceiver()
try:
    for row in generate(cfg, 20, 'clean_short').observed:
        step = sender.push(row)
        if step is not None and step['frame'] is not None:
            receiver.receive(step['frame'])
    print('SU40 sender:', dict(sender.counts))
    print('SU40 receiver:', dict(receiver.counts))
finally:
    sender.close()
PY
```

This snippet prints counters; it does not create a journal or new validation result. For archived SU40 comparisons use the [existing results](../results/tais-su/README.md). `--policy tais-jo --joint-variant JO-S` also exists for JO engineering; JO-HS/JO-Full are retained research variants whose health-layer/default-replacement findings are NO-GO, not recommended replacements. Fixed, Delta, Variance and Rao-inspired schedules are exposed through the [paper benchmark](../scripts/README.md#experiment-runners), not `run.py` policy choices.

## Your own data and known failure demonstrations

```sh
python examples/tais-core/run.py --csv examples/tais-core/example.csv \
  --pace 0 --ui quiet --out results/scratch/quickstart-csv-01
```

The seven example rows are hand-built, not device measurements. Inputs require strictly increasing, nonnegative numeric `timestamp` seconds, temperature in Celsius and humidity in %RH. Missing values remain invalid/null; there is no sorting, interpolation, unit inference or invented timeline. CSV/JSONL without verified labels have N/A truth metrics; do not add `--verify`, which requires the built-in synthetic trace. See the [full input and standalone receiver contract](../examples/tais-core/README.md) for `--stdin`, single-channel layouts and actual-byte pipe replay.

Use `range_same_long` to inspect a fault-erased event or `drift_none_long` for false reports. These are preserved failures. Optional `--drop-every`, `--corrupt-every` and `--reorder-pairs` simulate local link faults without ACKs or retries; receiver age and state are separate from sender knowledge. None is a real radio experiment.

## Check evidence without rerunning campaigns

```sh
python scripts/check_paper_artifacts.py
python scripts/verify_paper_revision.py
python scripts/verify_paper.py
python scripts/verify_transfer.py
```

These check committed summaries/provenance and the current PDF without a full campaign or raw-archive replay. A normal Git checkout with history is needed for Git comparisons; use `git fetch --unshallow` if a shallow clone lacks the recorded base. For optional raw-archive checks, complete fresh replay and paper generation, follow [scripts](../scripts/README.md) and [results](../results/README.md). Do not run historical builders against their default evidence paths just to explore the project.

## Troubleshooting

| Symptom | Next step |
| --- | --- |
| Missing upstream file/import | Initialize submodules; run from the checkout root. Do not update their pinned commits. |
| SensorTrust compiler error | Check `cc --version` and `CC`; compiler failures are real failures, not a Python fallback. |
| Python/dependency install error | Use Python 3.14 with the lock; other versions are not verified against it. |
| Output already exists | Choose a new scratch directory. |
| Timestamp/layout error | Check seconds, order, channel names and layout against the input contract. |
| Import works in scripts but not an interactive shell | Check the active interpreter/editable install; earlier macOS import issues are in [validation history](VALIDATION_HISTORY.md). |
| Verification needs absent archives or old paths | Distinguish committed summary checks from full local-archive audits; read the script's navigation entry first. |
