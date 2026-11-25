#!/usr/bin/env python3
"""Phase 5.5: Real E220-400T22D Hardware-Trace-Driven Link Validation (seeds 1200-1219)."""
from concurrent.futures import ProcessPoolExecutor, as_completed
import hashlib
import json
import multiprocessing
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from tais.closed_loop import ClosedLoopParams, ClosedLoopSender
from tais.closed_loop.trace_link import TraceDrivenLinkModel, load_e220_regimes
from tais.config import load
from tais.core_stream import CoreReceiver
from tais.paper_baselines import episodes
from tais.transfer_signals import counterfactual
from tais.wire_codec import encode, envelope_from_record
from ablation_support import make_trace as ma_trace
from analyze_ablation import holm
from benchmark_phase5_boundary import (
    _evaluate_run,
    _replay_open_loop_sender,
)
from analyze_phase5_boundary import COLORS, aggregate, paired_inference, seed_table

SEEDS = list(range(1200, 1220))
SCENARIOS = ["clean_both", "high_frequency", "drift_temperature_same", "range_temperature_cross"]
METHODS = ["Fixed-20", "A5", "A7", "Risk-T1-U1", "JALC-ObsOnly", "JALC-AoI", "JALC-Full"]
REGIME_ORDER = ["e220_random_20", "e220_random_30", "e220_burst_20", "e220_burst_30"]
OUT_DIR = ROOT / "results/phase5_hw_trace"


def audit_hw_seeds() -> dict:
    used = set()
    scanned = 0
    for p in sorted(ROOT.rglob("*")):
        if any(part in p.parts for part in (".git", ".venv", "vendor", "__pycache__", "build")):
            continue
        rel = str(p.relative_to(ROOT))
        if rel.startswith("results/phase5_hw_trace") or rel == "configs/e220_hardware_traces.json":
            continue
        if p.suffix not in (".json", ".yaml", ".yml"):
            continue
        scanned += 1
        try:
            data = json.loads(p.read_text(errors="ignore")) if p.suffix == ".json" else yaml.safe_load(p.read_text(errors="ignore"))
        except Exception:
            continue

        def walk(obj):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if "seed" in str(k).lower():
                        if isinstance(v, int) and 0 <= v < 10000:
                            used.add(v)
                        elif isinstance(v, list):
                            for item in v:
                                if isinstance(item, int) and 0 <= item < 10000:
                                    used.add(item)
                    walk(v)
            elif isinstance(obj, list):
                for item in obj:
                    walk(item)

        walk(data)

    collisions = sorted(s for s in SEEDS if s in used)
    report = dict(
        status="PASS" if not collisions else "FAIL",
        scanned_files=scanned,
        max_existing_seed=max(used) if used else None,
        candidate_seeds=SEEDS,
        collisions=collisions,
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "seed-audit.json").write_text(json.dumps(report, indent=2) + "\n")
    assert report["status"] == "PASS", report
    return report


def _replay_trace_link(trace, cfg, phase4_plan, params, method, hw_profile, seed, sc_label, sender_cache):
    channels = tuple(cfg["channels"])
    rx = CoreReceiver(layout_id=1)
    link = TraceDrivenLinkModel(hw_profile, receiver=rx, seed=seed, label=f"{sc_label}:{hw_profile.regime_id}")

    if method == "JALC-Full":
        sender = ClosedLoopSender(cfg, params=params, variant="Full", link=link)
        rows = []
        try:
            for source in trace.observed:
                item = sender.push(source)
                if item is not None:
                    rows.append(item["record"])
        finally:
            sender.close()
        result = episodes(rows, channels)
    else:
        if method not in sender_cache:
            sender_cache[method] = _replay_open_loop_sender(trace, cfg, phase4_plan, params, method)
        result = sender_cache[method]
        for rec in result["records"]:
            if rec["upload"]:
                env = envelope_from_record(rec, layout_id=1)
                frame = encode(env, layout_id=1)
                link.send(float(rec["timestamp"]), frame, env, redundancy_k=1)
    return result, link


