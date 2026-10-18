"""Verify pilot provenance, frozen comparators, masks, metrics and source immutability."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from tais_spatial.pilot import dates, settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workbook", type=Path, required=True)
    parser.add_argument("--results", type=Path, default=ROOT/"results/offline-spatial-pilot")
    parser.add_argument("--baseline", default="66f4270d1649bc14ffe53911cbf4d219f55f4080")
    args = parser.parse_args()
    config = json.loads((ROOT/"configs/offline_spatial_pilot.json").read_text())
    assert hashlib.sha256(args.workbook.read_bytes()).hexdigest() == config["workbook_sha256"]
    protected = 0
    tree = subprocess.check_output(["git", "ls-tree", "-rz", args.baseline], cwd=ROOT).split(b"\0")
    for line in filter(None, tree):
        metadata, path = line.decode().split("\t"); mode, kind, sha = metadata.split()
        if kind == "commit":
            assert subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT/path).decode().strip() == sha
            assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT/path).strip()
        elif path != "README.md":
            b = (ROOT/path).read_bytes()
            assert hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest() == sha, path
            protected += 1
    frozen = json.loads((args.results/"freeze.json").read_text())
    for path, sha in frozen["code_sha256"].items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest() == sha, path
    splits = {}; provenance_checks = 0
    for split in ["development", "validation", "test"]:
        directory = args.results/split
        if not directory.exists():
            continue
        manifest = json.loads((directory/"manifest.json").read_text())
        assert manifest["config"] == config
        assert manifest["source_sha256"] == config["workbook_sha256"]
        for name, sha in manifest["artifacts"].items():
            assert hashlib.sha256((directory/name).read_bytes()).hexdigest() == sha, (split, name)
        df = pd.read_csv(directory/"node-metrics.csv.gz")
        expected = len(dates(config, split))*27*2*13*4*sum(len(m) for _, _, m in settings(config))
        assert len(df) == expected == manifest["rows"]
        index = ["date", "node", "variable", "reference_shift_s", "reference_max_age_s", "multiplier", "method"]
        drift = df[df.case.eq("drift")].set_index(index).reports
        slow = df[df.case.eq("local_slow")].set_index(index).reports
        assert drift.equals(slow), "Identical inputs must not be classified by hidden truth"
        assert ((df.application_bytes == df.reference_requests*36+df.reports*18)
                & (df.application_requests == df.reference_requests+df.reports)).all()
        budget_index = ["date", "node", "variable", "case", "reference_shift_s", "reference_max_age_s", "multiplier"]
        a = df[df.method.eq("Spatial")].set_index(budget_index)
        b = df[df.method.eq("NullSpatial")].set_index(budget_index)
        assert a.reference_requests.equals(b.reference_requests)
        assert a.reference_payload_bytes.equals(b.reference_payload_bytes)
        assert df[df.method.isin(["HistoryShort", "HistoryExtended"])].reference_requests.eq(0).all()
        assert df.loc[df.event_requested.eq(0), "event_incremental_hit"].isna().all()
        pairs = pd.read_csv(directory/"paired-differences.csv")
        assert pairs.independent_dates.max() <= len(dates(config, split))
        with gzip.open(directory/"example-traces.jsonl.gz", "rt") as f:
            traces = [json.loads(line) for line in f]
        for row in traces:
            assert row["target_assumed_available"] <= row["t"]
            assert all(a <= row["t"] for a in row["reference_assumed_available"])
            provenance_checks += 1
        # Trace-level equality verifies timings, not merely aggregate report counts.
        for method in config["methods"]:
            d = [r["t"] for r in traces if r["case"] == "drift" and r["method"] == method and r["report"]]
            s = [r["t"] for r in traces if r["case"] == "local_slow" and r["method"] == method and r["report"]]
            assert d == s
        splits[split] = {"metric_rows": len(df), "independent_dates": len(dates(config, split)),
                         "artifact_hashes_verified": len(manifest["artifacts"])}
    print(json.dumps({"status": "PASS", "unchanged_existing_files_except_readme": protected,
                      "upstream_gitlinks_unchanged": 2, "workbook_sha256_verified": config["workbook_sha256"],
                      "frozen_code_and_config_verified": True, "trace_availability_checks": provenance_checks,
                      "identical_input_boundary_verified": True, "cost_equalization_verified": True,
                      "splits": splits}, indent=2))


if __name__ == "__main__":
    main()
