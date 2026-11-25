"""Self-contained unit tests for Phase 6 Intel Berkeley loader & spatial identifiability."""
import gzip
import math
from pathlib import Path

from tais.real_data import (
    SpatialParams,
    evaluate_spatial_methods,
    k_nearest_neighbors,
    load_intel_berkeley,
    run_spatial_detector,
)


def test_k_nearest_neighbors_metric_order():
    locs = {1: (0.0, 0.0), 2: (1.0, 0.0), 3: (0.0, 2.0), 4: (5.0, 5.0), 5: (0.5, 0.5)}
    nn = k_nearest_neighbors(locs, target=1, k=3)
    assert [m for m, _ in nn] == [5, 2, 3]
    assert all(m != 1 for m, _ in nn)


def test_causal_loader_rejects_future_leakage_and_bad_values(tmp_path: Path):
    locs_p = tmp_path / "mote_locs.txt"
    locs_p.write_text("1 1.0 2.0\n2 2.0 2.0\n")
    data_p = tmp_path / "data.txt.gz"
    lines = [
        "2004-03-01 00:01:00.0 1 1 22.0 40.0 100.0 2.7\n",
        "2004-03-01 00:02:00.0 2 1 122.0 40.0 100.0 2.7\n",  # out-of-range temp
        "2004-03-01 00:05:00.0 5 1 24.5 42.0 100.0 2.7\n",
        "malformed line\n",
    ]
    with gzip.open(data_p, "wt", encoding="utf-8") as f:
        f.writelines(lines)

    ds = load_intel_berkeley(data_p, locs_p)
    series = ds.causal_series("2004-03-01", 1, start_s=0, end_s=360, step_s=60, max_staleness_s=90)
    assert series[0]["temperature"] is None
    assert series[1]["temperature"] == 22.0
    assert series[2]["temperature"] == 22.0
    assert series[3]["temperature"] is None
    assert series[5]["temperature"] == 24.5


def test_spatial_knn_breaks_single_drift_vs_common_event_tie_and_beats_null():
    """Single-channel cannot separate drift from common ramp; SpatialKNN does and NullSpatial cannot."""
    n = 200
    clean = [22.0] * n
    ramp = [22.0 + (4.0 * min(1.0, max(0.0, (t - 70) / 60.0)) if t >= 70 else 0.0) for t in range(n)]
    flat_nbrs = [[22.0] * n for _ in range(4)]
    common_nbrs = [list(ramp) for _ in range(4)]
    null_nbrs = [[22.0] * n for _ in range(4)]

    # 1. Single-mote drift (neighbors stay flat)
    res_drift = evaluate_spatial_methods(
        clean, ramp, flat_nbrs, flat_nbrs, null_nbrs,
        target_offset=22.0, nbr_offsets=[22.0] * 4, null_offsets=[22.0] * 4,
        event_window=None, drift_window=(70, 150), params=SpatialParams(),
    )
    assert res_drift["SingleChannel"]["drift_false_env_alarms"] >= 1
    assert res_drift["SpatialKNN"]["drift_false_env_alarms"] == 0
    assert res_drift["SpatialKNN"]["drift_correctly_flagged"] == 1

    # 2. Common environmental ramp (neighbors move together)
    res_common = evaluate_spatial_methods(
        clean, ramp, flat_nbrs, common_nbrs, null_nbrs,
        target_offset=22.0, nbr_offsets=[22.0] * 4, null_offsets=[22.0] * 4,
        event_window=(70, 150), drift_window=None, params=SpatialParams(),
    )
    assert res_common["SpatialKNN"]["event_detected"] == 1
    assert res_common["NullSpatial"]["event_detected"] == 0

    # 3. Local sharp fast event (target jumps +3.5C suddenly while neighbors stay flat)
    fast = [22.0 + (3.5 if 90 <= t < 110 else 0.0) for t in range(n)]
    res_fast = evaluate_spatial_methods(
        clean, fast, flat_nbrs, flat_nbrs, null_nbrs,
        target_offset=22.0, nbr_offsets=[22.0] * 4, null_offsets=[22.0] * 4,
        event_window=(90, 115), drift_window=None, params=SpatialParams(),
    )
    assert res_fast["SpatialKNN"]["event_detected"] == 1


def test_spatial_knn_cancels_diurnal_hvac_ramp_while_null_spatial_triggers_false_drift():
    """Realistic +6C morning HVAC ramp should NOT trigger SpatialKNN false drift, while NullSpatial fails."""
    n = 300
    # Morning HVAC turns on between t=40 and t=100 (+6C), then holds steady
    diurnal = [17.0 + 6.0 * min(1.0, max(0.0, (t - 40) / 60.0)) for t in range(n)]
    nbr_same_day = [[v + (j - 1.5) * 1.2 for v in diurnal] for j in range(4)]  # large static offsets cancel!
    # NullSpatial from a weekend day without morning HVAC ramp
    nbr_other_day = [[18.0 + (j - 1.5) * 1.2 for _ in range(n)] for j in range(4)]

    # Inject +4C slow drift starting at t=160
    drifted = [
        diurnal[t] + (4.0 * min(1.0, (t - 160) / 50.0) if t >= 160 else 0.0)
        for t in range(n)
    ]
    res = evaluate_spatial_methods(
        diurnal, drifted, nbr_same_day, nbr_same_day, nbr_other_day,
        target_offset=21.0, nbr_offsets=[21.0] * 4, null_offsets=[21.0] * 4,
        event_window=None, drift_window=(160, 250), params=SpatialParams(),
    )
    assert res["SpatialKNN"]["clean_false_drift_onsets"] == 0
    assert res["SpatialKNN"]["drift_correctly_flagged"] == 1
    assert res["SpatialKNN"]["drift_false_env_alarms"] == 0
    # NullSpatial mismatches the clean morning HVAC ramp and emits a false drift onset!
    assert res["NullSpatial"]["clean_false_drift_onsets"] >= 1


def test_strict_causality_spatial_prefix_invariance():
    n = 120
    a = [22.0] * n
    b = [22.0] * 70 + [35.0] * 50
    na = [[22.0] * n for _ in range(3)]
    nb = [[22.0] * 70 + [35.0] * 50 for _ in range(3)]
    ra = run_spatial_detector(a[:70], [s[:70] for s in na], 22.0, [22.0] * 3, "SpatialKNN")
    rb = run_spatial_detector(b, nb, 22.0, [22.0] * 3, "SpatialKNN")
    assert [t for t in rb["env_onsets"] if t < 70] == ra["env_onsets"]
    assert [t for t in rb["drift_onsets"] if t < 70] == ra["drift_onsets"]
