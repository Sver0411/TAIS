"""Repair overlay; numerical scheduler/trust parameters remain from frozen v0.2."""
from copy import deepcopy
import yaml
from tais import ROOT
from tais_v02.config import load as v02_load
from tais.signals import scenarios

def load():
 cfg,_=v02_load();spec=yaml.safe_load((ROOT/'configs/blocked_rearm.yaml').read_text());cfg['rearm']=spec['rearm']
 seeds=[s for group in spec['splits'].values() for s in group]
 if len(seeds)!=len(set(seeds)):raise ValueError('Overlapping splits')
 if spec['threshold_multipliers']!=[.75,1.,1.5]:raise ValueError('Preserve declared multipliers')
 return cfg,spec

def suite_config(cfg,spec,suite):
 out=deepcopy(cfg);s=spec['suites'][suite]
 out['synthetic'].update(s['synthetic_overrides'])
 return out,scenarios() if s['scenarios']=='all' else list(s['scenarios'])
