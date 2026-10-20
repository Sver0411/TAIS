#!/usr/bin/env python3
"""Verify frozen input/source fingerprints, counts, views, budgets and optional archives."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from benchmark_paper import OUT,RAW,sha,fingerprints,dump

def verify(root,archives=False,phase='test'):
    m=json.loads((root/phase/'manifest.json').read_text());assert m['status']=='COMPLETE'
    assert sha(root/phase/'metrics.csv')==m['metrics_sha256']
    assert sha(root/phase/'events.csv')==m['events_sha256']
    if (OUT/'selection.json').exists():
        lock=json.loads((OUT/'selection.json').read_text())
        # A separately frozen G2 generator adds a module to src/tais. Verify every
        # original pinned file; a new unrelated file is not an old-source mutation.
        current=fingerprints();assert all(current.get(p)==h for p,h in lock['sources'].items())
        assert lock['operating_points_sha256']==sha(OUT/'operating-points.json')
    d=pd.read_csv(root/phase/'metrics.csv');assert len(d)==m['runs']
    assert not d.duplicated(['seed','scenario','view','method']).any()
    assert d.groupby(['seed','scenario']).observed_sha256.nunique().max()==1
    assert d.groupby(['seed','scenario']).signals_sha256.nunique().max()==1
    assert d.groupby(['seed','scenario','schedule']).samples.nunique().max()==1
    assert (d.tp+d.missed==d.n_events).all() and (d.rx_tp+d.rx_missed==d.n_events).all()
    assert d.loc[d.n_events==0,'recall'].isna().all()
    assert d.loc[~d.health_available,'fault_detected'].isna().all()
    # Common view uses every sampled point and has immediate state edges.
    c=d[d['view']=='common'];assert (c.samples==c.uploads).all();assert (c.important_edges_unreported==0).all()
    assert (c.tp==c.rx_tp).all()
    summary=pd.read_csv(root/phase/'analysis/summary.csv')
    for _,s in summary[summary.group=='overall'].iterrows():
        rr=d[(d['view']==s['view'])&(d.method==s.method)]
        for k in ['tp','false_reports','missed','n_events','samples','uploads','binary_v1_bytes','fault_induced_false','rx_tp','rx_false_reports']:
            assert rr[k].sum()==s[k],(s.method,k)
        assert abs(s.f1-2*s.tp/(s.n_events+s.tp+s.false_reports))<1e-12
    b=pd.read_csv(root/phase/'analysis/budget_comparisons.csv')
    assert ((b.test_gap.abs()<=.05)==b.within_5pct).all()
    assert (abs(b.samples/b.target_samples-1-b.test_gap)<1e-12).all()
    historical=json.loads((OUT/'historical-protection.json').read_text());changed=[]
    for p,h in historical['files'].items():
        if sha(ROOT/p)!=h:changed.append(p)
    # Navigation-only maintenance may update the two public README entry points.
    # Keep the frozen inventory intact and continue reporting those differences;
    # no algorithm, configuration, protocol or experiment data file is exempted.
    assert not set(changed)-{'README.md','results/README.md'},changed
    for sub in ['AdaptiveSense','SensorTrust']:
        assert subprocess.check_output(['git','status','--porcelain'],cwd=ROOT/'vendor'/sub,text=True)==''
    assert subprocess.check_output(['git','diff',historical['base'],'--','vendor'],cwd=ROOT,text=True)==''
    checks=dict(status='PASS',phase=phase,runs=len(d),seed_count=d.seed.nunique(),scenarios=d.scenario.nunique(),view_methods=d.groupby('view').method.nunique().to_dict(),historical_changes=changed,archive_hashes_checked=0,source_freeze_checked=(OUT/'selection.json').exists(),budget_points_within_5pct=int(b.within_5pct.sum()),budget_points=len(b),metrics_sha256=sha(root/phase/'metrics.csv'))
    if archives:
        archive=Path(m['archive_root'])/phase
        for p,h in m['artifacts'].items():assert sha(archive/p)==h,p
        checks['archive_hashes_checked']=len(m['artifacts'])
    print(json.dumps(checks,indent=2));return checks

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=OUT);p.add_argument('--phase',default='test');p.add_argument('--archives',action='store_true');p.add_argument('--write-report',action='store_true');a=p.parse_args();r=verify(a.root,a.archives,a.phase)
    if a.write_report:dump(a.root/'checks'/f'verification-{a.phase}.json',r)
