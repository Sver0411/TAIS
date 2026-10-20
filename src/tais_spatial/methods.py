"""Minimal fixed-plan detectors. No truth, case names or future data enter here."""
from __future__ import annotations

import numpy as np


def trailing_median(x, fresh, length):
    """Use past fresh values only; require three finite entries for a reference.

    The current sample is excluded to avoid absorbing its own displacement."""
    source = np.where(fresh, x, np.nan)
    windows = np.lib.stride_tricks.sliding_window_view(np.pad(source, (length, 0), constant_values=np.nan), length)[:-1]
    n = np.isfinite(windows).sum(axis=1)
    ordered = np.sort(np.where(np.isfinite(windows), windows, np.inf), axis=1)
    left = ordered[np.arange(len(x)), np.maximum((n - 1) // 2, 0)]
    right = ordered[np.arange(len(x)), np.maximum(n // 2, 0)]
    return np.where(n >= 3, (left + right) / 2, np.nan)


def trend(series, fresh, poll, duration, minimum_points, minimum_span):
    """Trailing least-squares evidence using current/past fresh samples only."""
    y = np.asarray(series, dtype=float); t = np.arange(len(y), dtype=float) * poll
    ok = np.isfinite(y) & fresh; length = duration // poll + 1
    def rolling(v):
        c = np.pad(np.cumsum(v), (1, 0))
        return c[1:] - c[np.maximum(np.arange(len(y)) + 1 - length, 0)]
    n = rolling(ok.astype(float)); sy = rolling(np.where(ok, y, 0))
    st = rolling(np.where(ok, t, 0)); stt = rolling(np.where(ok, t*t, 0))
    syy = rolling(np.where(ok, y*y, 0)); sty = rolling(np.where(ok, t*y, 0))
    vt = n*stt-st*st; vy = n*syy-sy*sy; cov = n*sty-st*sy
    slope = np.divide(cov, vt, out=np.zeros(len(y)), where=vt > 0)
    r2 = np.divide(cov*cov, vt*vy, out=np.zeros(len(y)), where=(vt > 0) & (vy > 1e-12))
    positions = np.flatnonzero(ok)
    span = np.zeros(len(y))
    if len(positions):
        lo = np.searchsorted(positions, np.arange(len(y)) - length + 1)
        hi = np.searchsorted(positions, np.arange(len(y)), side="right") - 1
        first = positions[np.minimum(lo, len(positions)-1)]
        last = positions[np.maximum(hi, 0)]
        span = np.where(hi >= lo, (last-first)*poll, 0)
    eligible = (n >= minimum_points) & (span >= minimum_span) & ok
    return np.where(eligible, abs(slope)*span, 0), np.where(eligible, np.clip(r2, 0, 1), 0)


def features(values, rows, real_residual, null_residual, config):
    """Build causal displacement, fresh-row jumps and trailing trend evidence.

    Repeated cached rows do not become new observations. All trend arrays use
    current/past polls only; no intervention labels enter this function."""
    values = np.asarray(values, dtype=float); rows = np.asarray(rows)
    valid = np.isfinite(values) & (rows >= 0)
    previous = np.full(len(rows), -1, dtype=np.int64)
    last = -1
    for i in range(len(rows)):
        previous[i] = last
        if valid[i]:
            last = rows[i]
    fresh = valid & (rows != previous)
    median = trailing_median(values, fresh, config["short_history_seconds"] // config["poll_seconds"])
    jump = np.zeros(len(values)); last_value = None
    for i in range(len(values)):
        if fresh[i]:
            if last_value is not None:
                jump[i] = abs(values[i] - last_value)
            last_value = values[i]
    out = {"score": abs(values - median), "fresh": fresh, "jump": jump, "past_median": median}
    for name, series in [("history", values), ("spatial", real_residual), ("null", null_residual)]:
        displacement, r2 = trend(series, fresh, config["poll_seconds"], config["trend_history_seconds"],
                                 config["trend_minimum_points"], config["trend_minimum_span_seconds"])
        out[name + "_displacement"] = displacement; out[name + "_r2"] = r2
    return out


def detect(feature, threshold, method, config):
    """Emit onset-only reports with sampled hysteresis and optional trend suppression.

    Missing/stale samples leave active unchanged. HistoryExtended, Spatial and
    NullSpatial choose different trend features; a fresh large jump bypasses
    suppression. A report is detector output, not verified physical truth."""
    active = False; raw = np.zeros(len(feature["score"]), dtype=bool)
    for i, score in enumerate(feature["score"]):
        if not feature["fresh"][i] or not np.isfinite(score):
            continue
        if not active and score >= threshold:
            active = True; raw[i] = True
        elif active and score < threshold * config["release_threshold_factor"]:
            active = False
    if method == "HistoryShort":
        suspicious = np.zeros(len(raw), dtype=bool)
    else:
        key = {"HistoryExtended": "history", "Spatial": "spatial", "NullSpatial": "null"}[method]
        suspicious = ((feature[key + "_displacement"] >= threshold * config["trend_displacement_threshold_factor"])
                      & (feature[key + "_r2"] >= config["trend_r2"]))
    bypass = feature["jump"] >= threshold
    report = raw & (~suspicious | bypass)
    return report, {"raw_onset": raw, "suspicious": suspicious, "fast_bypass": bypass}
