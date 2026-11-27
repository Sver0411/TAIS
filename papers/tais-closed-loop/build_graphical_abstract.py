"""Generate a clean 3:2 Graphical Abstract tailored for the official IEEE Sensors Journal template."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

OUT_DIR = Path("/Users/mac/Documents/TAIS/papers/tais-closed-loop-v2")

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.edgecolor": "#334155",
    "axes.linewidth": 0.7,
})

fig = plt.figure(figsize=(6.0, 3.55), dpi=300, facecolor="white")

# Top title strip
fig.text(
    0.5, 0.955,
    "TAIS-JALC + Causal Spatial k-NN for Reliable IoT Sensing",
    ha="center", va="top", fontsize=9.8, fontweight="bold", color="#0B4F6C"
)
fig.text(
    0.5, 0.905,
    "32,240 Runs  |  ESP32-S3 C11 (3.25 KB RAM)  |  24 E220 Logs  |  54-Mote Intel Data",
    ha="center", va="top", fontsize=6.8, color="#475569"
)

# Top pipeline band (y: 0.67 to 0.85)
ax_top = fig.add_axes([0.02, 0.67, 0.96, 0.18])
ax_top.set_xlim(-0.10, 10.10)
ax_top.set_ylim(0, 2)
ax_top.axis("off")

boxes = [
    (0.05, 2.25, "#EBF5FB", "#1F618D", "SensorTrust C11\nHealth Gating"),
    (2.60, 2.35, "#E8F8F5", "#117A65", "TAIS-JALC 4+1 FSM\nAoI Reserve + K=2"),
    (5.25, 2.15, "#FEF9E7", "#B7950B", "Lossy LoRa / E220\nBinary v1 (0 B Heap)"),
    (7.70, 2.25, "#F4ECF7", "#6C3483", "Spatial k-NN Layer\nDrift vs. Env Ramp"),
]
for x, w, fc, ec, txt in boxes:
    patch = FancyBboxPatch(
        (x, 0.22), w, 1.56,
        boxstyle="round,pad=0.06,rounding_size=0.14",
        facecolor=fc, edgecolor=ec, linewidth=1.1
    )
    ax_top.add_patch(patch)
    ax_top.text(
        x + w / 2, 1.0, txt,
        ha="center", va="center", fontsize=6.7, fontweight="bold", color="#0F172A",
        linespacing=1.25
    )

for x1, x2 in [(2.32, 2.58), (4.97, 5.23), (7.42, 7.68)]:
    ax_top.annotate(
        "", xy=(x2, 1.0), xytext=(x1, 1.0),
        arrowprops=dict(arrowstyle="-|>", color="#334155", lw=1.1, mutation_scale=8)
    )

# Bottom-left: E220 hardware-trace replay (F1 + P95 AoI)
ax1 = fig.add_axes([0.08, 0.17, 0.34, 0.41])
methods = ["Fixed-20\n-TU", "Fixed-20", "JALC\n-AoI", "JALC\n-Full"]
f1_vals = [57.62, 56.09, 61.61, 65.33]
aoi_vals = [225.92, 86.86, 134.11, 46.39]
colors = ["#B05B8E", "#8E9AAF", "#2A9D8F", "#0B5394"]
x = np.arange(len(methods))

bars = ax1.bar(x, f1_vals, width=0.56, color=colors, edgecolor="none", zorder=2)
ax1.set_ylim(42, 73)
ax1.set_xticks(x)
ax1.set_xticklabels(methods, fontsize=6.4)
ax1.set_ylabel("Rx F1 (%)", fontsize=6.8, color="#0B5394", fontweight="bold")
ax1.tick_params(axis="y", labelsize=6.2, colors="#0B5394")
ax1.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6, zorder=1)
ax1.spines["top"].set_visible(False)
ax1.set_title("E220 Trace Replay (Pooled 4 Regimes)", fontsize=7.3, fontweight="bold", color="#0B4F6C", pad=5)

for xi, v in zip(x, f1_vals):
    ax1.text(xi, v + 0.9, f"{v:.1f}%", ha="center", va="bottom", fontsize=5.8, fontweight="bold", color="#1E293B")

ax1b = ax1.twinx()
ax1b.plot(x, aoi_vals, color="#C0392B", marker="o", markersize=4.0, linewidth=1.4, linestyle="--", zorder=4)
ax1b.set_ylim(0, 275)
ax1b.set_ylabel("P95 AoI (s)", fontsize=6.8, color="#C0392B", fontweight="bold")
ax1b.tick_params(axis="y", labelsize=6.2, colors="#C0392B")
ax1b.spines["top"].set_visible(False)
offsets = [12, 12, 12, 12]
for xi, av, dy in zip(x, aoi_vals, offsets):
    ax1b.text(
        xi, av + dy, f"{av:.0f}s", ha="center", va="bottom", fontsize=5.8,
        fontweight="bold", color="white",
        bbox=dict(boxstyle="round,pad=0.14", fc="#C0392B", ec="none", alpha=0.92),
        zorder=5
    )

fig.text(
    0.27, 0.035,
    "Pareto win vs. Fixed-20: +9.5 pp F1, -46.6% AoI, -5.1% TX cost",
    ha="center", va="bottom", fontsize=6.1, style="italic", color="#334155"
)

# Bottom-right: 54-Mote Spatial k-NN (12 Held-Out Days)
ax2 = fig.add_axes([0.62, 0.17, 0.36, 0.41])
cats = ["Drift ID\n(H1)", "Common\nRamp", "Drift+\nFast", "Local\nSlow (H3)"]
sc = [0.0, 85.8, 23.3, 85.8]
sk = [88.3, 85.8, 88.3, 30.8]
ns = [87.5, 40.4, 88.3, 40.4]
xc = np.arange(len(cats))
w = 0.25

ax2.bar(xc - w, sc, width=w, color="#D9534F", label="SingleChannel", zorder=2)
ax2.bar(xc,     sk, width=w, color="#0B5394", label="SpatialKNN", zorder=2)
ax2.bar(xc + w, ns, width=w, color="#94A3B8", label="NullSpatial", zorder=2)
ax2.set_ylim(0, 115)
ax2.set_xticks(xc)
ax2.set_xticklabels(cats, fontsize=6.3)
ax2.set_ylabel("Rate (%)", fontsize=6.8, fontweight="bold", color="#1E293B")
ax2.tick_params(axis="y", labelsize=6.2)
ax2.grid(axis="y", linestyle=":", linewidth=0.5, alpha=0.6, zorder=1)
ax2.spines["top"].set_visible(False)
ax2.spines["right"].set_visible(False)
ax2.set_title("54-Mote Spatial k-NN (12 Held-Out Days)", fontsize=7.3, fontweight="bold", color="#0B4F6C", pad=5)
ax2.legend(loc="upper right", fontsize=5.6, frameon=True, framealpha=0.9, borderpad=0.25, handlelength=1.1)

fig.text(
    0.78, 0.035,
    "-75% drift FA  |  +45.4 pp vs. NullSpatial  |  H3 boundary",
    ha="center", va="bottom", fontsize=6.1, style="italic", color="#334155"
)

fig.savefig(OUT_DIR / "graphical_abstract.pdf", bbox_inches="tight", pad_inches=0.04)
fig.savefig(OUT_DIR / "graphical_abstract.png", dpi=300, bbox_inches="tight", pad_inches=0.04)
plt.close(fig)
print("Generated graphical_abstract.pdf and graphical_abstract.png successfully.")
