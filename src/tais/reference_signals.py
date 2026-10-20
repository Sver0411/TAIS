"""IRB-1: independent same-unit sensors, independent labels, exact twin worlds."""
from copy import deepcopy
from dataclasses import asdict
import math
import random
from .config import baseline
from .signals import Trace,Fault
from .observability_signals import overlap
from dataset.generate_dataset import label_events

VERSION='IRB-1'
A='temperature'
B='reference_temperature'


def main_config(cfg):
    out=deepcopy(cfg);out['channels']={A:out['channels'][A]};return out


def scenario_specs():
    """Enumerate the fixed IRB same-quantity reference and stress interventions."""
    specs=[]
    def add(cohort,alpha=None,shape=None,duration=None,offset=None,reference='normal'):
        event=cohort in ('mixed','event_only','missing','bias_stress')
        fault=cohort in ('mixed','drift_only','missing','bias_stress')
        name=f'{cohort}_a{alpha:g}_{shape}_d{duration}_dt{offset}' if event else f'{cohort}_d{duration}' if fault else 'clean'
        d=dict(id=name,cohort=cohort,alpha=alpha,event=event,drift=fault,shape=shape,duration_s=duration,offset_s=offset,reference=reference)
        specs.append(d)
    for alpha in (1.,.5,0.):
        for shape in ('plateau','matched_ramp'):
            for offset in (-220,0,60,220):
                for duration in (240,600):add('mixed',alpha,shape,duration,offset)
    for alpha in (1.,.5,0.):
        for shape in ('plateau','matched_ramp'):
            for duration in (240,600):add('event_only',alpha,shape,duration,0)
    for duration in (240,600):add('drift_only',duration=duration)
    add('clean')
    for cohort,reference in (('missing','missing'),('bias_stress','bias_stress')):
        for alpha in (1.,.5,0.):
            for shape in ('plateau','matched_ramp'):
                for duration in (240,600):add(cohort,alpha,shape,duration,60,reference)
    assert len(specs)==len({s['id'] for s in specs})==87
    return specs


def equivalence_pairs():
    """Identify worlds with identical observations but different physical event labels."""
    specs=scenario_specs()
    return [(next(s['id'] for s in specs if s['cohort']=='drift_only' and s['duration_s']==d),
             next(s['id'] for s in specs if s['cohort']=='event_only' and s['alpha']==0 and s['shape']=='matched_ramp' and s['duration_s']==d)) for d in (240,600)]


def generate(cfg,seed,scenario):
    """Return an IRB trace and offline metadata for main/reference temperature.

    Reference B responds to environmental displacement by alpha and has its
    own seeded noise and modeled bias/missingness. Alpha=0 matched-ramp twins
    deliberately expose nonidentifiability: observations alone cannot decide
    which physical cause produced them. Labels never enter ReferenceGate."""
    spec=next((s for s in scenario_specs() if s['id']==scenario),None)
    if spec is None:raise ValueError('Unknown IRB-1 case')
    syn=cfg['synthetic'];n=syn['duration_s'];duration=spec['duration_s']
    profile='short' if duration==240 else 'long'
    drift_start=syn['fault_start_s']+random.Random(syn['fault_seed_offset']+seed).randint(-syn['fault_jitter_s'],syn['fault_jitter_s'])
    event_start=drift_start+(spec['offset_s'] or 0)
    event_duration=(syn['profiles'][profile]['event_duration_s'] if spec['shape']=='plateau' else duration) if spec['event'] else None
    intensity=syn['profiles'][profile]['intensity'] if duration else 0
    rate=syn['drift_per_second']*intensity
    rng_a=random.Random(seed);rng_b=random.Random(2000000+seed)
    bias=3.0 if spec['reference']=='bias_stress' else .3
    latent=[];noisy=[];observed=[];local=[];reference_local=[]
    for t in range(n):
        g=syn['baseline'][A]+syn['background_amplitude'][A]*math.sin(2*math.pi*t/syn['background_period_s'])
        l=0.
        if spec['event']:
            if spec['shape']=='plateau':
                ramp=syn['event_ramp_s'];l=syn['event_amplitude'][A]*max(0,min(1,(t-event_start)/ramp,(event_start+event_duration-t)/ramp))
            elif event_start<=t<event_start+event_duration:l=rate*(t-event_start)
        d=rate*(t-drift_start) if spec['drift'] and drift_start<=t<drift_start+duration else 0.
        la=(spec['alpha'] or 0.)*l
        ea=rng_a.gauss(0,syn['noise_sigma'][A]);eb=rng_b.gauss(0,syn['noise_sigma'][A])
        # Common arithmetic order guarantees exact twins, not just close values.
        na=(g+ea)+l;nb=((g+bias)+eb)+la
        latent.append(dict(timestamp=t,temperature=g+l,reference_temperature=g+la))
        noisy.append(dict(timestamp=t,temperature=na,reference_temperature=nb))
        b=None if spec['reference']=='missing' and drift_start-60<=t<drift_start+duration+120 else nb
        observed.append(dict(timestamp=t,temperature=na+d,reference_temperature=b))
        local.append(l);reference_local.append(la)
    bcfg=baseline(main_config(cfg))
    driven={c:local if c==A else [0.]*n for c in bcfg['adaptive']['channels']}
    events=label_events(driven,bcfg)
    driven[A]=reference_local;reference_events=label_events(driven,bcfg)
    faults=[Fault(A,drift_start,drift_start+duration,'drift')] if spec['drift'] else []
    trace=Trace(scenario,'same_quantity',profile,seed,latent,noisy,observed,events,faults)
    ov=overlap(events[0],faults[0]) if events and faults else dict(start_s=None,end_s=None,duration_s=0.,observation_points=0)
    temporal='no_event' if not events else 'no_fault' if not faults else 'overlap' if ov['observation_points'] else 'event_before_fault' if events[0].end_s<drift_start else 'fault_before_event'
    meta=dict(version=VERSION,seed=seed,unit='degree_C',spec=spec,drift_start_s=drift_start if faults else None,
              drift_end_s=drift_start+duration if faults else None,drift_rate_per_s=rate if faults else None,
              event_plan_start_s=event_start if spec['event'] else None,event_plan_duration_s=event_duration,
              reference_static_bias_C=bias,noise_sigma_C=syn['noise_sigma'][A],reference_noise_seed=2000000+seed,
              events=[asdict(e) for e in events],faults=[asdict(f) for f in faults],reference_physical_labels=[asdict(e) for e in reference_events],
              overlap=ov,temporal=temporal,event_starts_during_drift=bool(events and faults and drift_start<=events[0].start_s<drift_start+duration),
              event_extends_past_drift=bool(events and faults and events[0].end_s>=drift_start+duration),
              reference_has_nonzero_event_response=bool(spec['event'] and spec['alpha']>0))
    return trace,meta
