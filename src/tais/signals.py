"""Independent latent signals, observed noise and intervention schedules.

Only the replay owns this object. Scheduler.update receives a single sample.
"""
from dataclasses import dataclass
import math,random
from simulator.events import Event
from dataset.generate_dataset import label_events
from .config import baseline

@dataclass
class Trace:
    scenario: str
    relationship: str
    profile: str
    seed: int
    latent: list
    noisy: list
    observed: list
    events: list
    faults: list

@dataclass(frozen=True)
class Fault:
    channel: str
    start_s: float
    end_s: float
    kind: str

KINDS=('range','spike','stuck','drift','missing','invalid','stable_offset')
RELATIONS=('none','cross','same')

def scenarios():
    return ['clean_none','clean_event','clean_short']+[f'{k}_{r}_{p}' for k in KINDS for r in RELATIONS for p in ['short','long']]

def generate(cfg,seed,scenario):
    spec=cfg['synthetic'];n=spec['duration_s'];base=spec['baseline']
    names=list(cfg['channels'])
    if scenario.startswith('clean_'):
        kind='clean';relation='none' if scenario=='clean_none' else 'same'
        profile='short' if scenario=='clean_short' else 'long'
    else:kind,relation,profile=scenario.rsplit('_',2)
    # Same seed/profile/relation => same latent/noisy trace for EVERY fault kind.
    noise=random.Random(seed)
    schedule=random.Random(spec['fault_seed_offset']+seed)
    start=spec['fault_start_s']+schedule.randint(-spec['fault_jitter_s'],spec['fault_jitter_s'])
    duration=spec['profiles'][profile]['fault_duration_s']
    end=start+duration
    event_start=start+spec['event_delay_s']
    event_duration=spec['profiles'][profile]['event_duration_s']
    event_channel='humidity' if relation=='cross' else 'temperature'
    latent=[];noisy=[];driven={c:[] for c in baseline(cfg)['adaptive']['channels']}
    for t in range(n):
        row={'timestamp':t};obs={'timestamp':t}
        for c in names:
            background=spec['background_amplitude'][c]*math.sin(2*math.pi*t/spec['background_period_s'])
            # Piecewise trapezoid; truth uses physical deviation+duration, not score.
            ramp=spec['event_ramp_s']
            pulse=max(0,min(1,(t-event_start)/ramp,(event_start+event_duration-t)/ramp)) if relation!='none' else 0
            if c!=event_channel:pulse=0
            offset=spec['event_amplitude'][c]*pulse
            row[c]=base[c]+background+offset
            obs[c]=row[c]+noise.gauss(0,spec['noise_sigma'][c])
            driven[c].append(offset)
        for c in driven:
            if c not in names:driven[c].append(0.0)
        latent.append(row);noisy.append(obs)
    events=label_events(driven,baseline(cfg))
    observed=[dict(r) for r in noisy];faults=[]
    if kind!='clean':
        if kind=='spike':end=start+1
        faults=[Fault('temperature',start,end,kind)]
        intensity=spec['profiles'][profile]['intensity']
        for t in range(start,min(n,end)):
            v=observed[t]['temperature']
            if kind=='range':v=spec['range_value']*intensity
            elif kind=='spike':v+=spec['spike_amplitude']*intensity
            elif kind=='stuck':v=noisy[start]['temperature']
            elif kind=='drift':v+=spec['drift_per_second']*intensity*(t-start)
            elif kind=='missing':v=None
            elif kind=='invalid':v=float('nan')
            elif kind=='stable_offset':v+=spec['offset_amplitude']*intensity
            observed[t]['temperature']=v
    return Trace(scenario,relation,profile,seed,latent,noisy,observed,events,faults)
