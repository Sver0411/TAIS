"""Describe already frozen pilot outputs; never replay, fit, or select nodes."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results/offline-spatial-pilot"))
    args = parser.parse_args()
    output = args.results / "audit"
    output.mkdir(exist_ok=False)
    coverage, primary, sensitivity, counts = [], [], [], []
    inputs = {}
    for split in ["development", "validation", "test"]:
        directory = args.results / split
        for filename in ["node-metrics.csv.gz", "summary.csv", "paired-differences.csv", "gate.json"]:
            inputs[f"{split}/{filename}"] = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
        passed = json.loads((directory / "gate.json").read_text())["coverage_pass"]
        status = "exploratory_coverage_pass" if passed else "NO_GO_coverage_failure_diagnostics_only"
        raw = pd.read_csv(directory / "node-metrics.csv.gz")
        p = raw[(raw.reference_shift_s == 0) & (raw.reference_max_age_s == 900) & (raw.multiplier == 1)]
        daily = p[(p.method == "Spatial") & (p.case == "untouched")].groupby("date", as_index=False).agg(
            target_coverage=("target_scoring_coverage", "mean"),
            reference_quorum_coverage=("reference_quorum_coverage", "mean"),
            requested_node_variables=("node", "size"))
        coverage.append(daily.assign(split=split, interpretation=status))
        summary = pd.read_csv(directory / "summary.csv", na_values="N/A")
        primary.append(summary[(summary.reference_shift_s == 0) & (summary.reference_max_age_s == 900)].assign(
            split=split, interpretation=status))
        pairs = pd.read_csv(directory / "paired-differences.csv")
        sensitivity.append(pairs[pairs.multiplier == 1].assign(split=split, interpretation=status))
        # Secondary descriptive checks, not new primary endpoints: offset and
        # reference-only interventions relative to untouched background reports.
        clean = p[p.case == "untouched"].set_index(["date", "node", "variable", "method"]).reports
        for case in ["offset", "reference_fault", "reference_missing"]:
            changed = p[p.case == case].set_index(clean.index.names).reports
            delta = (changed - clean).rename("net_report_change").reset_index()
            delta["case"] = case
            counts.append(delta.assign(split=split, interpretation=status))
    pd.concat(coverage).to_csv(output / "coverage-by-date.csv", index=False)
    pd.concat(primary).to_csv(output / "all-primary-operating-points.csv", index=False, na_rep="N/A")
    pd.concat(sensitivity).to_csv(output / "all-timing-assumptions.csv", index=False)
    pd.concat(counts).to_csv(output / "secondary-report-count-changes.csv", index=False)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), constrained_layout=True, sharey=True)
    for ax, data in zip(axes, coverage):
        x = pd.to_datetime(data.date)
        ax.plot(x, data.target_coverage, "o-", label="Target")
        ax.plot(x, data.reference_quorum_coverage, "s-", label="At least 2 references")
        ax.axhline(.5, color="red", linestyle="--", label="Predeclared split-mean gate")
        ax.set(title=data.split.iloc[0], ylim=(-.03, 1.03), xlabel="Prespecified weekly proxy date")
        ax.tick_params(axis="x", rotation=40); ax.grid(alpha=.2)
    axes[0].set_ylabel("Availability across all 27 nodes and both variables")
    axes[0].legend(fontsize=7)
    fig.suptitle("Held-out coverage failed: no qualified independent effectiveness comparison")
    fig.savefig(output / "coverage-by-date.png", dpi=160); plt.close(fig)
    metadata = {
        "purpose": "Post-replay descriptive audit only; no model, sampling, or data selection",
        "python": platform.python_version(), "platform": platform.platform(),
        "packages": {k: importlib.metadata.version(k) for k in ["numpy", "pandas", "matplotlib", "pytest"]},
        "source_artifact_sha256": inputs,
    }
    (output / "manifest.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps({"status": "written", "output": str(output), "held_out": "NO-GO"}))


if __name__ == "__main__":
    main()
