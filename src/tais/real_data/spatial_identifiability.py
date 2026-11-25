"""Causal single-channel vs. spatial k-NN vs. equal-cost NullSpatial identifiability."""
from dataclasses import dataclass
import math
from statistics import median


@dataclass(frozen=True)
class SpatialParams:
    dev_threshold_c: float = 2.2
    abrupt_jump_c: float = 1.6
    spatial_residual_c: float = 1.4  # strictly < dev_threshold_c to eliminate onset race on slow drift
    min_fresh_neighbors: int = 2
    confirm_slots: int = 3
    baseline_lag_slots: int = 20     # 40 min lag at 2-min cadence
    baseline_window_slots: int = 40  # 80 min causal baseline window [t-60, t-20)


def _finite(v) -> bool:
    return v is not None and math.isfinite(v)


def _lagged_dev(series: list[float | None], t: int, lag: int, win: int) -> float | None:
    """Strictly causal deviation of series[t] relative to median(series[t-lag-win : t-lag])."""
    v = series[t] if t < len(series) else None
    if not _finite(v):
        return None
    b_start = max(0, t - lag - win)
    b_end = max(0, t - lag)
    pool = [x for x in series[b_start:b_end] if _finite(x)]
    if len(pool) < 5:
        return None
    return v - median(pool)


def run_spatial_detector(
    target_series: list[float | None],
    neighbor_series: list[list[float | None]],
    target_offset: float,
    neighbor_offsets: list[float],
    mode: str,
    params: SpatialParams | None = None,
) -> dict:
    """Strictly causal detector comparing SingleChannel, SpatialKNN, and NullSpatial.

    Uses matched causal differential deviations over the exact same lagged window [t-60, t-20)
    so static inter-mote or seasonal offsets cancel identically without future leakage:
        delta_x_target(t) = x_target(t) - median(x_target[t-60 : t-20])
        delta_x_nbr(t)    = median_{j in N_k}(x_j(t) - median(x_j[t-60 : t-20]))
        delta_r_spatial   = delta_x_target(t) - delta_x_nbr(t)
    """
    if mode not in ("SingleChannel", "SpatialKNN", "NullSpatial"):
        raise ValueError(f"Unsupported mode: {mode}")
    del target_offset, neighbor_offsets  # retained in signature for backwards compatibility
    p = params or SpatialParams()
    n = len(target_series)

    consec_env = 0
    consec_drift = 0
    env_active = False
    drift_active = False

    env_onsets: list[int] = []
    drift_onsets: list[int] = []
    env_active_slots = 0
    drift_active_slots = 0
    spatial_ref_used_slots = 0

    for t in range(n):
        v = target_series[t]
        if not _finite(v):
            consec_env = 0
            consec_drift = 0
            env_active = False
            drift_active = False
            continue

        # 1. Target causal lagged deviation [t-60, t-20)
        tdev = _lagged_dev(target_series, t, p.baseline_lag_slots, p.baseline_window_slots)
        target_dev = tdev if tdev is not None else 0.0

        # 2. Target causal short-lag abrupt jump [t-8, t-2)
        s_start = max(0, t - 8)
        s_end = max(0, t - 2)
        short_pool = [x for x in target_series[s_start:s_end] if _finite(x)]
        abrupt = abs(v - median(short_pool)) if len(short_pool) >= 3 else 0.0

        # 3. Matched causal neighbor deviations over the exact same lagged window [t-60, t-20)
        nbr_devs = []
        if mode in ("SpatialKNN", "NullSpatial"):
            for nser in neighbor_series:
                nd = _lagged_dev(nser, t, p.baseline_lag_slots, p.baseline_window_slots)
                if nd is not None:
                    nbr_devs.append(nd)

        has_spatial = len(nbr_devs) >= p.min_fresh_neighbors
        if has_spatial:
            spatial_ref_used_slots += 1
            spatial_res = target_dev - median(nbr_devs)
        else:
            spatial_res = 0.0

        is_env_cand = False
        is_drift_cand = False

        if mode == "SingleChannel":
            if abs(target_dev) >= p.dev_threshold_c or abrupt >= p.abrupt_jump_c:
                is_env_cand = True
        else:
            if abrupt >= p.abrupt_jump_c:
                # Sharp local step preserves true local fast events even during ongoing sensor drift
                is_env_cand = True
            elif abs(target_dev) >= p.dev_threshold_c:
                if has_spatial and abs(spatial_res) >= p.spatial_residual_c:
                    # Target changed slowly while k nearest physical neighbors did not -> drift
                    is_drift_cand = True
                else:
                    # Physical neighbors moved consistently (common event) or offline fallback
                    is_env_cand = True

        if is_env_cand:
            consec_env += 1
            consec_drift = 0
        elif is_drift_cand:
            consec_drift += 1
            consec_env = 0
        else:
            consec_env = 0
            consec_drift = 0

        now_env = consec_env >= p.confirm_slots
        now_drift = consec_drift >= p.confirm_slots

        if now_env and not env_active:
            env_onsets.append(t)
        if now_drift and not drift_active:
            drift_onsets.append(t)
        if now_env:
            env_active_slots += 1
        if now_drift:
            drift_active_slots += 1

        env_active = now_env
        drift_active = now_drift

    return dict(
        env_onsets=env_onsets,
        drift_onsets=drift_onsets,
        env_active_slots=env_active_slots,
        drift_active_slots=drift_active_slots,
        spatial_ref_used_slots=spatial_ref_used_slots,
    )


def evaluate_spatial_methods(
    target_clean: list[float | None],
    target_intervened: list[float | None],
    nbr_clean: list[list[float | None]],
    nbr_intervened: list[list[float | None]],
    nbr_null: list[list[float | None]],
    target_offset: float,
    nbr_offsets: list[float],
    null_offsets: list[float],
    event_window: tuple[int, int] | None,
    drift_window: tuple[int, int] | None,
    params: SpatialParams | None = None,
) -> dict[str, dict]:
    """Run SingleChannel, SpatialKNN, and equal-cost NullSpatial on paired clean & intervened worlds."""
    results = {}
    for mode, n_clean, n_int, n_offs in [
        ("SingleChannel", [], [], []),
        ("SpatialKNN", nbr_clean, nbr_intervened, nbr_offsets),
        ("NullSpatial", nbr_null, nbr_null, null_offsets),
    ]:
        base = run_spatial_detector(target_clean, n_clean, target_offset, n_offs, mode, params)
        pert = run_spatial_detector(target_intervened, n_int, target_offset, n_offs, mode, params)

        def _incremental(pert_onsets, base_onsets, win):
            if win is None:
                return []
            a, b = win
            return [
                t
                for t in pert_onsets
                if a <= t <= b and not any(abs(t - bt) <= 5 for bt in base_onsets)
            ]

        inc_env = _incremental(pert["env_onsets"], base["env_onsets"], event_window)
        inc_drift_false_env = _incremental(pert["env_onsets"], base["env_onsets"], drift_window)
        inc_drift_flagged = _incremental(pert["drift_onsets"], base["drift_onsets"], drift_window)

        results[mode] = dict(
            event_detected=1 if inc_env else 0,
            drift_false_env_alarms=len(inc_drift_false_env),
            drift_correctly_flagged=1 if inc_drift_flagged else 0,
            clean_false_drift_onsets=len(base["drift_onsets"]),
            clean_false_env_onsets=len(base["env_onsets"]),
            env_active_slots_delta=max(0, pert["env_active_slots"] - base["env_active_slots"]),
            spatial_ref_used_slots=pert["spatial_ref_used_slots"],
        )
    return results
