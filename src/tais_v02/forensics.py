"""Read-only instrumentation of legacy decisions. Never passes truth online.

Temporarily replaces the legacy analyzer constructor with a delegating observer.
Single-threaded context; restored even on error. No equation or return is changed.
"""
from copy import deepcopy
from dataclasses import asdict
from unittest.mock import patch
import tais.scheduler as legacy
from tais.replay import run, finite
from tais.trust import SensorTrust
from simulator.scoring import ChangeAnalyzer
from simulator.config import analyzer_config
from tais.config import baseline


def inspect_run(trace, cfg, method, multiplier=1):
    evidence = []
    calls = []

    class Analyzer:
        def __init__(self, *args):
            self.inner = ChangeAnalyzer(*args)
        def update(self, t, values):
            before = self.inner._potential_start
            result = self.inner.update(t, values)
            calls.append(dict(t=t, channels=list(values), raw_score=result[0],
                              raw_active=result[2], debounce_before=before,
                              debounce_after=self.inner._potential_start))
            return result

    class Observed(legacy.Scheduler):
        def update(self, t, values):
            before = deepcopy(self.pending)
            blocked = dict(self.blocked)
            begin = len(calls)
            d = super().update(t, values)
            channel = {}
            for n in self.names:
                hits = [x for x in calls[begin:] if n in x['channels']]
                prior, after = before[n], self.pending[n]
                # Also exposes episodes created and terminated in a single call.
                action = 'none'
                if after is not None and prior is None: action = 'created'
                elif after is not None: action = 'retained'
                elif d.active[n] and (prior is not None or d.health[n]['state'] == 'DEGRADED'): action = 'confirmed'
                elif prior is not None or (self.blocked[n] and not blocked[n]):
                    action = 'cancelled'
                channel[n] = dict(raw_calls=hits, pending_before=prior, pending_after=after,
                                  blocked=self.blocked[n], ladder_state=self.level[n],
                                  ladder_position=self.pos[n], lifecycle=action)
            evidence.append(dict(timestamp=t, channels=channel))
            return d
    if method in ('TAIS', 'GateOnly'):
        with patch.object(legacy, 'ChangeAnalyzer', Analyzer), patch('tais.replay.Scheduler', Observed):
            result = run(trace, cfg, method, multiplier)
    else:
        result = run(trace, cfg, method, multiplier)
        analyzers = {n: ChangeAnalyzer(analyzer_config(baseline(cfg, multiplier))) for n in cfg['channels']}
        trust = {n: SensorTrust(cfg['channels'][n]['trust']) for n in cfg['channels']}
        for r in result['records']:
            channels = {}
            for n in cfg['channels']:
                v = r['values'][n]; a = analyzers[n]
                before = a._potential_start
                score, _, active = a.update(r['timestamp'], {n:v} if finite(v) else {})
                channels[n] = dict(raw_calls=[dict(raw_score=score, raw_active=active,
                                    debounce_before=before, debounce_after=a._potential_start)],
                                   lifecycle='debounced' if active else 'none',
                                   pending_before=None, pending_after=None,
                                   offline_health=asdict(trust[n].update(r['timestamp'], v)))
            evidence.append(dict(timestamp=r['timestamp'], channels=channels))
    return result, evidence
