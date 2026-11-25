#!/usr/bin/env python3
"""Phase 6: Intel Berkeley 54-Mote External Validity (Exp A) & Spatial Drift Identifiability (Exp B)."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
import math
import multiprocessing
from pathlib import Path
from statistics import median
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tais.closed_loop import ClosedLoopParams, ClosedLoopSender, LinkProfile, StatefulLinkModel
from tais.closed_loop.trace_link import TraceDrivenLinkModel, load_e220_regimes
from tais.config import load
from tais.core_stream import CoreReceiver
from tais.paper_baselines import episodes
from tais.real_data import (
    SpatialParams,
    evaluate_spatial_methods,
    k_nearest_neighbors,
    load_intel_berkeley,
)
from tais.signals import Fault
from tais.wire_codec import encode, envelope_from_record
from simulator.events import Event
from analyze_ablation import holm
from benchmark_phase5_boundary import _evaluate_run, _replay_open_loop_sender

DATA_GZ = ROOT / "data/raw/intel_berkeley/data.txt.gz"
LOCS_TXT = ROOT / "data/raw/intel_berkeley/mote_locs.txt"
OUT_DIR = ROOT / "results/phase6_intel_berkeley"

CALIB_DATES = ["2004-02-28", "2004-02-29", "2004-03-01"]
ISOLATION_DATES = ["2004-03-02"]
HELDOUT_DATES = [
    "2004-03-03", "2004-03-04", "2004-03-05", "2004-03-06",
    "2004-03-07", "2004-03-08", "2004-03-09", "2004-03-10",
    "2004-03-11", "2004-03-12", "2004-03-13", "2004-03-14",
]
TIME_SCALE = 6.0  # 1 real 30s Intel Berkeley slot -> 5s TAIS normalized tick (real_s = 6 * tick_s)


@dataclass
class RealTrace:
    scenario: str
    observed: list[dict]
    events: list[Event]
    faults: list[Fault]


def _build_real_bg_1800(ds, date: str, mote: int) -> list[dict]:
    """3 real hours (08:00-11:00 = 360 causal 30s slots) mapped 1:6 to 1800 normalized ticks."""
    slots = ds.causal_series(date, mote, start_s=8 * 3600, end_s=11 * 3600, step_s=30, max_staleness_s=90.0)
    rows = []
    for k, s in enumerate(slots):
        for off in range(5):
            rows.append(
                dict(
                    timestamp=k * 5 + off,
                    temperature=s["temperature"],
                    humidity=s["humidity"],
                )
            )
    return rows


def _inject_exp_a(bg: list[dict], scenario: str) -> tuple[RealTrace, RealTrace]:
    obs = deepcopy(bg)
    cf_obs = deepcopy(bg)
    events: list[Event] = []
    faults: list[Fault] = []

    def add_pulse(arr, ch, start, end, amp):
        dur = end - start
        for t in range(start, end):
            if arr[t][ch] is not None:
                u = (t - start + 0.5) / dur
                w = 1.0 if u < 0.7 else math.exp(-10.0 * (u - 0.7))
                arr[t][ch] = arr[t][ch] + amp * w

    if scenario == "real_clean_events":
        add_pulse(obs, "temperature", 300, 420, 3.5)
        add_pulse(cf_obs, "temperature", 300, 420, 3.5)
        add_pulse(obs, "humidity", 1020, 1140, 12.0)
        add_pulse(cf_obs, "humidity", 1020, 1140, 12.0)
        events = [Event("temperature", 300, 419), Event("humidity", 1020, 1139)]
    elif scenario == "real_range_cross":
        add_pulse(obs, "humidity", 600, 750, 12.0)
        add_pulse(cf_obs, "humidity", 600, 750, 12.0)
        events = [Event("humidity", 600, 749)]
        for t in range(500, 900):
            obs[t]["temperature"] = 105.0
        faults = [Fault("temperature", 500, 900, "range")]
    elif scenario == "real_drift_cross":
        add_pulse(obs, "humidity", 660, 810, 12.0)
        add_pulse(cf_obs, "humidity", 660, 810, 12.0)
        events = [Event("humidity", 660, 809)]
        acc = 0.0
        for t in range(500, 1100):
            acc += 0.015
            if obs[t]["temperature"] is not None:
                obs[t]["temperature"] = obs[t]["temperature"] + acc
        faults = [Fault("temperature", 500, 1100, "drift")]
    else:
        raise ValueError(scenario)

    return RealTrace(scenario, obs, events, faults), RealTrace(scenario + ":cf", cf_obs, events, [])


def _run_exp_a_date(date: str, motes: list[int], bg_map: dict, plan: dict, phase4_plan: dict) -> list[dict]:
    cfg = load()
    params = ClosedLoopParams(**plan["params"])
    regimes = load_e220_regimes()
    methods = ["Fixed-20", "A5", "A7", "JALC-AoI", "JALC-Full"]
    scenarios = ["real_clean_events", "real_range_cross", "real_drift_cross"]
    date_seed = int(hashlib.sha256(date.encode()).hexdigest()[:8], 16) % 100000

    link_specs = [
        ("loss_0", None),
        ("e220_burst_20", regimes["e220_burst_20"][date_seed % len(regimes["e220_burst_20"])]),
        ("e220_random_30", regimes["e220_random_30"][date_seed % len(regimes["e220_random_30"])]),
    ]

    rows = []
    for mote in motes:
        bg = bg_map[(date, mote)]
        valid_frac = sum(r["temperature"] is not None and r["humidity"] is not None for r in bg) / len(bg)
        for sc in scenarios:
            tr, cf = _inject_exp_a(bg, sc)
            sender_cache: dict = {}
            cf_cache: dict = {}
            for lname, hw_prof in link_specs:
                for m in methods:
                    def _run_one(trace_obj, cache_dict, tag):
                        rx = CoreReceiver(layout_id=1)
                        if hw_prof is None:
                            link = StatefulLinkModel(LinkProfile("loss_0", loss_rate=0.0), receiver=rx, seed=date_seed + mote, label=tag)
                        else:
                            link = TraceDrivenLinkModel(hw_prof, receiver=rx, seed=date_seed + mote, label=tag)
                        if m == "JALC-Full":
                            sender = ClosedLoopSender(cfg, params=params, variant="Full", link=link)
                            recs = []
                            try:
                                for src in trace_obj.observed:
                                    item = sender.push(src)
                                    if item is not None:
                                        recs.append(item["record"])
                            finally:
                                sender.close()
                            res = episodes(recs, tuple(cfg["channels"]))
                        else:
                            if m not in cache_dict:
                                cache_dict[m] = _replay_open_loop_sender(trace_obj, cfg, phase4_plan, params, m)
                            res = cache_dict[m]
                            for rec in res["records"]:
                                if rec["upload"]:
                                    env = envelope_from_record(rec, layout_id=1)
                                    frame = encode(env, layout_id=1)
                                    link.send(float(rec["timestamp"]), frame, env, redundancy_k=1)
                        return res, link

                    cf_bundle = _run_one(cf, cf_cache, f"{date}:{mote}:{sc}:{lname}:cf") if tr.faults else None
                    res, link = _run_one(tr, sender_cache, f"{date}:{mote}:{sc}:{lname}")
                    met = _evaluate_run(tr, res, link, cfg, plan, cf_bundle=cf_bundle)
                    rows.append(
                        dict(
                            date=date,
                            mote=mote,
                            scenario=sc,
                            link_id=lname,
                            method=m,
                            bg_valid_frac=valid_frac,
                            real_finite_age_mean_s=met["finite_age_mean_s"] * TIME_SCALE,
                            real_finite_age_p95_s=met["finite_age_p95_s"] * TIME_SCALE,
                            **met,
                        )
                    )
    return rows


def run_exp_b(ds, target_motes: list[int], calib_offsets: dict[int, float]) -> pd.DataFrame:
    """12 held-out dates x 20 target motes x 5 scenarios x 3 spatial methods."""
    params = SpatialParams()
    # 06:00 to 20:00 every 2 minutes -> 420 causal slots/day (max staleness 10 min = 600s)
    start_s, end_s, step_s, max_stale = 6 * 3600, 20 * 3600, 120, 600.0
    n_slots = (end_s - start_s) // step_s  # 420

    # Pre-extract 2-min temperature series for calibration prefix (for NullSpatial) & held-out dates
    calib_series: dict[tuple[str, int], list[float | None]] = {}
    for cd in CALIB_DATES:
        for m in ds.locations:
            calib_series[(cd, m)] = [
                r["temperature"]
                for r in ds.causal_series(cd, m, start_s, end_s, step_s, max_stale)
            ]

    rows = []
    # Daytime intervention after real 06:00-09:00 HVAC warmup (slot 150 = 11:00, slot 210 = 13:00, slot 270 = 15:00):
    # Slow ramp: slots 150..210 (+4.0C linear over 2 hours), hold 210..240, return 240..270
    # Fast local event: slots 195..215 (+3.5C sharp step for 40 min)
    for d_idx, date in enumerate(HELDOUT_DATES):
        day_series = {
            m: [r["temperature"] for r in ds.causal_series(date, m, start_s, end_s, step_s, max_stale)]
            for m in ds.locations
        }
        null_date = CALIB_DATES[d_idx % len(CALIB_DATES)]

        for target in target_motes:
            t_clean = day_series[target]
            t_valid = sum(v is not None for v in t_clean) / n_slots
            nbrs = k_nearest_neighbors(ds.locations, target, k=4)
            nbr_ids = [m for m, _ in nbrs]
            mean_dist_m = float(np.mean([dist for _, dist in nbrs]))

            n_clean = [day_series[m] for m in nbr_ids]
            # Equal-cost NullSpatial: calibration-day values masked identically to real neighbor availability
            n_null = [
                [
                    calib_series[(null_date, m)][i] if n_clean[j][i] is not None else None
                    for i in range(n_slots)
                ]
                for j, m in enumerate(nbr_ids)
            ]

            # Strictly static calibration-prefix inter-mote offsets (zero held-out leakage)
            t_off = calib_offsets.get(target, 22.0)
            n_offs = [calib_offsets.get(m, 22.0) for m in nbr_ids]
            null_offs = list(n_offs)

            def ramp_add(series, scale=1.0):
                out = list(series)
                for i in range(150, 270):
                    if out[i] is None:
                        continue
                    if i < 210:
                        delta = 4.0 * (i - 150) / 60.0
                    elif i < 240:
                        delta = 4.0
                    else:
                        delta = 4.0 * (270 - i) / 30.0
                    out[i] = out[i] + scale * delta
                return out

            def fast_add(series):
                out = list(series)
                for i in range(195, 215):
                    if out[i] is not None:
                        out[i] = out[i] + 3.5
                return out

            scenarios_b = [
                ("single_drift", ramp_add(t_clean, 1.0), n_clean, None, (150, 270)),
                ("common_env_event", ramp_add(t_clean, 1.0), [ramp_add(ns, 0.9) for ns in n_clean], (150, 270), None),
                ("local_fast_event", fast_add(t_clean), n_clean, (195, 225), None),
                ("drift_plus_local_fast", fast_add(ramp_add(t_clean, 1.0)), n_clean, (195, 225), (150, 194)),
                ("local_slow_event", ramp_add(t_clean, 1.0), n_clean, (150, 270), None),
            ]
            for sc_name, t_int, n_int, ev_win, dr_win in scenarios_b:
                res = evaluate_spatial_methods(
                    t_clean, t_int, n_clean, n_int, n_null,
                    t_off, n_offs, null_offs, ev_win, dr_win, params=params,
                )
                for mode, vals in res.items():
                    rows.append(
                        dict(
                            date=date,
                            is_outage_day=date in ("2004-03-10", "2004-03-11"),
                            target_mote=target,
                            mean_nbr_dist_m=round(mean_dist_m, 2),
                            target_valid_frac=t_valid,
                            scenario=sc_name,
                            method=mode,
                            **vals,
                        )
                    )
    return pd.DataFrame(rows)


def _date_paired_bootstrap(df: pd.DataFrame, method_a: str, method_b: str, metric: str, seed: int = 2026112502):
    dates = sorted(df["date"].unique())
    piv = df.groupby(["date", "method"])[metric].mean().unstack().loc[dates]
    delta = (piv[method_a] - piv[method_b]).to_numpy(dtype=float)
    rng = np.random.default_rng(seed)
    n = len(delta)
    draw = rng.integers(0, n, size=(5000, n))
    signs = rng.choice([-1, 1], size=(20000, n))
    point = float(delta.mean())
    lo, hi = np.percentile(delta[draw].mean(axis=1), [2.5, 97.5])
    p = (1 + np.count_nonzero(np.abs(signs @ delta / n) >= abs(point) - 1e-12)) / (len(signs) + 1)
    return point, float(lo), float(hi), float(p)


def make_figures(audit: dict, exp_a: pd.DataFrame, exp_b: pd.DataFrame) -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.2,
        }
    )
    fig_dir = OUT_DIR / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # --- Fig 1: Dataset daily coverage + Exp A External Validity ---
    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.9))
    daily = pd.DataFrame(audit["daily_summary"])
    colors_bar = [
        "#4477aa" if d in CALIB_DATES else ("#228833" if d in HELDOUT_DATES else "#bbbbbb")
        for d in daily["date"]
    ]
    axes[0].bar(range(len(daily)), daily["slot_2min_coverage_54motes"] * 100.0, color=colors_bar)
    axes[0].axhline(50.0, color="black", ls="--", lw=0.9, label="50% Coverage Gate")
    from matplotlib.patches import Patch
    handles = [
        Patch(color="#4477aa", label="Calibration (3d)"),
        Patch(color="#228833", label="Held-out Eval (12d)"),
        Patch(color="#bbbbbb", label="Gap / Post-decay"),
        plt.Line2D([0], [0], color="black", ls="--", lw=0.9, label="50% Gate"),
    ]
    axes[0].set(
        ylabel="54-Mote 2-min Coverage (%)",
        xlabel="Chronological Date Index (2004-02-28 to 04-02)",
        title="Intel Berkeley Pre-Evaluation Coverage Audit",
    )
    axes[0].legend(handles=handles, fontsize=7.5, loc="upper right")

    methods_a = ["Fixed-20", "A5", "A7", "JALC-AoI", "JALC-Full"]
    m_colors = {"Fixed-20": "#777777", "A5": "#aa3377", "A7": "#cc3311", "JALC-AoI": "#228833", "JALC-Full": "#004488"}
    links = ["loss_0", "e220_burst_20", "e220_random_30"]
    link_labels = ["Lossless", "E220 Burst 20%", "E220 Random 30%"]
    x = np.arange(len(links))
    for m in methods_a:
        f1s, aois = [], []
        for lid in links:
            g = exp_a[(exp_a["method"] == m) & (exp_a["link_id"] == lid)]
            tp, fp, n = g["receiver_tp"].sum(), g["receiver_fp"].sum(), g["n_events"].sum()
            f1s.append(200.0 * tp / (n + tp + fp) if (n + tp + fp) else 0.0)
            aois.append(g["real_finite_age_p95_s"].mean() / 60.0)  # real minutes
        lw = 2.4 if m == "JALC-Full" else 1.4
        axes[1].plot(x, f1s, "o-", lw=lw, label=m, color=m_colors[m])
        axes[2].plot(x, aois, "o-", lw=lw, label=m, color=m_colors[m])
    axes[1].set(xticks=x, xticklabels=link_labels, ylabel="Receiver F1 (%)", title="Exp A: Real Intel Background × E220 Link (F1)")
    axes[2].set(xticks=x, xticklabels=link_labels, ylabel="Run-P95 Finite AoI (real minutes)", title="Exp A: Real Wall-Clock Data Freshness")
    axes[2].axhline(4.5, color="black", ls="--", lw=0.9, label="4.5 min AoI cap")
    axes[2].legend(fontsize=7.5, loc="upper left")
    fig.suptitle("Phase 6 Exp A: Real 54-Mote Intel Berkeley Background × Real E220 Hardware Loss Traces (12 held-out dates)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(fig_dir / "fig01_intel_berkeley_coverage_and_external_validity.png", dpi=180)
    fig.savefig(fig_dir / "fig01_intel_berkeley_coverage_and_external_validity.pdf")
    plt.close(fig)

    # --- Fig 2: Exp B Spatial Drift Identifiability ---
    fig, axes = plt.subplots(1, 2, figsize=(15.0, 5.2))
    modes = ["SingleChannel", "SpatialKNN", "NullSpatial"]
    mode_colors = {"SingleChannel": "#cc3311", "SpatialKNN": "#004488", "NullSpatial": "#999999"}

    # Panel 1: Drift false environmental alarms/run & clean-day false drift/run (no clipping!)
    sd = exp_b[exp_b["scenario"] == "single_drift"]
    x1 = np.arange(len(modes))
    false_env = [sd[sd["method"] == m]["drift_false_env_alarms"].mean() for m in modes]
    clean_fdr = [sd[sd["method"] == m]["clean_false_drift_onsets"].mean() for m in modes]
    b1 = axes[0].bar(x1 - 0.18, false_env, width=0.34, color="#cc3311", alpha=0.85, label="Drift -> False Env Alarms / run (lower better)")
    b2 = axes[0].bar(x1 + 0.18, clean_fdr, width=0.34, color="#ee8833", alpha=0.85, label="Clean-Day Spurious Drift / run (lower better)")
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            axes[0].text(bar.get_x() + bar.get_width() / 2.0, h + 0.04, f"{h:.2f}", ha="center", va="bottom", fontsize=8)
    axes[0].set(xticks=x1, xticklabels=modes, ylabel="Mean False Onsets per Run (count)", title="False Alarms: Drift Misclassification & Clean-Day Noise", ylim=(0, 2.55))
    axes[0].legend(fontsize=8, loc="upper left")

    # Panel 2: Drift Identification + Event Recall across all 5 scenarios
    ev_scenarios = ["single_drift", "common_env_event", "local_fast_event", "drift_plus_local_fast", "local_slow_event"]
    ev_labels = ["Single Drift\n(Identified)", "Common Env\nRamp", "Local Fast\nEvent", "Drift + Local\nFast Event", "Local Slow\n(Boundary)"]
    x2 = np.arange(len(ev_scenarios))
    w = 0.25
    for idx_m, m in enumerate(modes):
        vals = []
        for sc in ev_scenarios:
            sub_sc = exp_b[(exp_b["scenario"] == sc) & (exp_b["method"] == m)]
            col = "drift_correctly_flagged" if sc == "single_drift" else "event_detected"
            vals.append(sub_sc[col].mean() * 100.0)
        bars = axes[1].bar(x2 + (idx_m - 1) * w, vals, width=w, color=mode_colors[m], alpha=0.88, label=m)
        for bar in bars:
            h = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2.0, h + 1.5, f"{h:.0f}%", ha="center", va="bottom", fontsize=7)
    axes[1].set(xticks=x2, xticklabels=ev_labels, ylabel="Detection / Identification Rate (%)", title="Identifiability Gain, NullSpatial Control & Honest H3 Boundary", ylim=(0, 108))
    axes[1].legend(fontsize=8, loc="upper right")
    fig.suptitle("Phase 6 Exp B: Causal Spatial k-NN Reference vs. Single-Channel & Equal-Cost NullSpatial (12 held-out dates × 20 motes)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(fig_dir / "fig02_spatial_identifiability_drift_vs_events.png", dpi=180)
    fig.savefig(fig_dir / "fig02_spatial_identifiability_drift_vs_events.pdf")
    plt.close(fig)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = json.loads((OUT_DIR / "data_audit.json").read_text())
    plan = json.loads((ROOT / "configs/phase5_boundary.json").read_text())
    phase4_plan = json.loads((ROOT / "configs/phase4.json").read_text())

    all_needed_dates = set(CALIB_DATES) | set(HELDOUT_DATES)
    print("Loading Intel Berkeley records for", len(all_needed_dates), "dates...", flush=True)
    ds = load_intel_berkeley(DATA_GZ, LOCS_TXT, dates_filter=all_needed_dates)

    # Select target motes STRICTLY on calibration prefix availability (zero held-out peeking!)
    calib_counts = {}
    calib_offsets = {}
    for m in ds.locations:
        pts = [pt[1] for d in CALIB_DATES for pt in ds.records.get(d, {}).get(m, [])]
        calib_counts[m] = len(pts)
        if pts:
            calib_offsets[m] = median(pts)
    ranked_motes = [m for m, _ in sorted(calib_counts.items(), key=lambda kv: (-kv[1], kv[0]))]
    motes_b = ranked_motes[:20]
    motes_a = ranked_motes[:10]
    print("Calibration-selected top-10 motes (Exp A):", motes_a)
    print("Calibration-selected top-20 motes (Exp B):", motes_b)

    # --- Experiment A ---
    bg_map = {(d, m): _build_real_bg_1800(ds, d, m) for d in HELDOUT_DATES for m in motes_a}
    exp_a_rows = []
    with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn")) as pool:
        futs = [pool.submit(_run_exp_a_date, d, motes_a, bg_map, plan, phase4_plan) for d in HELDOUT_DATES]
        for fut in as_completed(futs):
            exp_a_rows.extend(fut.result())
    exp_a = pd.DataFrame(exp_a_rows).sort_values(["date", "mote", "scenario", "link_id", "method"])
    exp_a.to_csv(OUT_DIR / "exp_a_metrics.csv", index=False)

    # Exp A summary & date-cluster paired effects
    sum_a = []
    for (lid, m), g in exp_a.groupby(["link_id", "method"]):
        tp, fp, n = g["receiver_tp"].sum(), g["receiver_fp"].sum(), g["n_events"].sum()
        sum_a.append(
            dict(
                link_id=lid,
                method=m,
                receiver_f1=2 * tp / (n + tp + fp) if (n + tp + fp) else np.nan,
                receiver_recall=tp / n if n else np.nan,
                real_p95_aoi_s=float(g["real_finite_age_p95_s"].mean()),
                real_mean_aoi_s=float(g["real_finite_age_mean_s"].mean()),
                aoi_violation_rate=float(g["aoi_violation_45s_rate"].mean()),
                sent_bytes=int(g["sent_bytes"].sum()),
                receiver_fi=int(g["receiver_fault_induced_false"].sum()),
            )
        )
    sum_a_df = pd.DataFrame(sum_a)
    sum_a_df.to_csv(OUT_DIR / "exp_a_summary.csv", index=False)

    # --- Experiment B ---
    exp_b = run_exp_b(ds, motes_b, calib_offsets)
    exp_b.to_csv(OUT_DIR / "exp_b_metrics.csv", index=False)

    sum_b = (
        exp_b.groupby(["scenario", "method"])
        .agg(
            runs=("event_detected", "size"),
            event_recall=("event_detected", "mean"),
            drift_false_env_per_run=("drift_false_env_alarms", "mean"),
            drift_flagged_rate=("drift_correctly_flagged", "mean"),
            clean_false_drift_per_run=("clean_false_drift_onsets", "mean"),
            mean_spatial_slots=("spatial_ref_used_slots", "mean"),
        )
        .reset_index()
    )
    sum_b.to_csv(OUT_DIR / "exp_b_summary.csv", index=False)

    # Date-cluster paired Bootstrap + Sign-Flip + Holm for Exp B & Exp A
    effects = []
    for lid in ["loss_0", "e220_burst_20", "e220_random_30"]:
        sub = exp_a[exp_a["link_id"] == lid].copy()
        # Date-level micro F1 per (date, method)
        dm = sub.groupby(["date", "method"]).apply(
            lambda g: pd.Series(
                dict(
                    rx_f1=2 * g["receiver_tp"].sum() / max(1, g["n_events"].sum() + g["receiver_tp"].sum() + g["receiver_fp"].sum()),
                    real_p95_aoi_s=g["real_finite_age_p95_s"].mean(),
                    aoi_viol=g["aoi_violation_45s_rate"].mean(),
                )
            ),
            include_groups=False,
        ).reset_index()
        for ref in ["A5", "Fixed-20", "JALC-AoI"]:
            for met in ["rx_f1", "real_p95_aoi_s", "aoi_viol"]:
                pt, lo, hi, p = _date_paired_bootstrap(dm, "JALC-Full", ref, met)
                effects.append(dict(exp="ExpA_" + lid, method="JALC-Full", reference=ref, metric=met, mean_date_diff=pt, ci95_low=lo, ci95_high=hi, p_signflip=p))

    for sc, met in [
        ("single_drift", "drift_false_env_alarms"),
        ("single_drift", "drift_correctly_flagged"),
        ("single_drift", "clean_false_drift_onsets"),
        ("common_env_event", "event_detected"),
        ("local_fast_event", "event_detected"),
        ("drift_plus_local_fast", "event_detected"),
        ("drift_plus_local_fast", "drift_false_env_alarms"),
        ("local_slow_event", "event_detected"),
    ]:
        sub = exp_b[exp_b["scenario"] == sc]
        for ref in ["SingleChannel", "NullSpatial"]:
            pt, lo, hi, p = _date_paired_bootstrap(sub, "SpatialKNN", ref, met)
            effects.append(dict(exp="ExpB_" + sc, method="SpatialKNN", reference=ref, metric=met, mean_date_diff=pt, ci95_low=lo, ci95_high=hi, p_signflip=p))

    eff_df = pd.DataFrame(effects)
    eff_df["p_holm"] = holm(eff_df["p_signflip"])
    eff_df["holm_sig_005"] = eff_df["p_holm"] < 0.05
    eff_df.to_csv(OUT_DIR / "paired_effects.csv", index=False)

    make_figures(audit, exp_a, exp_b)

    manifest = dict(
        status="COMPLETE",
        calib_dates=CALIB_DATES,
        isolation_dates=ISOLATION_DATES,
        heldout_dates=HELDOUT_DATES,
        motes_exp_a=motes_a,
        motes_exp_b=motes_b,
        exp_a_runs=len(exp_a),
        exp_b_runs=len(exp_b),
        data_txt_gz_sha256=audit["data_txt_gz_sha256"],
        mote_locs_txt_sha256=audit["mote_locs_txt_sha256"],
    )
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    print("\n=== EXP A SUMMARY (REAL INTEL BERKELEY BG x E220 LINKS) ===")
    print(sum_a_df.to_string(index=False))
    print("\n=== EXP B SUMMARY (SPATIAL IDENTIFIABILITY, 12 DATES x 20 MOTES) ===")
    print(sum_b.to_string(index=False))
    print("\n=== KEY DATE-CLUSTER HOLM EFFECTS ===")
    print(eff_df[eff_df["exp"].str.startswith("ExpB_") | (eff_df["exp"] == "ExpA_e220_random_30")].to_string(index=False))


if __name__ == "__main__":
    main()
