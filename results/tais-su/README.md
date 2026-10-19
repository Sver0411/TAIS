# SU-1 frozen evidence

Combination works; **balanced default replacement NO-GO**. GateOnly remains default. SU20 is a higher-sampling performance option; Gate+U preserves baseline detection with lower bytes and older ordinary snapshots. All preceding NO-GO results are unchanged. [Report](../../docs/TAIS_SU_RESULTS.md), [predeclared protocol](../../docs/TAIS_SU_PROTOCOL.md).

- `engineering`: used seed20/all45cases/seven methods315runs. Not new independent evidence.
- `development`:550–559, all45/seven3150runs. Only cap20/30/40 examined. No H.
- `selection.json`: one development choice, balanced30; initial development-quality qualification false. `selection-before-json-fix.json` retains original lock. Amendment only fixes NumPy bool JSON serialization; metrics/plots unchanged byte for byte.
- `validation`:560–569,3150runs, same7methods and choice, no reselection. `analysis-attempt1` and failure log retained.
- `freeze.json`: final scheme/source fingerprints committed in ee4df83b728a26889d58920727a9ddcde874507b before final execution.
- `test`:570–599,9450runs, once; all3caps retained including unfavorable points. Same-generator held-out evidence, not real-world validation. Every method900events, no-event Recall N/A.
- `metrics.csv` retains old sender-on-upload event definitions plus separately named `rx_*` metrics using **only received decoded flag transitions**. No local event gets counted remotely merely because it was sampled. `events.csv` has actual reports, received report times, strict and padded truth-window coverage. Do not confuse coverage with detection or truth windows with the full injected pulse including ramps.
- `pooled_age.csv` pools all source seconds; `summary.csv` ageP95 field is mean per-run P95. The pooled file is authoritative for aggregateP95. Actual null stays null, reconstruction coverage separate. Upload suppression is not lossless full-signal reconstruction.
- Seven predefined paired contrasts use5000 whole-seed bootstrap draws RNG2026101904, descriptive95%CI. Four/fewer-second measurements within one run are not independent samples. `common_event_delays.csv` compares detected-in-both events; misses remain visible.
- `test/receiver-edge-difference.json`: one real received-event difference between S and SU20 due to an omitted clear frame. Complete wire/local context, no hidden receiver labels.
- `core`:14 actual old-seed20 streams, six normal/short/drift/cross/offset cases each high/selected-balanced plus Gate+U and range-erasure failure. Source commit is the parent when new code was executed; per-file source hashes pin actual execution. No fake hardware or natural fault claims.
- Full trace copies, independent truth/fault schedules, exact frames, receiver outcomes and full clean counterfactuals are in ignored `results/traces/tais-su`. All hashes are in phase manifests/rows. The independent verifier recomputes main/receiver matches, induced counts, pooled age and actual bytes, checks SU20−S and Gate+U−Gate local parity, and guards old tracked files/upstreams. It does not tune/rerun the policy. Five original C0 files separately rehashed unchanged.
- Compressed seed audit is lossless; its legacy engine base/automatic400–449 allocation labels are not SU allocation. `seed-audit.json` pins real550–599 split and zero collisions. Uncompressed audit kept outside tracked results. No inaccessible remote-machine guarantee.

From repository root, Python + C11 compiler:

```sh
git submodule update --init --recursive
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-lock.txt
.venv/bin/python -m pip install -e . --no-build-isolation
.venv/bin/python -m pytest -q
.venv/bin/python examples/tais-core/run.py --policy tais-su --su-mode high \
  --scenario clean_short --seed 20 --pace .01 --ui live --verify \
  --out results/scratch/su-high-new-01
.venv/bin/python examples/tais-core/run.py --policy tais-su --su-mode balanced \
  --scenario drift_same_long --seed 20 --pace .01 --ui live --verify \
  --out results/scratch/su-balanced-new-01
```

`balanced` is the fixed cap30 candidate and **does not imply qualification**. Default stays GateOnly. Existing CSV/stdin and all3layouts work; no true labels means no truth-dependent metrics.

Reproduce already-used final seeds into NEW paths (engineering replication, not a new independent test):

```sh
.venv/bin/python scripts/benchmark_su.py --phase test \
  --output-root results/scratch/su-replication-01 \
  --archive-root results/traces/su-replication-01
cp results/tais-su/selection.json results/scratch/su-replication-01/selection.json
.venv/bin/python scripts/analyze_su.py --phase test --root results/scratch/su-replication-01
```

The original phase refuses overwrite; no old archive is needed for reproduction. The committed selection/frozen source hashes must match, so checkout this branch's frozen implementation. Phase manifests label replication to avoid new-independent-evidence claims. Original execution used `benchmark_su.py --phase development`, `analyze_su.py --phase development`, `analyze_su.py --select`, validation, then committed freeze and one test. The first, failed validation analysis has only a JSON export error; fixed numeric/statistical/plot files were identical.

No algorithm/config/threshold search beyond caps20/30/40. No H, APPflags, Wirev2, stateful prediction, or free acknowledgements. Health detection may change because acquisition timing changes; type-specific labels and conditional delays remain separate. Binary lengths are actual encode() lengths, not JSON counts or real radio/energy cost. Requested intervals bound the software scheduler; prerecorded data do not measure hardware sampling savings.
