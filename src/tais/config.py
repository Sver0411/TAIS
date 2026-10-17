"""Load one TAIS configuration and the exact vendored baseline config."""
from copy import deepcopy
import yaml
from . import ROOT
from simulator.config import load_config as load_upstream

def load(path=None):
    cfg = yaml.safe_load((path or ROOT/'configs/experiment.yaml').read_text())
    lo,hi=cfg['sampling']['min_interval_s'],cfg['sampling']['max_interval_s']
    if not 0 < lo <= cfg['sampling']['default_interval_s'] <= hi:
        raise ValueError('Invalid sampling bounds')
    tr=cfg['trust']
    if tr['degraded_confirmation_samples']<2 or tr['max_confirmation_duration_s']<lo:
        raise ValueError('Confirmation must require >=2 samples and positive window')
    if not lo<=tr['diagnostic_interval_s']<=hi:
        raise ValueError('Diagnostic interval out of bounds')
    partitions=[cfg['evaluation'][k] for k in ['development_seeds','validation_seeds','held_out_test_seeds']]
    flat=[s for p in partitions for s in p]
    if len(set(flat))!=len(flat):raise ValueError('Overlapping seed split')
    return cfg

def baseline(cfg, multiplier=1.0):
    b=deepcopy(load_upstream())
    for name,c in b['adaptive']['channels'].items():c['use']=name in cfg['channels']
    # Operating-point sweeps change thresholds explicitly, never baseline files.
    for k in ['stable_threshold','active_threshold','event_threshold']:
        b['adaptive'][k]*=multiplier
    return b