def _worker(seed: int, plan: dict, phase4_plan: dict) -> tuple[int, list[dict]]:
    cfg = load()
    params = ClosedLoopParams(**plan["params"])
    regimes = load_e220_regimes()
    rows = []

    for sc in SCENARIOS:
        tr = ma_trace(phase4_plan["ma1_plan"], seed, sc)
        cf = counterfactual(tr) if tr.faults else None
        sender_cache: dict = {}
        cf_cache: dict = {}
        for rid in REGIME_ORDER:
            hw_runs = regimes[rid]
            hw_prof = hw_runs[seed % len(hw_runs)]
            for m in METHODS:
                cf_bundle = None
                if cf is not None:
                    cf_bundle = _replay_trace_link(
                        cf, cfg, phase4_plan, params, m, hw_prof, seed, sc + ":cf", cf_cache
                    )
                res, link = _replay_trace_link(
                    tr, cfg, phase4_plan, params, m, hw_prof, seed, sc, sender_cache
                )
                metrics = _evaluate_run(tr, res, link, cfg, plan, cf_bundle=cf_bundle)
                rows.append(
                    dict(
                        seed=seed,
                        cohort="e220_hw_trace",
                        scenario=sc,
                        method=m,
                        regime_id=rid,
                        hw_run_id=hw_prof.run_id,
                        hw_raw_sha256=hw_prof.raw_sha256,
                        e220_airtime_s=link.total_airtime_ms / 1000.0,
                        **metrics,
                    )
                )
    return seed, rows


def _make_figure(df: pd.DataFrame, plan: dict) -> None:
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
    labels = ["E220 Random 20%", "E220 Random 30%", "E220 Burst 20%", "E220 Burst 30%"]
    x = np.arange(len(REGIME_ORDER))
    rng = np.random.default_rng(plan["bootstrap_seed"])

    fig, axes = plt.subplots(1, 3, figsize=(16.5, 4.8))
    for m in METHODS:
        f1_m, f1_lo, f1_hi = [], [], []
        aoi_m, aoi_lo, aoi_hi = [], [], []
        air_m = []
        for rid in REGIME_ORDER:
            g = df[(df["method"] == m) & (df["regime_id"] == rid)]
            st = seed_table(g)
            idx = rng.integers(0, len(st), (2000, len(st)))
            v1 = st["receiver_f1"].to_numpy() * 100.0
            v2 = st["finite_age_p95_s"].to_numpy()
            f1_m.append(v1.mean())
            l1, h1 = np.percentile(v1[idx].mean(axis=1), [2.5, 97.5])
            f1_lo.append(v1.mean() - l1)
            f1_hi.append(h1 - v1.mean())
            aoi_m.append(v2.mean())
            l2, h2 = np.percentile(v2[idx].mean(axis=1), [2.5, 97.5])
            aoi_lo.append(v2.mean() - l2)
            aoi_hi.append(h2 - v2.mean())
            air_m.append(g.groupby("seed")["e220_airtime_s"].sum().mean())
        lw = 2.4 if m == "JALC-Full" else 1.4
        axes[0].errorbar(x, f1_m, yerr=[f1_lo, f1_hi], fmt="o-", lw=lw, ms=4, capsize=2, label=m, color=COLORS[m])
        axes[1].errorbar(x, aoi_m, yerr=[aoi_lo, aoi_hi], fmt="o-", lw=lw, ms=4, capsize=2, label=m, color=COLORS[m])
        axes[2].plot(x, air_m, "o-", lw=lw, ms=4, label=m, color=COLORS[m])

    axes[0].set(ylabel="Receiver F1 (%)", title="Detection under E220 Hardware Traces", ylim=(30, 82))
    axes[1].set(ylabel="Mean Run-P95 Finite AoI (s)", title="Freshness under E220 Hardware Traces")
    axes[1].axhline(45.0, color="black", ls="--", lw=0.9)
    axes[2].set(ylabel="Total Measured E220 RF Airtime / seed (s)", title="Physical E220 TX Airtime (30.4 ms/frame)")
    for ax in axes:
        ax.set_xticks(x, labels, rotation=18, ha="right")
    axes[2].legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)
    fig.suptitle("Phase 5.5: Real ESP32-S3 + E220-400T22D Hardware-Trace-Driven Link Validation (20 held-out seeds 1200-1219)", fontsize=11.5)
    fig.tight_layout(rect=(0, 0, 0.90, 0.92))
    fig.savefig(OUT_DIR / "fig05_e220_hardware_trace_validation.png", dpi=180)
    fig.savefig(OUT_DIR / "fig05_e220_hardware_trace_validation.pdf")
    plt.close(fig)


