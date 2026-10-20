"""Reproducible offline pilot; never touches frozen research artifacts."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from tais_spatial.data import Dataset, prepare
from tais_spatial.pilot import run_split
from tais_spatial.analysis import summarize, update_checksums


def code_hashes():
    paths = sorted((ROOT/"src/tais_spatial").glob("*.py")) + [Path(__file__).resolve(), ROOT/"configs/offline_spatial_pilot.json"]
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}


def main():
    """Dispatch preparation, fixed-plan pilot, analysis or gated test-freeze creation.

    Freeze requires both development and validation exploration gates; a NO-GO
    must not open held-out evaluation. Code hashes include annotation bytes,
    so later maintenance does not match the original frozen experiment source."""
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["prepare", "run", "analyze", "freeze"])
    p.add_argument("--workbook", type=Path)
    p.add_argument("--cache", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--split", choices=["development", "validation", "test"], default="development")
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--freeze", type=Path)
    p.add_argument("--development", type=Path)
    p.add_argument("--validation", type=Path)
    args = p.parse_args()
    config = json.loads((ROOT/"configs/offline_spatial_pilot.json").read_text())
    if args.command == "prepare":
        if not args.workbook:
            p.error("prepare needs --workbook")
        print(json.dumps(prepare(args.workbook, args.output, config)["total"], indent=2))
    elif args.command == "run":
        if args.split == "test":
            if not args.freeze:
                p.error("test requires a pre-existing --freeze record")
            frozen = json.loads(args.freeze.read_text())
            if frozen["code_sha256"] != code_hashes() or not frozen["held_out_allowed"]:
                raise ValueError("Frozen code/config mismatch or evaluation not allowed")
        if not args.cache:
            p.error("run needs --cache")
        m = run_split(Dataset.open(args.cache, config), config, args.split, args.output, ROOT, args.smoke)
        print(json.dumps({"rows": m["rows"], "split": args.split}))
    elif args.command == "analyze":
        print(json.dumps(summarize(args.output), indent=2)); update_checksums(args.output)
    else:
        if not args.development or not args.validation:
            p.error("freeze needs completed --development and --validation directories")
        gates = [json.loads((d/"gate.json").read_text()) for d in [args.development, args.validation]]
        if not all(g["informative_exploration_pass"] for g in gates):
            raise ValueError("Coverage or informative-comparison gate failed; do not open test")
        record = {"code_sha256": code_hashes(), "held_out_allowed": True, "gates": gates,
                  "prior_outputs": {str(d): hashlib.sha256((d/"manifest.json").read_bytes()).hexdigest()
                                    for d in [args.development, args.validation]},
                  "interpretation": "exploratory; freezes rules, not evidence of superiority"}
        with args.output.open("x") as f:
            f.write(json.dumps(record, indent=2)+"\n")


if __name__ == "__main__":
    main()
