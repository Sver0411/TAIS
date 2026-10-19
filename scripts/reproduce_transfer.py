#!/usr/bin/env python3
"""Re-execute frozen G2 in a fresh scratch archive and compare every CSV hash."""
import argparse,json,subprocess,sys,tempfile
from pathlib import Path
from benchmark_transfer import ROOT,OUT,check_freeze
from benchmark_joint_optimization import sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--workers',type=int,default=4);p.add_argument('--check-only',action='store_true');a=p.parse_args();check_freeze()
    def run(*args):subprocess.run([sys.executable,*args],cwd=ROOT,check=True)
    run('-m','pytest','tests/test_transfer_signals.py','tests/test_transfer_benchmark.py','-q')
    run('scripts/verify_transfer.py')
    if a.check_only:return
    scratch=ROOT/'results/scratch';scratch.mkdir(exist_ok=True);dest=Path(tempfile.mkdtemp(prefix='transfer-replica-',dir=scratch));out=dest/'results';raw=dest/'traces'
    run('scripts/benchmark_transfer.py','test','--workers',str(a.workers),'--output-root',str(out),'--archive-root',str(raw))
    run('scripts/analyze_transfer.py','--root',str(out));run('scripts/verify_transfer.py','--root',str(out),'--archives','full')
    for f in ['metrics.csv','events.csv','faults.csv','pooled_age.csv','age_histograms.json']:assert sha(out/'test'/f)==sha(OUT/'test'/f),f
    for p in (OUT/'test/analysis').glob('*.csv'):assert sha(out/'test/analysis'/p.name)==sha(p),p
    print('PASS: complete G2 replay and all analysis CSVs reproduce byte-for-byte',dest)
if __name__=='__main__':main()