def main() -> None:
    audit = audit_hw_seeds()
    print("Seed audit:", audit["status"], "max_existing:", audit["max_existing_seed"])

    plan = json.loads((ROOT / "configs/phase5_boundary.json").read_text())
    phase4_plan = json.loads((ROOT / "configs/phase4.json").read_text())

    all_rows = []
    with ProcessPoolExecutor(max_workers=4, mp_context=multiprocessing.get_context("spawn")) as pool:
        futs = [pool.submit(_worker, s, plan, phase4_plan) for s in SEEDS]
        for fut in as_completed(futs):
            s, srows = fut.result()
            all_rows.extend(srows)
            print(f"[e220_hw_trace] seed {s}: {len(srows)} runs complete", flush=True)

    df = pd.DataFrame(all_rows).sort_values(["seed", "regime_id", "scenario", "method"])
    df.to_csv(OUT_DIR / "metrics.csv", index=False)

    jalc = df[df["method"].str.startswith("JALC-")]
    assert (jalc["fast_window_max"] <= 6).all()

    # Summary by regime and overall
    summary_rows = []
    for m, g in df.groupby("method"):
        row = dict(regime="all_e220", method=m, **aggregate(g))
        row["mean_airtime_s_per_seed"] = float(g.groupby("seed")["e220_airtime_s"].sum().mean())
        summary_rows.append(row)
    for (rid, m), g in df.groupby(["regime_id", "method"]):
        row = dict(regime=rid, method=m, **aggregate(g))
        row["mean_airtime_s_per_seed"] = float(g.groupby("seed")["e220_airtime_s"].sum().mean())
        summary_rows.append(row)
    pd.DataFrame(summary_rows).to_csv(OUT_DIR / "summary.csv", index=False)

    # Paired seed-cluster Bootstrap + Sign-Flip + Holm
    contrasts = [
        ("JALC-Full", "A5"),
        ("JALC-Full", "A7"),
        ("JALC-Full", "Risk-T1-U1"),
        ("JALC-Full", "Fixed-20"),
        ("JALC-Full", "JALC-AoI"),
    ]
    endpoints = ["receiver_f1", "finite_age_p95_s", "aoi_violation_45s_rate", "sent_bytes", "receiver_fi"]
    frames = [paired_inference(df, plan, contrasts, endpoints, "all_e220")]
    for rid in REGIME_ORDER:
        frames.append(paired_inference(df[df["regime_id"] == rid], plan, contrasts, endpoints, rid))
    effects = pd.concat(frames, ignore_index=True)
    effects["p_holm"] = holm(effects["p_signflip"])
    effects["holm_sig_005"] = effects["p_holm"] < 0.05
    effects.to_csv(OUT_DIR / "paired_effects.csv", index=False)

    _make_figure(df, plan)

    manifest = dict(
        status="COMPLETE",
        seeds=SEEDS,
        scenarios=SCENARIOS,
        regimes=REGIME_ORDER,
        runs=len(df),
        e220_traces_sha256=hashlib.sha256((ROOT / "configs/e220_hardware_traces.json").read_bytes()).hexdigest(),
        metrics_sha256=hashlib.sha256((OUT_DIR / "metrics.csv").read_bytes()).hexdigest(),
    )
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"COMPLETE: {len(df)} runs, {len(effects)} Holm-adjusted tests saved to {OUT_DIR}")


if __name__ == "__main__":
    main()
