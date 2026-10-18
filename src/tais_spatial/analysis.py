"""Predeclared paired date-cluster summaries and scientific figures."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

GROUP = ["variable", "case", "reference_shift_s", "reference_max_age_s", "multiplier", "method"]
PAIR = ["date", "node", "variable", "case", "reference_shift_s", "reference_max_age_s", "multiplier"]
METRICS = ["reports", "event_incremental_hit", "event_window_hit", "drift_extra_net", "drift_added_reports",
           "drift_outside_event_net", "incremental_delay_minutes", "reference_quorum_coverage",
           "application_requests", "application_bytes"]


def bootstrap(differences, repetitions, seed):
    differences = np.asarray(differences, dtype=float)
    rng = np.random.default_rng(seed)
    means = differences[rng.integers(0, len(differences), size=(repetitions, len(differences)))].mean(axis=1)
    return float(differences.mean()), *np.quantile(means, [0.025, 0.975]).tolist()


def summarize(directory):
    directory = Path(directory)
    if (directory/"summary.csv").exists():
        raise FileExistsError("Analysis outputs already exist; do not silently replace")
    manifest = json.loads((directory/"manifest.json").read_text()); config = manifest["config"]
    df = pd.read_csv(directory/"node-metrics.csv.gz")
    summaries = []
    for keys, g in df.groupby(GROUP, sort=True):
        row = dict(zip(GROUP, keys)); event_n = int(g.event_requested.sum())
        opportunity = g.event_realized_opportunity.eq(1)
        row.update(node_days=len(g), dates=g.date.nunique(), reports=int(g.reports.sum()),
                   event_requests=event_n, event_opportunities=int(opportunity.sum()),
                   event_incremental_hits=int(g.event_incremental_hit.sum()),
                   event_window_hits=int(g.event_window_hit.sum()),
                   incremental_recall=float(g.event_incremental_hit.sum()/event_n) if event_n else None,
                   window_recall=float(g.event_window_hit.sum()/event_n) if event_n else None,
                   opportunity_incremental_recall=float(g.loc[opportunity, "event_incremental_hit"].mean()) if opportunity.any() else None,
                   missed_incremental=event_n-int(g.event_incremental_hit.sum()) if event_n else None,
                   mean_incremental_delay_minutes=float(g.incremental_delay_minutes.mean()),
                   drift_extra_net=float(g.drift_extra_net.mean()),
                   drift_added_reports=float(g.drift_added_reports.mean()),
                   target_coverage=float(g.target_scoring_coverage.mean()),
                   reference_slot_coverage=float(g.reference_slot_coverage.mean()),
                   reference_quorum_coverage=float(g.reference_quorum_coverage.mean()))
        for col in ["application_requests", "application_bytes", "reference_requests", "reference_payload_bytes",
                    "target_poll_attempts", "target_values_used", "target_distinct_rows", "target_cached_reuses",
                    "reference_values_used", "reference_distinct_current_rows"]:
            row["mean_"+col] = float(g[col].mean())
        summaries.append(row)
    pd.DataFrame(summaries).to_csv(directory/"summary.csv", index=False, na_rep="N/A")
    spatial = df[df.method.eq("Spatial")].set_index(PAIR)
    comparisons = []
    group_pair = ["variable", "case", "reference_shift_s", "reference_max_age_s", "multiplier"]
    for comparator in ["HistoryShort", "HistoryExtended", "NullSpatial"]:
        control = df[df.method.eq(comparator)].set_index(PAIR)
        assert spatial.index.equals(control.index)
        for metric in METRICS:
            delta = (spatial[metric]-control[metric]).rename("delta").reset_index()
            for keys, group in delta.groupby(group_pair, sort=True):
                valid = group.dropna(subset=["delta"])
                if valid.empty:
                    continue
                per_day = valid.groupby("date").delta.mean()
                material = f"{config['bootstrap_seed']}:{comparator}:{metric}:{keys}".encode()
                seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "little")
                mean, lo, hi = bootstrap(per_day.to_numpy(), config["bootstrap_repetitions"], seed)
                row = dict(zip(group_pair, keys))
                row.update(method="Spatial", comparator=comparator, metric=metric,
                           paired_node_days=len(valid), independent_dates=len(per_day),
                           paired_difference=mean, ci95_low=lo, ci95_high=hi,
                           date_differences=json.dumps(per_day.to_dict(), sort_keys=True))
                comparisons.append(row)
    pd.DataFrame(comparisons).to_csv(directory/"paired-differences.csv", index=False)
    primary = df[(df.reference_shift_s == 0) & (df.reference_max_age_s == 900) & (df.multiplier == 1)]
    coverage = primary[(primary.method == "Spatial") & (primary.case == "untouched")]
    # A nonzero *benefit or harm* is informative; positivity is not required.
    comparison = df[(df.reference_shift_s == 0) & (df.reference_max_age_s == 900)]
    pivot = comparison.pivot(index=PAIR, columns="method", values="reports")
    differs = bool(((pivot.Spatial != pivot.HistoryExtended) | (pivot.Spatial != pivot.NullSpatial)).any())
    gate = {"independent_dates": int(coverage.date.nunique()),
            "mean_target_coverage": float(coverage.target_scoring_coverage.mean()),
            "mean_reference_quorum_coverage": float(coverage.reference_quorum_coverage.mean()),
            "spatial_outputs_differ_from_history_or_null": differs}
    rules = config["development_gate"]
    gate["coverage_pass"] = (gate["independent_dates"] >= rules["minimum_days"]
                             and gate["mean_target_coverage"] >= rules["minimum_target_coverage"]
                             and gate["mean_reference_quorum_coverage"] >= rules["minimum_reference_coverage"])
    gate["informative_exploration_pass"] = gate["coverage_pass"] and differs
    gate["not_evidence_of_superiority"] = True
    (directory/"gate.json").write_text(json.dumps(gate, indent=2)+"\n")
    plot(directory)
    return gate


def plot(directory):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import gzip

    directory = Path(directory); df = pd.read_csv(directory/"summary.csv", na_values="N/A")
    primary = df[(df.reference_shift_s == 0) & (df.reference_max_age_s == 900)]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), constrained_layout=True)
    for ax, variable in zip(axes, ["temperature", "humidity"]):
        for method, g in primary[(primary.variable == variable) & (primary.case == "local_fast")].groupby("method"):
            g = g.sort_values("multiplier")
            ax.plot(g.mean_application_requests, g.incremental_recall, "o-", label=method)
            for _, row in g.iterrows():
                ax.annotate(f"x{row.multiplier:g}", (row.mean_application_requests, row.incremental_recall), fontsize=7)
        ax.set(xlabel="Assumed application requests / node-day", ylabel="Incremental local-fast recall",
               title=variable, ylim=(-0.03, 1.03)); ax.grid(alpha=.2)
    axes[0].legend(fontsize=8)
    fig.suptitle("Offline controlled interventions: requests include reference RPCs")
    fig.savefig(directory/"cost-recall.png", dpi=160); plt.close(fig)

    paired = pd.read_csv(directory/"paired-differences.csv")
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), constrained_layout=True)
    for i, variable in enumerate(["temperature", "humidity"]):
        for j, (metric, case) in enumerate([("drift_extra_net", "drift"), ("event_incremental_hit", "local_fast")]):
            g = paired[(paired.variable == variable) & (paired.comparator == "HistoryExtended")
                       & (paired.metric == metric) & (paired.case == case) & (paired.multiplier == 1)]
            table = g.pivot(index="reference_shift_s", columns="reference_max_age_s", values="paired_difference")
            ax = axes[i, j]; im = ax.imshow(table, cmap="coolwarm", aspect="auto")
            ax.set_xticks(range(len(table.columns)), [f"{a/60:g}" for a in table.columns])
            ax.set_yticks(range(len(table.index)), [f"{a/60:g}" for a in table.index])
            for rr in range(len(table.index)):
                for cc in range(len(table.columns)):
                    ax.text(cc, rr, f"{table.iloc[rr,cc]:+.3f}", ha="center", va="center", fontsize=8)
            ax.set(xlabel="Maximum reference age (proxy min)", ylabel="Reference clock shift (min)",
                   title=f"{variable}: {metric}\nSpatial minus HistoryExtended")
            fig.colorbar(im, ax=ax, shrink=.75)
    fig.suptitle("All nine declared clock/age assumptions, multiplier 1")
    fig.savefig(directory/"time-sensitivity.png", dpi=160); plt.close(fig)

    traces = []
    with gzip.open(directory/"example-traces.jsonl.gz", "rt") as f:
        for line in f:
            traces.append(json.loads(line))
    if traces:
        t = pd.DataFrame(traces); cases = list(dict.fromkeys(t.case))
        fig, axes = plt.subplots(5, 3, figsize=(14, 15), constrained_layout=True)
        colors = {"HistoryShort": "#333333", "HistoryExtended": "#e69f00", "Spatial": "#0072b2", "NullSpatial": "#cc79a7"}
        for ax, case in zip(axes.flat, cases):
            one = t[(t.case == case) & (t.method == "HistoryShort")]
            ax.plot(one.minutes/60, one.target, color="#777777", lw=1)
            for method, color in colors.items():
                g = t[(t.case == case) & (t.method == method) & t.report]
                ax.scatter(g.minutes/60, g.target, color=color, s=20, label=method)
            ax.set(title=case, xlabel="Naive proxy hour", ylabel="Temperature (C)"); ax.grid(alpha=.2)
        for ax in list(axes.flat)[len(cases):]:
            ax.set_visible(False)
        axes.flat[0].legend(fontsize=7)
        fig.suptitle(f"Preselected example: AF29, {t.date.iloc[0]}, primary alignment / multiplier 1")
        fig.savefig(directory/"example-trajectories.png", dpi=140); plt.close(fig)


def update_checksums(directory):
    directory = Path(directory); p = directory/"manifest.json"; manifest = json.loads(p.read_text())
    manifest["artifacts"] = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
                             for f in sorted(directory.iterdir()) if f.is_file() and f.name != "manifest.json"}
    p.write_text(json.dumps(manifest, indent=2)+"\n")
