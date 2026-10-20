#!/usr/bin/env python3
"""One command, frozen final split; refuse overwrite; no calibration on test."""
import argparse,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=ROOT/'results/scratch/paper-reproduction');p.add_argument('--workers',type=int,default=4);a=p.parse_args()
assert not a.output.exists(),'Choose a fresh output directory'
archive=a.output/'archives'
subprocess.run([sys.executable,'scripts/benchmark_paper.py','test','--workers',str(a.workers),'--output-root',str(a.output),'--archive-root',str(archive)],cwd=ROOT,check=True)
subprocess.run([sys.executable,'scripts/analyze_paper.py','--phase','test','--root',str(a.output)],cwd=ROOT,check=True)
subprocess.run([sys.executable,'scripts/verify_paper.py','--root',str(a.output),'--archives','--write-report'],cwd=ROOT,check=True)
original=json.loads((ROOT/'results/tais-paper/test/manifest.json').read_text());replica=json.loads((a.output/'test/manifest.json').read_text())
assert original['metrics_sha256']==replica['metrics_sha256'],'Mismatch in deterministic per-run metrics'
print('PASS: exact complete held-out metrics fingerprint reproduced')
