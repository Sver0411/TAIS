"""FO-1 timing variants. Historical generator and physical truth remain unchanged."""
from copy import deepcopy
from dataclasses import asdict
import math
import re
from .signals import generate as historical_generate, scenarios as historical_scenarios

VERSION = 'FO-1'
OFFSETS = {'spike': (-60, -10, -1, 0, 1, 10, 60),
           'drift': (-500, -220, -60, 0, 60, 220, 650)}


def scenarios():
    added = [f'{kind}_{relation}_{profile}_dt_{"m"+str(-dt) if dt < 0 else "p"+str(dt)}'
             for kind, offsets in OFFSETS.items() for relation in ('same', 'cross')
             for profile in ('short', 'long') for dt in offsets if dt != 60]
    return historical_scenarios() + added


def specification(scenario):
    if scenario in historical_scenarios():
        return scenario, 60, 'original'
    match = re.fullmatch(r'(spike|drift)_(same|cross)_(short|long)_dt_([mp])(\d+)', scenario)
    if not match:
        raise ValueError('Unknown FO-1 scenario')
    kind, relation, profile, sign, value = match.groups()
    offset = int(value) * (-1 if sign == 'm' else 1)
    if offset == 60 or offset not in OFFSETS[kind]:
        raise ValueError('Duplicate default timing or unregistered offset')
    return f'{kind}_{relation}_{profile}', offset, 'added'


def generate(cfg, seed, scenario):
    base, offset, _ = specification(scenario)
    if base == scenario:
        return historical_generate(cfg, seed, base)
    adjusted = deepcopy(cfg)
    adjusted['synthetic']['event_delay_s'] = offset
    trace = historical_generate(adjusted, seed, base)
    trace.scenario = scenario
    return trace


def overlap(event, fault):
    """Truth labels include the last 1-Hz point; injection intervals are half-open.

    Report both geometric interval duration and actual shared observation points.
    A boundary-only label point can be affected despite zero geometric duration.
    """
    start = max(event.start_s, fault.start_s)
    end = min(event.end_s, fault.end_s)
    points = max(0, min(math.floor(event.end_s), math.ceil(fault.end_s)-1) - math.ceil(start) + 1)
    return dict(start_s=start if points else None, end_s=end if points else None,
                duration_s=max(0., end-start), observation_points=points)


def metadata(trace, cfg):
    base, offset, cohort = specification(trace.scenario)
    spec = cfg['synthetic']
    f = trace.faults[0] if trace.faults else None
    e = trace.events[0] if trace.events else None
    ov = overlap(e, f) if e and f else dict(start_s=None,end_s=None,duration_s=0.,observation_points=0)
    if not e: temporal = 'no_event'
    elif not f: temporal = 'no_fault'
    elif ov['observation_points']: temporal = 'overlap'
    elif e.end_s < f.start_s: temporal = 'event_before_fault'
    elif e.start_s >= f.end_s: temporal = 'fault_before_event'
    else: raise AssertionError('Unclassified truth interval')
    injection = None
    if f:
        intensity = spec['profiles'][trace.profile]['intensity']
        injection = {**asdict(f), 'intensity': intensity,
                     'drift_rate_per_s': spec['drift_per_second']*intensity if f.kind=='drift' else None,
                     'spike_amplitude': spec['spike_amplitude']*intensity if f.kind=='spike' else None}
    return dict(generator_version=VERSION, scenario=trace.scenario, base_scenario=base,
                seed=trace.seed, cohort=cohort, offset_s=offset if e and f else None,
                fault_kind=f.kind if f else 'clean', relationship=trace.relationship,
                profile=trace.profile, event_plan_start_s=f.start_s+offset if e and f else None,
                events=[asdict(x) for x in trace.events], injection=injection,
                overlap=ov, temporal=temporal,
                event_start_order=('event_first' if e.start_s<f.start_s else 'fault_first' if e.start_s>f.start_s else 'simultaneous') if e and f else 'not_applicable')
