"""Artificial parsing fixture only; no claim of original data verification."""
import importlib.util,json
from pathlib import Path
import pandas as pd
from tais import ROOT

def test_fixture_audit_gaps_missing_and_fixed_reconstruction(tmp_path):
    spec=importlib.util.spec_from_file_location('greenhouse_helper',ROOT/'scripts/greenhouse.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    f=tmp_path/'artificial.csv'
    f.write_text('date,time,temp,rh,state\n2023-01-01,00:00:00,24,45,0\n2023-01-01,00:05:00,25,,0\n2023-01-01,00:15:00,26,48,1\n')
    mapping=tmp_path/'mapping.json';mapping.write_text(json.dumps(dict(date='date',time='time',temperature='temp',humidity='rh',state='state')))
    m.audit(f,tmp_path,mapping,'%Y-%m-%d %H:%M:%S')
    d=json.loads((tmp_path/'audit.json').read_text())
    assert d['rows']==3 and d['gaps_over_300_s']==1 and d['numeric_missing']['humidity']==1
    metrics=pd.read_csv(tmp_path/'fixed_reconstruction.csv')
    assert list(metrics.interval_s)==[300,600,900,1800,3600]
    assert metrics.event_recall.isna().all()
