#!/usr/bin/env python3
"""Read-only Phase4 pairing, source protection, wire and evidence checks."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from benchmark_phase4 import OUT,ROOT,sources


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_historical_files():
    """Keep the original ledger; audit the two CI-only verifier replacements."""
    active=json.loads((OUT/'historical-protection.json').read_text())
    original_path=OUT/active['original_ledger']
    assert sha(original_path)==active['original_ledger_sha256']
    original=json.loads(original_path.read_text())['files']
    protected=active['files']
    maintenance=json.loads((OUT/active['maintenance_ledger']).read_text())['files']
    assert set(maintenance)=={'scripts/verify_transfer.py','scripts/verify_paper_revision.py'}
    assert not set(protected)&set(maintenance)
    assert {**protected,**{name:entry['original_sha256'] for name,entry in maintenance.items()}}==original
    for name,entry in maintenance.items():
        assert sha(ROOT/name)==entry['current_sha256'],name
    for name,h in protected.items():
        assert sha(ROOT/name)==h,('historical file changed',name)
    return len(protected),len(maintenance)


def verify(root,phase='test',archives=False,replay=False):
    plan=json.loads((ROOT/'configs/phase4.json').read_text())
    source=root/(plan['engineering_directory'] if phase=='engineering' else phase)
    manifest=json.loads((source/'manifest.json').read_text())
    assert manifest['status']=='COMPLETE' and manifest['sources']==sources()
    for name,h in manifest['outputs'].items():assert sha(source/name)==h,name
    if phase=='test':
        lock=json.loads((root/'freeze.json').read_text());assert lock['sources']==sources()
        assert manifest['freeze_sha256']==sha(root/'freeze.json')
        for name,h in lock['sources'].items():assert sha(root/'sources'/name)==h,name
    unchanged,maintained=verify_historical_files()
    f=pd.read_csv(source/'metrics.csv');e=pd.read_csv(source/'events.csv');fr=pd.read_csv(source/'forensics.csv.gz')
    keys=['seed','scenario','method'];expected=len(manifest['seeds'])*len(manifest['cases'])*len(manifest['methods'])
    assert len(f)==manifest['runs']==expected and not f.duplicated(keys).any()
    assert f.groupby(['seed','scenario']).observed_sha256.nunique().eq(1).all()
    assert f.groupby(['seed','scenario']).n_events.nunique().eq(1).all()
    for side in ['sender','receiver']:
        grouped=e[e.side==side].groupby(keys).agg(event_n=('matched','size'),matched_n=('matched','sum'),restricted_sum=('restricted_delay_s','sum'))
        g=f.set_index(keys).join(grouped)
        assert g.event_n.fillna(0).eq(g.n_events).all()
        assert g.matched_n.fillna(0).eq(g[side+'_tp']).all()
        assert (g[side+'_tp']+g[side+'_fn']).eq(g.n_events).all()
        assert np.allclose(g.restricted_sum.fillna(0),g[side+'_restricted_delay_sum_s'])
    assert len(fr)==len(e[e.side=='sender'])
    assert not fr.duplicated(keys+['channel','truth_start']).any()
    assert fr[~fr.gate_enabled].miss_category.isin(['C_gate','C_exposure']).sum()==0
    pairs=[('A0','A3'),('A1','A5'),('A2','A6'),('A4','A7')]
    pairs += [(f'{kind}-T{t}-U0',f'{kind}-T{t}-U1') for kind in ['Robust','Risk'] for t in (0,1)]
    for a,b in pairs:
        g=f[f.method==a].merge(f[f.method==b],on=['seed','scenario'],suffixes=('_a','_b'))
        for key in ['sample_schedule_sha256','samples','sender_tp','sender_fp','sender_fn','receiver_tp','receiver_fp']:
            assert g[key+'_a'].eq(g[key+'_b']).all(),(a,b,key)
    new=f[f.method.str.startswith(('Robust-','Risk-'))]
    assert new.fast_window_max.le(plan['common']['fast_limit']).all()
    assert new.important_edges_unreported.eq(0).all()
    timelines=pd.read_csv(source/'timelines.csv')
    assert timelines.groupby(['seed','scenario','method','channel']).timestamp.apply(lambda x:x.diff().dropna().gt(0).all()).all()
    analysis=source/'analysis/manifest.json'
    if analysis.exists():
        a=json.loads(analysis.read_text());assert a['inputs']==manifest['outputs']
        for name,h in a['outputs'].items():assert sha(source/'analysis'/name)==h,name
        assert len(list((source/'analysis/figures').glob('*.png')))==12
        assert len(list((source/'analysis/figures').glob('*.pdf')))==12
    archive_count=0
    if archives:
        for name,h in json.loads((source/'archives.json').read_text()).items():
            assert sha(Path(manifest['archive_root'])/name)==h,name
            archive_count+=1
    replayed=0
    if replay:
        from phase4_support import make_trace,replay as run
        from tais.config import load
        from tais.transfer_signals import counterfactual
        from paper_metrics import metrics
        from benchmark_joint_optimization import canon,metrics as codec_metrics
        for seed,case,method in [(920,'high_frequency','Risk-T1-U1'),(930,'noisy_none','Robust-T1-U1'),(939,'multi_range','A7')]:
            cfg=load();tr=make_trace(plan,seed,case);cf=counterfactual(tr);cr=run(cf,cfg,method,plan);_,ff=codec_metrics(cf,cr,cfg,cr)
            result=run(tr,cfg,method,plan);_,frames,_,_,_=metrics(tr,result,cfg,cr,ff)
            expected=f[(f.seed==seed)&(f.scenario==case)&(f.method==method)].iloc[0].result_sha256
            assert hashlib.sha256(gzip.compress(canon(dict(result=result,frames=frames)),mtime=0)).hexdigest()==expected
            replayed+=1
    assert not (ROOT/'docs/PHASE4_PROGRESS_JA.md').exists(),'Personalized report must be outside Git'
    value=dict(status='PASS',runs=len(f),seed_clusters=f.seed.nunique(),cases=f.scenario.nunique(),methods=f.method.nunique(),
               per_event_rows=len(fr),raw_archives_checked=archive_count,deterministic_replays=replayed,
               historical_files_unchanged=unchanged,historical_verifier_maintenance=maintained,
               U_sample_and_detection_invariance=True,fast_budget_bound=True)
    print(json.dumps(value,indent=2));return value


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',type=Path,default=OUT);p.add_argument('--phase',choices=['engineering','test'],default='test')
    p.add_argument('--archives',action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args()
    verify(a.root,a.phase,a.archives,a.replay)
