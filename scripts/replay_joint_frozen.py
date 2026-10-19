#!/usr/bin/env python3
"""Engineering replication to NEW paths; never replaces frozen JO-1 results."""
import argparse,sys,shutil
from pathlib import Path
import benchmark_joint_optimization as b
import analyze_joint_optimization as a
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--phase',choices=['validation','test'],default='test');p.add_argument('--output-root',type=Path,required=True);p.add_argument('--archive-root',type=Path,required=True);p.add_argument('--workers',type=int,default=4);args=p.parse_args()
assert args.output_root.resolve()!=b.OUT.resolve() and args.archive_root.resolve()!=b.RAW.resolve()
args.output_root.mkdir(parents=True,exist_ok=False);shutil.copyfile(b.OUT/'selection.json',args.output_root/'selection.json')
b.OUT=args.output_root;b.RAW=args.archive_root
sys.argv=[sys.argv[0],'--phase',args.phase,'--workers',str(args.workers)];b.main()
a.OUT=args.output_root;a.RAW=args.archive_root;a.analyze(args.phase)
print('REPLICATION of already used seeds, not new independent evidence')
