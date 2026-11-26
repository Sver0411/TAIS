#!/usr/bin/env python3
"""Generate IEEE Sensors Journal double-column (7.16 in) print-ready vector PDF figures.

Reads strictly from frozen saved CSV/JSON results without altering any experiment data.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
FIG_DIR = Path(__file__).resolve().parent / "figures"
FIG_DIR.mkdir(parents=True, exist_ok=True)

IEEE_W = 7.16  # Standard IEEEtran two-column textwidth in inches

plt.rcParams.update(
    {
        "font.family": "serif",
        "font.serif": ["DejaVu Serif", "Times New Roman", "Times"],
        "mathtext.fontset": "stix",
        "font.size": 8.0,
        "axes.titlesize": 8.2,
        "axes.labelsize": 8.0,
        "xtick.labelsize": 7.4,
        "ytick.labelsize": 7.4,
        "legend.fontsize": 7.2,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.65,
        "grid.alpha": 0.22,
        "grid.linewidth": 0.45,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
    }
)

# Colorblind-safe & grayscale-distinguishable styles (distinct markers + linestyles)
DISPLAY_NAME = {
    "Fixed-20":     "Fixed-20",
    "A5":           "Fixed-20-TU",
    "A7":           "Adapt-TU",
    "Risk-T1-U1":   "Risk-OpenLoop",
    "JALC-ObsOnly": "JALC-ObsOnly",
    "JALC-AoI":     "JALC-AoI",
    "JALC-Full":    "JALC-Full",
}

STYLES = {
    "JALC-Full":    dict(color="#004488", marker="o", ls="-",  lw=1.7, ms=4.2, zorder=6),
    "JALC-AoI":     dict(color="#228833", marker="s", ls="-",  lw=1.2, ms=3.7, zorder=5),
    "Fixed-20":     dict(color="#555555", marker="^", ls="--", lw=1.1, ms=3.9, zorder=4),
    "A5":           dict(color="#aa3377", marker="D", ls="-.", lw=1.1, ms=3.5, zorder=4),
    "A7":           dict(color="#cc3311", marker="v", ls=":",  lw=1.1, ms=3.7, zorder=3),
    "Risk-T1-U1":   dict(color="#6699cc", marker="P", ls="--", lw=1.0, ms=3.6, zorder=3),
    "JALC-ObsOnly": dict(color="#ee7733", marker="X", ls="-.", lw=1.0, ms=3.6, zorder=3),
}


def _seed_ci(df: pd.DataFrame, group_cols: list[str], metric: str, seed_col: str = "seed", n_boot: int = 2000):
    """Return mean and (lo, hi) 95% cluster-bootstrap CI."""
    rng = np.random.default_rng(20261126)
    out = {}
    for key, g in df.groupby(group_cols):
        if metric == "rx_f1_micro":
            per = g.groupby(seed_col).apply(
                lambda s: 200.0 * s["receiver_tp"].sum() / max(1, s["n_events"].sum() + s["receiver_tp"].sum() + s["receiver_fp"].sum()),
                include_groups=False,
            ).to_numpy(dtype=float)
        elif metric == "airtime_per_seed":
            per = g.groupby(seed_col)["e220_airtime_s"].sum().to_numpy(dtype=float)
        else:
            per = g.groupby(seed_col)[metric].mean().to_numpy(dtype=float)
        m = float(per.mean())
        idx = rng.integers(0, len(per), size=(n_boot, len(per)))
        lo, hi = np.percentile(per[idx].mean(axis=1), [2.5, 97.5])
        out[key] = (m, max(0.0, m - float(lo)), max(0.0, float(hi) - m))
    return out


def build_fig02_dynamics() -> None:
    """Fig 2: Held-out Final Axis A 5x5 duration x amplitude heatmaps (4 crisp panels)."""
    df = pd.read_csv(ROOT / "results/phase5/analysis/axis_a_grid_final.csv")
    durs = [10, 20, 45, 120, 600]
    amps = [2.5, 1.5, 1.0, 0.75, 0.5]  # top to bottom

    def grid(method: str) -> np.ndarray:
        sub = df[df["method"] == method]
        mat = np.zeros((len(amps), len(durs)))
        for i, a in enumerate(amps):
            for j, d in enumerate(durs):
                row = sub[(sub["duration_s"] == d) & (np.isclose(sub["amplitude"], a))]
                mat[i, j] = float(row["receiver_f1"].iloc[0]) * 100.0 if len(row) else 0.0
        return mat

    m_a5 = grid("A5")
    m_a7 = grid("A7")
    m_full = grid("JALC-Full")
    m_diff = m_full - m_a5

    fig, axes = plt.subplots(1, 4, figsize=(IEEE_W, 2.15), constrained_layout=True)
    panels = [
        (axes[0], m_a5,   "(a) Fixed-20-TU",         "viridis", 0, 100, False),
        (axes[1], m_a7,   "(b) Adapt-TU",            "viridis", 0, 100, False),
        (axes[2], m_full, "(c) JALC-Full (Ours)",    "viridis", 0, 100, False),
        (axes[3], m_diff, r"(d) $\Delta$F1: JALC $-$ Fixed-20-TU", "RdBu", -25, 25, True),
    ]
    for idx, (ax, mat, title, cmap, vmin, vmax, is_diff) in enumerate(panels):
        im = ax.imshow(mat, cmap=cmap, vmin=vmin, vmax=vmax, aspect="auto")
        ax.set_title(title, pad=4)
        ax.set_xticks(range(len(durs)))
        ax.set_xticklabels([str(d) for d in durs])
        ax.set_xlabel("Duration (s)")
        ax.set_yticks(range(len(amps)))
        if idx == 0:
            ax.set_yticklabels([f"{a:g}x" for a in amps])
            ax.set_ylabel("Amplitude")
        else:
            ax.set_yticklabels([])
        for i in range(len(amps)):
            for j in range(len(durs)):
                val = mat[i, j]
                if is_diff:
                    txt = f"{val:+.0f}" if abs(val) >= 0.5 else "0"
                    col = "white" if abs(val) > 13 else "black"
                else:
                    txt = f"{val:.0f}"
                    col = "black" if val > 58 else "white"
                ax.text(j, i, txt, ha="center", va="center", fontsize=6.7, color=col, fontweight="bold" if (is_diff and val >= 8) else "normal")
        if idx in (2, 3):
            cb = fig.colorbar(im, ax=ax, fraction=0.055, pad=0.03)
            cb.ax.tick_params(labelsize=6.6)
            cb.set_label("pp" if is_diff else "F1 (%)", fontsize=6.8)

    fig.savefig(FIG_DIR / "fig02_dynamics_boundary.pdf")
    plt.close(fig)


def build_fig03_links() -> None:
    """Fig 3: Held-out Final Axis B link degradation boundary (2x3 grid, top shared legend)."""
    df = pd.read_csv(ROOT / "results/phase5/final/metrics.csv")
    df = df[df["cohort"] == "axis_b"].copy()
    losses = ["loss_0", "loss_5", "loss_15", "loss_30", "burst_ge"]
    loss_lbls = ["0%", "5%", "15%", "30%", "GE"]
    bws = [np.inf, 1200.0, 600.0]
    bw_titles = ["(a) Unlimited BW", "(b) BW Cap: 1200 B/min", "(c) BW Cap: 600 B/min"]
    methods = ["Fixed-20", "A5", "A7", "Risk-T1-U1", "JALC-ObsOnly", "JALC-AoI", "JALC-Full"]

    ci_f1 = _seed_ci(df, ["bandwidth_bpm", "loss_id", "method"], "rx_f1_micro")
    ci_aoi = _seed_ci(df, ["bandwidth_bpm", "loss_id", "method"], "finite_age_p95_s")

    fig, axes = plt.subplots(2, 3, figsize=(IEEE_W, 3.25), sharex=True)
    x = np.arange(len(losses))

    for col_i, (bw, btitle) in enumerate(zip(bws, bw_titles)):
        ax_top = axes[0, col_i]
        ax_bot = axes[1, col_i]
        ax_top.set_title(btitle, pad=4)
        for m in methods:
            st = STYLES[m]
            f1_m, f1_lo, f1_hi = [], [], []
            ao_m, ao_lo, ao_hi = [], [], []
            for lid in losses:
                v, lo, hi = ci_f1[(bw, lid, m)]
                f1_m.append(v); f1_lo.append(lo); f1_hi.append(hi)
                v2, lo2, hi2 = ci_aoi[(bw, lid, m)]
                ao_m.append(v2); ao_lo.append(lo2); ao_hi.append(hi2)
            ax_top.errorbar(x, f1_m, yerr=[f1_lo, f1_hi], label=DISPLAY_NAME[m], capsize=1.8, elinewidth=0.65, **st)
            ax_bot.errorbar(x, ao_m, yerr=[ao_lo, ao_hi], label=DISPLAY_NAME[m], capsize=1.8, elinewidth=0.65, **st)

        ax_top.set_ylim(38, 82)
        ax_top.grid(True)
        ax_bot.axhline(45.0, color="#222222", ls="--", lw=0.75, zorder=2)
        ax_bot.set_ylim(0, 225)
        ax_bot.set_xticks(x)
        ax_bot.set_xticklabels(loss_lbls)
        ax_bot.set_xlabel("Link Loss Profile")
        ax_bot.grid(True)
        if col_i == 0:
            ax_top.set_ylabel("Receiver F1 (%)")
            ax_bot.set_ylabel("Run-P95 Finite AoI (s)")
        else:
            ax_top.set_yticklabels([])
            ax_bot.set_yticklabels([])

    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, 0.995), handlelength=1.8, columnspacing=0.9, handletextpad=0.35)
    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.115, top=0.86, wspace=0.08, hspace=0.14)
    fig.savefig(FIG_DIR / "fig03_link_boundary.pdf")
    plt.close(fig)


def build_fig04_e220() -> None:
    """Fig 4: Real ESP32-S3 + E220-400T22D hardware-trace validation (3 crisp panels)."""
    df = pd.read_csv(ROOT / "results/phase5_hw_trace/metrics.csv")
    regimes = ["e220_random_20", "e220_random_30", "e220_burst_20", "e220_burst_30"]
    reg_lbls = ["Rand 20%", "Rand 30%", "Burst 20%", "Burst 30%"]
    methods = ["Fixed-20", "A5", "A7", "Risk-T1-U1", "JALC-ObsOnly", "JALC-AoI", "JALC-Full"]

    ci_f1 = _seed_ci(df, ["regime_id", "method"], "rx_f1_micro")
    ci_aoi = _seed_ci(df, ["regime_id", "method"], "finite_age_p95_s")
    ci_air = _seed_ci(df, ["regime_id", "method"], "airtime_per_seed")

    fig, axes = plt.subplots(1, 3, figsize=(IEEE_W, 2.22))
    x = np.arange(len(regimes))
    for m in methods:
        st = STYLES[m]
        for ax, ci_dict, use_err in [
            (axes[0], ci_f1, True),
            (axes[1], ci_aoi, True),
            (axes[2], ci_air, False),
        ]:
            ys = [ci_dict[(r, m)][0] for r in regimes]
            if use_err:
                los = [ci_dict[(r, m)][1] for r in regimes]
                his = [ci_dict[(r, m)][2] for r in regimes]
                ax.errorbar(x, ys, yerr=[los, his], label=DISPLAY_NAME[m], capsize=1.8, elinewidth=0.65, **st)
            else:
                ax.plot(x, ys, label=DISPLAY_NAME[m], **st)

    axes[0].set(title="(a) Receiver F1", ylabel="Receiver F1 (%)", ylim=(36, 75))
    axes[1].set(title="(b) Data Freshness", ylabel="Run-P95 Finite AoI (s)", ylim=(20, 380))
    axes[1].axhline(45.0, color="#222222", ls="--", lw=0.75, zorder=2)
    axes[2].set(title="(c) Physical E220 RF Airtime", ylabel="Airtime / Seed (s)", ylim=(3.2, 12.2))
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(reg_lbls, rotation=16, ha="right")
        ax.grid(True)

    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=7, frameon=False,
               bbox_to_anchor=(0.5, 0.995), handlelength=1.8, columnspacing=0.9, handletextpad=0.35)
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.19, top=0.80, wspace=0.28)
    fig.savefig(FIG_DIR / "fig04_e220_hardware_traces.pdf")
    plt.close(fig)


def build_fig05_intel_exp_a() -> None:
    """Fig 5: Intel Berkeley coverage audit + Exp A real background x E220 external validity."""
    audit = json.loads((ROOT / "results/phase6_intel_berkeley/data_audit.json").read_text())
    exp_a = pd.read_csv(ROOT / "results/phase6_intel_berkeley/exp_a_metrics.csv")

    calib = {"2004-02-28", "2004-02-29", "2004-03-01"}
    held = {f"2004-03-{d:02d}" for d in range(3, 15)}
    daily = pd.DataFrame(audit["daily_summary"])

    fig, axes = plt.subplots(1, 3, figsize=(IEEE_W, 2.35))

    # Panel (a): Coverage audit
    colors_bar = ["#4477aa" if d in calib else ("#228833" if d in held else "#cccccc") for d in daily["date"]]
    axes[0].bar(range(len(daily)), daily["slot_2min_coverage_54motes"] * 100.0, color=colors_bar, width=0.82)
    axes[0].axhline(50.0, color="#111111", ls="--", lw=0.8)
    axes[0].set(title="(a) 54-Mote Coverage Audit", ylabel="2-min Coverage (%)", xlabel="Date Index (Feb 28–Apr 2)", ylim=(0, 102))
    axes[0].grid(axis="y")
    h_cov = [
        Patch(color="#4477aa", label="Calib (3d)"),
        Patch(color="#228833", label="Held-out (12d)"),
        Patch(color="#cccccc", label="Excluded"),
    ]
    axes[0].legend(handles=h_cov, fontsize=6.4, loc="upper right", frameon=True, framealpha=0.9, borderpad=0.3)

    # Panel (b) & (c): Exp A F1 & Real Wall-Clock P95 AoI
    methods_a = ["Fixed-20", "A5", "A7", "JALC-AoI", "JALC-Full"]
    links = ["loss_0", "e220_burst_20", "e220_random_30"]
    link_lbls = ["Lossless", "E220 Burst 20%", "E220 Rand 30%"]
    x = np.arange(len(links))

    for m in methods_a:
        st = STYLES[m]
        f1s, aois = [], []
        for lid in links:
            g = exp_a[(exp_a["method"] == m) & (exp_a["link_id"] == lid)]
            tp, fp, n = g["receiver_tp"].sum(), g["receiver_fp"].sum(), g["n_events"].sum()
            f1s.append(200.0 * tp / (n + tp + fp) if (n + tp + fp) else 0.0)
            aois.append(g["real_finite_age_p95_s"].mean() / 60.0)
        axes[1].plot(x, f1s, label=DISPLAY_NAME[m], **st)
        axes[2].plot(x, aois, label=DISPLAY_NAME[m], **st)

    axes[1].set(title="(b) Real BG × E220 F1", ylabel="Receiver F1 (%)", xticks=x, ylim=(39, 62))
    axes[1].set_xticklabels(link_lbls, rotation=12, ha="right")
    axes[1].grid(True)

    axes[2].set(title="(c) Wall-Clock Freshness", ylabel="P95 Finite AoI (min)", xticks=x, ylim=(17, 46))
    axes[2].set_xticklabels(link_lbls, rotation=12, ha="right")
    axes[2].grid(True)

    handles, labels = axes[1].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=5, frameon=False,
               bbox_to_anchor=(0.66, 0.995), handlelength=1.8, columnspacing=1.0, handletextpad=0.35)
    fig.subplots_adjust(left=0.07, right=0.99, bottom=0.20, top=0.80, wspace=0.28)
    fig.savefig(FIG_DIR / "fig05_intel_berkeley_exp_a.pdf")
    plt.close(fig)


def build_fig06_spatial() -> None:
    """Fig 6: Causal spatial k-NN vs SingleChannel & NullSpatial (B&W-safe hatches)."""
    exp_b = pd.read_csv(ROOT / "results/phase6_intel_berkeley/exp_b_metrics.csv")
    modes = ["SingleChannel", "SpatialKNN", "NullSpatial"]

    fig, axes = plt.subplots(1, 2, figsize=(IEEE_W, 2.30), gridspec_kw={"width_ratios": [1.0, 1.48]})

    # Panel (a): False alarms
    sd = exp_b[exp_b["scenario"] == "single_drift"]
    x1 = np.arange(len(modes))
    fe = [sd[sd["method"] == m]["drift_false_env_alarms"].mean() for m in modes]
    cd = [sd[sd["method"] == m]["clean_false_drift_onsets"].mean() for m in modes]
    b1 = axes[0].bar(x1 - 0.18, fe, width=0.34, color="#cc3311", edgecolor="#222222", lw=0.5, hatch="///", alpha=0.85, label="Drift → False Env / run")
    b2 = axes[0].bar(x1 + 0.18, cd, width=0.34, color="#ee8833", edgecolor="#222222", lw=0.5, hatch="...", alpha=0.88, label="Clean-Day Spurious Drift")
    for bars in (b1, b2):
        for bar in bars:
            h = bar.get_height()
            axes[0].text(bar.get_x() + bar.get_width() / 2.0, h + 0.05, f"{h:.2f}", ha="center", va="bottom", fontsize=6.8)
    axes[0].set(title="(a) False Onsets (Lower Better)", xticks=x1, xticklabels=["Single\nChannel", "Spatial\nk-NN", "Null\nSpatial"],
                ylabel="Mean False Onsets / Run", ylim=(0, 2.65))
    axes[0].grid(axis="y")
    axes[0].legend(fontsize=6.6, loc="upper left", frameon=True, framealpha=0.92, borderpad=0.3)

    # Panel (b): 5 scenarios
    scs = ["single_drift", "common_env_event", "local_fast_event", "drift_plus_local_fast", "local_slow_event"]
    sc_lbls = ["Single\nDrift ID", "Common\nEnv Ramp", "Local\nFast", "Drift +\nLocal Fast", "Local Slow\n(H3 Bound)"]
    x2 = np.arange(len(scs))
    w = 0.26
    m_style = {
        "SingleChannel": dict(color="#cc3311", hatch="///", alpha=0.85),
        "SpatialKNN":    dict(color="#004488", hatch="",    alpha=0.95),
        "NullSpatial":   dict(color="#aaaaaa", hatch="...", alpha=0.90),
    }
    for idx_m, m in enumerate(modes):
        vals = []
        for sc in scs:
            sub = exp_b[(exp_b["scenario"] == sc) & (exp_b["method"] == m)]
            col = "drift_correctly_flagged" if sc == "single_drift" else "event_detected"
            vals.append(sub[col].mean() * 100.0)
        bars = axes[1].bar(x2 + (idx_m - 1) * w, vals, width=w, edgecolor="#222222", lw=0.5, label=m, **m_style[m])
        for bar in bars:
            h = bar.get_height()
            axes[1].text(bar.get_x() + bar.get_width() / 2.0, h + 1.6, f"{h:.0f}%", ha="center", va="bottom", fontsize=6.1)

    axes[1].set(title="(b) Identifiability, NullSpatial Control & H3 Boundary", xticks=x2, xticklabels=sc_lbls,
                ylabel="Detection / ID Rate (%)", ylim=(0, 114))
    axes[1].grid(axis="y")
    axes[1].legend(fontsize=6.6, loc="upper right", ncol=3, frameon=True, framealpha=0.92, borderpad=0.25, columnspacing=0.6)

    fig.subplots_adjust(left=0.075, right=0.99, bottom=0.19, top=0.88, wspace=0.20)
    fig.savefig(FIG_DIR / "fig06_spatial_identifiability.pdf")
    plt.close(fig)


if __name__ == "__main__":
    build_fig02_dynamics()
    build_fig03_links()
    build_fig04_e220()
    build_fig05_intel_exp_a()
    build_fig06_spatial()
    print("Built all 5 IEEE print-ready vector PDF figures in", FIG_DIR)
