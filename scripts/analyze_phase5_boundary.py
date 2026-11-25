#!/usr/bin/env python3
"""Phase 5 statistical analysis (paired seed-cluster Bootstrap + Sign-Flip + Holm) & figures."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from analyze_ablation import holm

PLAN_PATH = ROOT / "configs/phase5_boundary.json"
OUT_ROOT = ROOT / "results/phase5"

COLORS = {
    "Fixed-20": "#777777",
    "A5": "#aa3377",
    "A7": "#cc3311",
    "Risk-T1-U1": "#4477aa",
    "JALC-ObsOnly": "#ee7733",
    "JALC-AoI": "#228833",
    "JALC-Full": "#004488",
}


def aggregate(df: pd.DataFrame) -> dict:
    n = df["n_events"].sum()
    stp, sfp = df["sender_tp"].sum(), df["sender_fp"].sum()
    rtp, rfp = df["receiver_tp"].sum(), df["receiver_fp"].sum()
    sf_n, sf_tp = df["receiver_same_fault_n"].sum(), df["receiver_same_fault_tp"].sum()
    return dict(
        n_events=int(n),
        sender_f1=2 * stp / (n + stp + sfp) if (n + stp + sfp) else np.nan,
        sender_recall=stp / n if n else np.nan,
        receiver_f1=2 * rtp / (n + rtp + rfp) if (n + rtp + rfp) else np.nan,
        receiver_recall=rtp / n if n else np.nan,
        receiver_fn=int(n - rtp),
        receiver_restricted_delay_s=df["receiver_restricted_delay_sum_s"].sum() / n if n else np.nan,
        sender_fi=int(df["sender_fault_induced_false"].sum()),
        receiver_fi=int(df["receiver_fault_induced_false"].sum()),
        same_fault_recall=sf_tp / sf_n if sf_n else np.nan,
        samples=int(df["samples"].sum()),
        logical_uploads=int(df["logical_uploads"].sum()),
        tx_attempts=int(df["tx_attempts"].sum()),
        redundant_copies=int(df["redundant_copies"].sum()),
        sent_bytes=int(df["sent_bytes"].sum()),
        loss_drops=int(df["loss_drops"].sum()),
        bw_drops=int(df["bw_drops"].sum()),
        finite_age_mean_s=float(np.average(df["finite_age_mean_s"], weights=df["duration_s"])),
        finite_age_p95_s=float(df["finite_age_p95_s"].mean()),
        aoi_violation_45s_rate=float(df["aoi_violation_45s_rate"].mean()),
        precoverage=float(df["pre_covered_events"].sum() / n) if n else np.nan,
        fast_window_max=int(df["fast_window_max"].max()),
    )


def seed_table(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        [dict(seed=s, method=m, **aggregate(g)) for (s, m), g in df.groupby(["seed", "method"])]
    )


def paired_inference(df: pd.DataFrame, plan: dict, contrasts: list[tuple[str, str]], endpoints: list[str], subset_name: str) -> pd.DataFrame:
    seeds = seed_table(df)
    ids = sorted(seeds["seed"].unique())
    n = len(ids)
    rng = np.random.default_rng(plan["bootstrap_seed"])
    draw = rng.integers(0, n, size=(plan["bootstrap_draws"], n))
    signs = rng.choice([-1, 1], size=(plan["permutation_draws"], n))
    rows = []
    for metric in endpoints:
        pivot = seeds.pivot(index="seed", columns="method", values=metric).loc[ids]
        for a, b in contrasts:
            delta = (pivot[a] - pivot[b]).to_numpy(dtype=float)
            if not np.isfinite(delta).all():
                continue
            lo, hi = np.percentile(delta[draw].mean(axis=1), [2.5, 97.5])
            point = float(delta.mean())
            p = (1 + np.count_nonzero(np.abs(signs @ delta / n) >= abs(point) - 1e-12)) / (len(signs) + 1)
            rows.append(
                dict(
                    subset=subset_name,
                    method=a,
                    reference=b,
                    metric=metric,
                    mean_seed_difference=point,
                    ci95_low=float(lo),
                    ci95_high=float(hi),
                    p_signflip=float(p),
                    seeds=n,
                )
            )
    return pd.DataFrame(rows)


def make_figures(sweep_df: pd.DataFrame, final_df: pd.DataFrame, out_dir: Path, plan: dict) -> None:
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
    fig_dir = out_dir / "figures"
    fig_dir.mkdir(parents=True, exist_ok=True)

    # --- Fig 1: Axis A Event Dynamics Phase Map (5x5 heatmaps) ---
    ax_a = sweep_df[sweep_df["cohort"] == "axis_a"]
    durs = plan["axis_a"]["durations_s"]
    amps = plan["axis_a"]["amplitude_factors"]

    def grid_f1(method_name):
        mat = np.zeros((len(amps), len(durs)))
        sub = ax_a[ax_a["method"] == method_name]
        for i, a in enumerate(amps):
            for j, d in enumerate(durs):
                g = sub[(sub["amplitude_factor"] == a) & (sub["duration_bin_s"] == d)]
                mat[i, j] = aggregate(g)["receiver_f1"] * 100.0
        return mat

    panels = [
        ("A5 (Fixed-20+T+U)", grid_f1("A5"), "viridis", 0, 100),
        ("A7 (Native S+T+U)", grid_f1("A7"), "viridis", 0, 100),
        ("JALC-Full (3D Closed-Loop)", grid_f1("JALC-Full"), "viridis", 0, 100),
        ("Delta F1: JALC-Full - A5 (pp)", grid_f1("JALC-Full") - grid_f1("A5"), "RdBu", -30, 30),
        ("Delta F1: JALC-Full - A7 (pp)", grid_f1("JALC-Full") - grid_f1("A7"), "RdBu", -30, 30),
    ]
    fig, axes = plt.subplots(1, 5, figsize=(19, 4.2))
    for ax, (title, mat, cmap, vmin, vmax) in zip(axes, panels):
        ax.grid(False)
        im = ax.imshow(mat, origin="lower", cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_xticks(range(len(durs)), [str(d) for d in durs])
        ax.set_yticks(range(len(amps)), [f"{a:g}x" for a in amps])
        ax.set_xlabel("Event Duration (s)")
        ax.set_ylabel("Amplitude Multiplier")
        ax.set_title(title, fontsize=9.5)
        for i in range(len(amps)):
            for j in range(len(durs)):
                val = mat[i, j]
                txt_col = "white" if (cmap == "viridis" and val < 45) or (cmap == "RdBu" and abs(val) > 18) else "black"
                ax.text(j, i, f"{val:.0f}", ha="center", va="center", color=txt_col, fontsize=8)
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    fig.suptitle("Phase 5 Axis A: Event Dynamics Effective & Failure Boundary (20 sweep seeds 1020-1039)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(fig_dir / "fig01_axis_a_dynamics_phase_map.png", dpi=180)
    fig.savefig(fig_dir / "fig01_axis_a_dynamics_phase_map.pdf")
    plt.close(fig)

    # --- Fig 2: Axis B Communication Degradation Boundary (Loss x BW) ---
    ax_b = final_df[final_df["cohort"] == "axis_b"]
    loss_order = ["loss_0", "loss_5", "loss_15", "loss_30", "burst_ge"]
    loss_labels = ["0%", "5%", "15%", "30%", "GE-Burst"]
    show_methods = ["Fixed-20", "A5", "A7", "Risk-T1-U1", "JALC-ObsOnly", "JALC-AoI", "JALC-Full"]

    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5), sharex=True)
    for col, bw in enumerate(["inf", "1200", "600"]):
        sub_bw = ax_b[ax_b["bandwidth_bpm"] == bw]
        for m in show_methods:
            f1_vals, f1_lo, f1_hi = [], [], []
            aoi_vals, aoi_lo, aoi_hi = [], [], []
            rng = np.random.default_rng(plan["bootstrap_seed"])
            for lid in loss_order:
                g = sub_bw[(sub_bw["method"] == m) & (sub_bw["loss_id"] == lid)]
                st = seed_table(g)
                idx = rng.integers(0, len(st), (2000, len(st)))
                f1s = st["receiver_f1"].to_numpy() * 100.0
                aois = st["finite_age_p95_s"].to_numpy()
                f1_vals.append(f1s.mean())
                l1, h1 = np.percentile(f1s[idx].mean(axis=1), [2.5, 97.5])
                f1_lo.append(f1s.mean() - l1)
                f1_hi.append(h1 - f1s.mean())
                aoi_vals.append(aois.mean())
                l2, h2 = np.percentile(aois[idx].mean(axis=1), [2.5, 97.5])
                aoi_lo.append(aois.mean() - l2)
                aoi_hi.append(h2 - aois.mean())
            x = np.arange(len(loss_order))
            lw = 2.4 if m == "JALC-Full" else 1.4
            axes[0, col].errorbar(x, f1_vals, yerr=[f1_lo, f1_hi], fmt="o-", lw=lw, ms=4, capsize=2, label=m, color=COLORS[m])
            axes[1, col].errorbar(x, aoi_vals, yerr=[aoi_lo, aoi_hi], fmt="o-", lw=lw, ms=4, capsize=2, label=m, color=COLORS[m])
        bw_title = "Unlimited BW" if bw == "inf" else f"BW Cap = {bw} B/min"
        axes[0, col].set_title(bw_title, fontsize=10.5)
        axes[0, col].set_ylabel("Receiver F1 (%)" if col == 0 else "")
        axes[0, col].set_ylim(20, 85)
        axes[1, col].set_ylabel("Mean Run-P95 Finite AoI (s)" if col == 0 else "")
        axes[1, col].axhline(45.0, color="black", ls="--", lw=1.0, label="45s AoI SLA" if col == 0 else None)
        axes[1, col].set_xticks(range(len(loss_order)), loss_labels)
        axes[1, col].set_xlabel("Link Loss Profile")
    axes[0, 2].legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, frameon=False)
    fig.suptitle("Phase 5 Axis B: Communication Degradation Boundary (Held-out Final 20 seeds 1100-1119)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 0.90, 0.93))
    fig.savefig(fig_dir / "fig02_axis_b_link_degradation_boundary.png", dpi=180)
    fig.savefig(fig_dir / "fig02_axis_b_link_degradation_boundary.pdf")
    plt.close(fig)

    # --- Fig 3: Stepwise Ablation & Pareto (Lossless vs 15% Loss + 600 B/min) ---
    fig, axes = plt.subplots(1, 2, figsize=(13.5, 5.2))
    for ax, lp, title in [
        (axes[0], "loss_0_bw_inf", "Lossless & Unlimited BW (Axis B)"),
        (axes[1], "loss_15_bw_600", "15% Packet Loss + 600 B/min BW Cap (Axis B)"),
    ]:
        sub = ax_b[ax_b["link_profile"] == lp]
        for m in show_methods:
            agg = aggregate(sub[sub["method"] == m])
            sz = 110 if m == "JALC-Full" else 65
            mk = "*" if m == "JALC-Full" else "o"
            ax.scatter(agg["finite_age_p95_s"], agg["receiver_f1"] * 100.0, s=sz, marker=mk, color=COLORS[m], label=f"{m} ({agg['sent_bytes']/1000:.0f} kB)")
            ax.annotate(m, (agg["finite_age_p95_s"], agg["receiver_f1"] * 100.0), xytext=(5, 4), textcoords="offset points", fontsize=7.5)
        ax.axvline(45.0, color="black", ls="--", lw=0.9)
        ax.set_xlabel("Mean Run-P95 Finite-Value AoI (s)  [left is fresher]")
        ax.set_ylabel("Receiver F1 (%)  [up is better]")
        ax.set_title(title)
        ax.legend(loc="lower right", fontsize=7.5, frameon=True)
    fig.suptitle("Stepwise Ablation & Receiver F1 vs. Data Freshness Tradeoff (Held-out Final 1100-1119)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(fig_dir / "fig03_ablation_and_pareto.png", dpi=180)
    fig.savefig(fig_dir / "fig03_ablation_and_pareto.pdf")
    plt.close(fig)

    # --- Fig 4: Slice C Noise & Fault Non-Degradation ---
    sl_c = final_df[(final_df["cohort"] == "slice_c") & (final_df["loss_id"] == "loss_0")]
    sl_c_loss = final_df[(final_df["cohort"] == "slice_c") & (final_df["loss_id"] == "loss_15")]
    fig, axes = plt.subplots(1, 3, figsize=(16, 4.8))
    x = np.arange(len(show_methods))

    # Panel 1: noisy_none samples/seed
    nn_vals = [sl_c[(sl_c["scenario"] == "noisy_none") & (sl_c["method"] == m)]["samples"].mean() for m in show_methods]
    axes[0].bar(x, nn_vals, color=[COLORS[m] for m in show_methods], alpha=0.85)
    axes[0].set_xticks(x, show_methods, rotation=32, ha="right")
    axes[0].set_ylabel("Samples / seed (noisy_none 7x)")
    axes[0].set_title("Noise Over-Sampling Guard (noisy_none)")

    # Panel 2: Operational FI (lossless vs 15% loss)
    fi0 = [sl_c[sl_c["method"] == m]["receiver_fault_induced_false"].sum() / 20.0 for m in show_methods]
    fi15 = [sl_c_loss[sl_c_loss["method"] == m]["receiver_fault_induced_false"].sum() / 20.0 for m in show_methods]
    w = 0.38
    axes[1].bar(x - w / 2, fi0, width=w, label="0% loss", color="#4477aa")
    axes[1].bar(x + w / 2, fi15, width=w, label="15% loss", color="#ee7733")
    axes[1].set_xticks(x, show_methods, rotation=32, ha="right")
    axes[1].set_ylabel("Operational Receiver FI / seed")
    axes[1].set_title("Fault-Induced False Reports (Slice C)")
    axes[1].legend(fontsize=8)

    # Panel 3: Slice C Receiver F1 & P95 AoI at 15% loss
    f1_c = [aggregate(sl_c_loss[sl_c_loss["method"] == m])["receiver_f1"] * 100.0 for m in show_methods]
    axes[2].bar(x, f1_c, color=[COLORS[m] for m in show_methods], alpha=0.85)
    axes[2].set_xticks(x, show_methods, rotation=32, ha="right")
    axes[2].set_ylabel("Receiver F1 (%) at 15% loss")
    axes[2].set_title("Slice C Fault+Noise Rx F1 (15% loss)")

    fig.suptitle("Phase 5 Slice C: Noise & Sensor-Fault Non-Degradation (Held-out Final 1100-1119)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.92))
    fig.savefig(fig_dir / "fig04_slice_c_noise_fault_nondegradation.png", dpi=180)
    fig.savefig(fig_dir / "fig04_slice_c_noise_fault_nondegradation.pdf")
    plt.close(fig)


def analyze(out_root: Path) -> None:
    plan = json.loads(PLAN_PATH.read_text())
    sweep_df = pd.read_csv(out_root / "sweep/metrics.csv", dtype={"bandwidth_bpm": str})
    final_df = pd.read_csv(out_root / "final/metrics.csv", dtype={"bandwidth_bpm": str})
    for df in (sweep_df, final_df):
        df["bandwidth_bpm"] = df["bandwidth_bpm"].fillna("inf").str.replace(r"\.0$", "", regex=True)
    an_dir = out_root / "analysis"
    an_dir.mkdir(parents=True, exist_ok=True)

    # 1. Summary tables for both sweep and final
    for tag, df in [("sweep", sweep_df), ("final", final_df)]:
        rows = []
        for cohort, g_c in df.groupby("cohort"):
            for m, g_m in g_c.groupby("method"):
                rows.append(dict(split=tag, cohort=cohort, subgroup="all", method=m, **aggregate(g_m)))
        # Axis B by loss_id and by link_profile
        ax_b = df[df["cohort"] == "axis_b"]
        for (lid, m), g in ax_b.groupby(["loss_id", "method"]):
            rows.append(dict(split=tag, cohort="axis_b_loss", subgroup=lid, method=m, **aggregate(g)))
        for (lp, m), g in ax_b.groupby(["link_profile", "method"]):
            rows.append(dict(split=tag, cohort="axis_b_profile", subgroup=lp, method=m, **aggregate(g)))
        # Axis A by duration and by amplitude
        ax_a = df[df["cohort"] == "axis_a"]
        for (dur, m), g in ax_a.groupby(["duration_bin_s", "method"]):
            rows.append(dict(split=tag, cohort="axis_a_dur", subgroup=f"d{int(dur)}", method=m, **aggregate(g)))
        for (amp, m), g in ax_a.groupby(["amplitude_factor", "method"]):
            rows.append(dict(split=tag, cohort="axis_a_amp", subgroup=f"a{amp:g}", method=m, **aggregate(g)))
        # Slice C by loss_id and scenario
        sl_c = df[df["cohort"] == "slice_c"]
        for (lid, m), g in sl_c.groupby(["loss_id", "method"]):
            rows.append(dict(split=tag, cohort="slice_c_loss", subgroup=lid, method=m, **aggregate(g)))
        for (sc, m), g in sl_c[sl_c["loss_id"] == "loss_0"].groupby(["scenario", "method"]):
            rows.append(dict(split=tag, cohort="slice_c_sc_loss0", subgroup=sc, method=m, **aggregate(g)))
        pd.DataFrame(rows).to_csv(an_dir / f"summary_{tag}.csv", index=False)

    # 2. Paired seed-cluster Bootstrap + Sign-Flip + Holm on Held-out Final (1100-1119)
    contrasts = [
        ("JALC-Full", "A5"),
        ("JALC-Full", "A7"),
        ("JALC-Full", "Risk-T1-U1"),
        ("JALC-Full", "Fixed-20"),
        ("JALC-Full", "JALC-AoI"),
        ("JALC-Full", "JALC-ObsOnly"),
        ("JALC-AoI", "JALC-ObsOnly"),
        ("JALC-ObsOnly", "A7"),
    ]
    endpoints_core = [
        "receiver_f1",
        "receiver_recall",
        "finite_age_p95_s",
        "aoi_violation_45s_rate",
        "sent_bytes",
        "samples",
    ]
    subsets = [
        ("axis_a_all", final_df[final_df["cohort"] == "axis_a"], endpoints_core),
        ("axis_b_loss0", final_df[(final_df["cohort"] == "axis_b") & (final_df["loss_id"] == "loss_0")], endpoints_core),
        ("axis_b_loss15", final_df[(final_df["cohort"] == "axis_b") & (final_df["loss_id"] == "loss_15")], endpoints_core),
        ("axis_b_loss30", final_df[(final_df["cohort"] == "axis_b") & (final_df["loss_id"] == "loss_30")], endpoints_core),
        ("axis_b_burst", final_df[(final_df["cohort"] == "axis_b") & (final_df["loss_id"] == "burst_ge")], endpoints_core),
        ("axis_b_loss15_bw600", final_df[(final_df["cohort"] == "axis_b") & (final_df["link_profile"] == "loss_15_bw_600")], endpoints_core),
        ("slice_c_loss0", final_df[(final_df["cohort"] == "slice_c") & (final_df["loss_id"] == "loss_0")], endpoints_core + ["receiver_fi"]),
        ("slice_c_loss15", final_df[(final_df["cohort"] == "slice_c") & (final_df["loss_id"] == "loss_15")], endpoints_core + ["receiver_fi"]),
    ]
    effect_frames = [
        paired_inference(sub_df, plan, contrasts, eps, sname)
        for sname, sub_df, eps in subsets
    ]
    effects = pd.concat(effect_frames, ignore_index=True)
    effects["p_holm"] = holm(effects["p_signflip"])
    effects["holm_sig_005"] = effects["p_holm"] < 0.05
    effects.to_csv(an_dir / "paired_effects_final.csv", index=False)

    # 3. Axis A 5x5 cell table for report
    ax_a_cells = []
    for (dur, amp, m), g in final_df[final_df["cohort"] == "axis_a"].groupby(["duration_bin_s", "amplitude_factor", "method"]):
        ax_a_cells.append(dict(duration_s=int(dur), amplitude=amp, method=m, **aggregate(g)))
    pd.DataFrame(ax_a_cells).to_csv(an_dir / "axis_a_grid_final.csv", index=False)

    # 4. Figures
    make_figures(sweep_df, final_df, an_dir, plan)

    outputs = {
        str(p.relative_to(an_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(an_dir.rglob("*"))
        if p.is_file() and p.name != "manifest.json"
    }
    (an_dir / "manifest.json").write_text(
        json.dumps(
            dict(
                status="COMPLETE",
                sweep_runs=len(sweep_df),
                final_runs=len(final_df),
                paired_tests=len(effects),
                outputs=outputs,
            ),
            indent=2,
        )
        + "\n"
    )
    print(f"Analysis complete: sweep={len(sweep_df)} runs, final={len(final_df)} runs, {len(effects)} Holm-adjusted tests, 4 figures")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=OUT_ROOT)
    args = p.parse_args()
    analyze(args.out)
