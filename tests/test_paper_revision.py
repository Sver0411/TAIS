"""Read-only qualification and publication binding checks, no simulation replay."""
import hashlib,sys
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import analyze_budget_sensitivity as sensitivity

def test_budget_sensitivity_reads_frozen_points_without_selection(tmp_path,monkeypatch):
    sources={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sensitivity.INPUTS.values()}
    monkeypatch.setattr(sensitivity,'OUT',tmp_path)
    rows=sensitivity.analyze();d=pd.DataFrame(rows)
    assert len(d)==60 and not d.duplicated(['generator','method','target']).any()
    assert (d.within_2pct<=d.within_5pct).all() and (d.within_5pct<=d.within_10pct).all()
    delta=d[(d.generator=='G1')&(d.method=='Delta-budget-SU40+C11')&(d.target=='JO-SU-40')].iloc[0]
    assert not delta.within_5pct and delta.within_10pct
    fixed=d[(d.generator=='G2')&(d.method=='Fixed-20+C11')&(d.target=='JO-SU-40')].iloc[0]
    assert not fixed.within_2pct and fixed.within_5pct and fixed.relative_gap<0
    assert {p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}==sources

def test_sensitivity_qualification_does_not_create_operating_points():
    d=pd.read_csv(ROOT/'results/tais-paper-review/budget_sensitivity.csv')
    for g,path in sensitivity.INPUTS.items():
        original=pd.read_csv(ROOT/path);original=original[original.group=='overall']
        if 'view' in original:original=original[original['view']=='native']
        original=original.set_index('method')
        for _,r in d[d.generator==g].iterrows():
            assert r.samples==original.loc[r.method,'samples']
            assert r.target_samples==original.loc[r.target,'samples']
            assert abs(r.relative_gap-(r.samples/r.target_samples-1))<1e-12
