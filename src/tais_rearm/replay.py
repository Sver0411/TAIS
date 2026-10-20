"""Only V02-Rearm selects the fix. Every comparator uses its original code."""
from unittest.mock import patch
from tais.replay import run as legacy_run
from tais_v02.replay import run as frozen_run
from .scheduler import Scheduler

def run(trace,cfg,method,multiplier=1.0):
    if method!='V02-Rearm':return frozen_run(trace,cfg,method,multiplier)
    if not cfg.get('rearm',{}).get('enabled',True):return frozen_run(trace,cfg,'V02',multiplier)
    with patch('tais.replay.Scheduler',Scheduler):
        return legacy_run(trace,cfg,'TAIS',multiplier)
