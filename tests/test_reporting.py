"""Partial/smoke matrices must preserve relationship distinctions and N/A."""
import importlib.util,sys
import pandas as pd
from tais import ROOT

def test_summary_handles_no_actual_same_channel_overlap(tmp_path,monkeypatch):
    spec=importlib.util.spec_from_file_location('reporting',ROOT/'scripts/summarize_results.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    dest=tmp_path/'results'/'smoke';dest.mkdir(parents=True)
    # Small smoke input deliberately has clean / cross / sequential-spike cases only.
    original=pd.read_csv(ROOT/'results/development-smoke/metrics.csv')
    original.to_csv(dest/'metrics.csv',index=False)
    m.ROOT=tmp_path;monkeypatch.setattr(sys,'argv',['summary','--split','smoke'])
    m.main()
    groups=pd.read_csv(dest/'by_relationship.csv').relationship.unique()
    assert 'same' not in groups and 'same_sequential' in groups and 'clean' in groups
    assert (dest/'tradeoff.png').is_file()
