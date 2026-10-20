"""Overlay only v0.2 parameters. Legacy config and upstream stay untouched."""
import math
from pathlib import Path
import yaml
from tais import ROOT
from tais.config import load as legacy_load

def load():
    spec=yaml.safe_load((ROOT/'configs/v02.yaml').read_text())
    cfg=legacy_load(ROOT/spec['legacy_config'])
    cfg['v02']=spec['v02']
    v=cfg['v02'];lo=cfg['sampling']['min_interval_s'];hi=cfg['sampling']['max_interval_s']
    if not isinstance(v['confirmation_samples'],int) or v['confirmation_samples']<2:
        raise ValueError('At least two real confirming observations required')
    for k in ['min_duration_s','max_confirmation_duration_s','confirmation_interval_s','diagnostic_interval_s']:
        if not math.isfinite(v[k]) or v[k]<=0:raise ValueError(k)
    if not lo<=v['confirmation_interval_s']<=hi or not lo<=v['diagnostic_interval_s']<=hi:raise ValueError('Interval bounds')
    if v['max_confirmation_duration_s']<=v['min_duration_s']:raise ValueError('Empty confirmation window')
    seeds=[s for group in spec['splits'].values() for s in group]
    if len(seeds)!=len(set(seeds)):raise ValueError('Overlapping seed sets')
    return cfg,spec
