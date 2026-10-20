#!/usr/bin/env python3
"""Read-only G2 source/data/receiver provenance and manuscript binding checks."""
import argparse,gzip,hashlib,json,subprocess,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from benchmark_transfer import OUT,RAW,BASE,check_freeze,plan
from benchmark_joint_optimization import sha,canon
from tais.transfer_signals import generate,counterfactual,scenarios
from tais.wire_codec import decode,encode

def verify(root,phase,archives):
    """Verify original source locks before checking G2 data, archives and manuscript bindings.

    Archive modes control how many immutable logs are read, not whether the
    source freeze is enforced. Comment changes fail exact source identity;
    separate semantic checks cannot silently substitute for this assertion."""
    check_freeze();base=root/phase;manifest=json.loads((base/'manifest.json').read_text());assert manifest['status']=='COMPLETE'
    for f,h in manifest['outputs'].items():assert sha(base/f)==h,f
    d=pd.read_csv(base/'metrics.csv');e=pd.read_csv(base/'events.csv');f=pd.read_csv(base/'faults.csv')
    assert len(d)==manifest['runs']==len(manifest['seeds'])*len(manifest['cases'])*len(manifest['specs'])
    assert not d.duplicated(['seed','scenario','method']).any()
    for _,r in d.groupby(['seed','scenario']):assert r.observed_sha256.nunique()==r.signals_sha256.nunique()==1
    for _,r in d.groupby(['seed','counterfactual_identity','method']):assert r.counterfactual_sha256.nunique()==1
    assert (d.tp+d.missed==d.n_events).all() and (d.rx_tp+d.rx_missed==d.n_events).all()
    assert d[d.n_events==0].recall.isna().all()
    assert not f[f.kind=='stable_offset'].type_detected.any() and not f[f.kind=='stable_offset'].type_supported.any()
    assert (d.important_edges_unreported==d.event_edges_unreported+d.health_edges_unreported).all()
    for m,r in d.groupby('method'):
        ee=e[e.method==m];ff=f[f.method==m]
        assert r.n_events.sum()==len(ee) and r.tp.sum()==ee.matched.sum() and r.rx_tp.sum()==ee.rx_matched.sum()
        assert r.fault_episodes.sum()==len(ff) and r.fault_detected.sum()==ff.any_detected.sum() and r.fault_type_detected.sum()==ff.type_detected.sum()
    ages=json.loads((base/'age_histograms.json').read_text());pool=pd.read_csv(base/'pooled_age.csv').set_index('method')
    for method,h in ages.items():
        h=np.array(h);n=int(h.sum());assert n==len(manifest['seeds'])*len(manifest['cases'])*plan()['duration_s']
        assert int(np.searchsorted(h.cumsum(),.95*n))==pool.loc[method,'p95_age_s']
        assert int(np.flatnonzero(h)[-1])==pool.loc[method,'max_age_s']
    if phase=='test':
        assert manifest['seeds']==plan()['final_seeds'] and manifest['cases']==scenarios()
        assert set(e.temporal_relation)>={'overlap','event_before_fault','fault_before_event'}
        assert set(f.channel)=={'temperature','humidity'} and e.fully_overwritten.any()
        assert set(e.duration_bin)=={'short','medium','long'}
        freeze_at_run=subprocess.check_output(['git','show',manifest['source_commit']+':results/tais-transfer/selection.json'],cwd=ROOT)
        assert freeze_at_run==(OUT/'selection.json').read_bytes()
    # Inspect all archive digests if requested; raw archives are reproducible and
    # intentionally excluded from Git. CI validates committed output digests.
    archive=Path(manifest['archive_root'])/phase;checked=0;frames=0
    if archives!='none':
        selected=manifest['artifacts'].items() if archives=='full' else [(p,h) for p,h in manifest['artifacts'].items() if '/'+plan()['example']['g2_scenario']+'/' in p]
        for p,h in selected:
            path=archive/p;assert sha(path)==h;checked+=1
            if not p.endswith('signals.json.gz'):
                data=json.loads(gzip.decompress(path.read_bytes()))
                for frame in data['frames']:
                    b=bytes.fromhex(frame['frame_hex']);assert len(b)==frame['bytes'];assert encode(decode(b))==b;frames+=1
        # Reproduce a predeclared input and its exact clean counterpart.
        seed=manifest['seeds'][0];case=manifest['cases'][0];tr=generate(plan(),seed,case)
        stored=json.loads(gzip.decompress((archive/str(seed)/case/'signals.json.gz').read_bytes()))
        assert canon(stored)==canon(tr)
        assert counterfactual(tr).observed==tr.noisy
    analysis=base/'analysis/manifest.json'
    if analysis.exists():
        a=json.loads(analysis.read_text());assert a['input_manifest_sha256']==sha(base/'manifest.json')
        for p,h in a['outputs'].items():assert sha(base/'analysis'/p)==h
        summary=pd.read_csv(base/'analysis/summary.csv')
        for _,r in summary[summary.group=='overall'].iterrows():
            rr=d[d.method==r.method]
            for k in ['tp','false_reports','missed','n_events','samples','uploads','binary_v1_bytes','fault_induced_false','rx_tp','rx_false_reports','rx_missed','fault_detected','fault_type_detected','event_edges_unreported','health_edges_unreported']:
                assert rr[k].sum()==r[k],(r.method,k)
            assert abs(r.f1-2*r.tp/(r.n_events+r.tp+r.false_reports))<1e-12
            assert abs(r.rx_f1-2*r.rx_tp/(r.n_events+r.rx_tp+r.rx_false_reports))<1e-12
            assert r.pooled_age_p95_s==pool.loc[r.method,'p95_age_s']
        if phase=='test':
            pd.testing.assert_frame_equal(pd.read_csv(root/'summary.csv'),summary[summary.group=='overall'].reset_index(drop=True),check_dtype=False,check_exact=True)
        budgets=pd.read_csv(base/'analysis/budget_comparisons.csv')
        for _,r in budgets.iterrows():assert abs(r.relative_gap-(r.samples/r.target_samples-1))<1e-12 and r.within_5pct==(abs(r.relative_gap)<=.05)
    paper=ROOT/'papers/tais/tables/transfer_data_audit.csv'
    if phase=='test' and paper.exists():
        audit=pd.read_csv(paper)
        for source,g in audit.groupby('source'):
            frame=pd.read_csv(ROOT/source)
            for _,r in g.iterrows():
                row=frame.iloc[int(r.row_index)];x=float(row[r.metric]);y=float(r.value)
                assert (np.isnan(x) and np.isnan(y)) or abs(x-y)<1e-9*max(1,abs(x))
        for p,h in json.loads((paper.parent/'transfer_source_fingerprints.json').read_text()).items():assert sha(ROOT/p)==h
    figures=root/'figures/manifest.json'
    if figures.exists():
        fig=json.loads(figures.read_text())
        for p,h in fig['inputs'].items():assert sha(ROOT/p)==h
        for p,h in fig['figures'].items():assert sha(root/'figures'/p)==h
    # Historical PDF evidence remains immutable; a paper-only revision binds
    # its current PDF separately without rewriting the G2 experiment record.
    revision_pdf=ROOT/'results/tais-paper-review/pdf-validation.json'
    pdf_check=revision_pdf if revision_pdf.exists() else root/'checks/pdf-validation.json'
    if pdf_check.exists():
        pdf=json.loads(pdf_check.read_text());assert sha(ROOT/'papers/tais/manuscript.pdf')==pdf['pdf_sha256']
        for p,h in pdf['source_sha256'].items():assert sha(ROOT/p)==h
    # Existing protected files must retain the exact inherited versions.
    paths=['src','vendor','configs/experiment.yaml','configs/tais-paper.json','results/tais-paper','results/tais-su','src/tais/signals.py']
    changed=subprocess.check_output(['git','diff','--name-only',BASE,'--',*paths],cwd=ROOT,text=True).splitlines()
    assert set(changed)<={'src/tais/transfer_signals.py'},changed
    print(json.dumps(dict(status='PASS',runs=len(d),event_rows=len(e),fault_rows=len(f),archive_digests=checked,frames_roundtripped=frames,seed_clusters=len(manifest['seeds']),frozen_sources_unchanged=True),indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=OUT);p.add_argument('--phase',choices=['smoke','test'],default='test');p.add_argument('--archives',choices=['none','sample','full'],default='none');a=p.parse_args();verify(a.root,a.phase,a.archives)
