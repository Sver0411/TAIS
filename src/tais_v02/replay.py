"""Reuse legacy replay/matcher/envelope exactly; swap only scheduler factory.

Process-local patch is single-threaded and restored on exit. Batch parallelism
uses separate processes, never threads sharing patched modules.
"""
from unittest.mock import patch
from tais.replay import run as legacy_run
from .scheduler import Scheduler

def run(trace,cfg,method,multiplier=1.0):
    """Dispatch V02/V02-Passive through a scoped scheduler-factory patch.

    Passive keeps evidence but omits accelerated confirmation. Disabled v0.2
    falls back to legacy TAIS; other method names keep their original dispatch.
    The process-local patch is unsuitable for concurrent threads."""
    if method not in ('V02','V02-Passive'):return legacy_run(trace,cfg,method,multiplier)
    if not cfg['v02']['enabled']:return legacy_run(trace,cfg,'TAIS',multiplier)
    def factory(config,confirmation=True,multiplier=1.0):
        return Scheduler(config,confirmation=method=='V02',multiplier=multiplier)
    with patch('tais.replay.Scheduler',factory):
        return legacy_run(trace,cfg,'TAIS',multiplier)
