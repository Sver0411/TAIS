"""Independent G2 physical process. No detector/scheduler imports or decisions.

The source is a dense 1 Hz observation grid; all hidden metadata are offline.
The online facade in benchmark_transfer exposes only observed rows.
"""
from copy import deepcopy
from dataclasses import dataclass,field
import hashlib,json,math,random
from .signals import Trace,Fault,KINDS
from simulator.events import Event

CHANNELS=('temperature','humidity')
@dataclass
class TransferTrace(Trace):
    metadata: dict=field(default_factory=dict)

def stream(seed,name):
    """Derive an independent reproducible RNG stream from the seed and stream name."""
    digest=hashlib.sha256(f'tais-transfer-v1:{seed}:{name}'.encode()).digest()
    return random.Random(int.from_bytes(digest[:16],'big'))

def scenarios():
    return ['clean_none','clean_temperature','clean_humidity','clean_both']+[f'{k}_{c}_{r}' for k in KINDS for c in CHANNELS for r in ('none','same','cross')]

def scenario_spec(case):
    if case not in scenarios():raise ValueError(case)
    if case.startswith('clean_'):
        family=case[6:];return 'clean',None,'none' if family=='none' else 'clean',family
    kind,channel,relation=case.rsplit('_',2)
    family='none' if relation=='none' else channel if relation=='same' else CHANNELS[1-CHANNELS.index(channel)]
    return kind,channel,relation,family

def shape(name,u):
    if name=='step_recovery':return 1. if u<.7 else math.exp(-10*(u-.7))
    if name=='smooth_pulse':return math.sin(math.pi*u)**2
    # Beta-shaped pulse with peak at 1/5 of the support, asymmetric recovery.
    return u*(1-u)**4/(.2*.8**4)

def generate(spec,seed,case):
    """Build G2 mean-reverting background, correlated noise, events and faults.

    Environment/noise/event/fault RNG names isolate their random draws. Events
    have independently placed exogenous support, represented as inclusive
    1-Hz truth endpoints [start, end-1]; faults use half-open intervals.
    latent includes noise-free events; noisy adds noise; observed applies
    fault replacement. Hidden schedules and parameters are offline metadata,
    never online inputs. This generator differs from G1 in truth rules as well
    as signal dynamics, so comparisons do not isolate a single distribution shift."""
    kind,channel,relation,family=scenario_spec(case);n=spec['duration_s'];bg=spec['background'];ns=spec['noise'];es=spec['events'];fs=spec['faults']
    env=stream(seed,'environment');noise=stream(seed,'noise');er=stream(seed,'events:'+family)
    centers=[env.uniform(*bg[c+'_center']) for c in CHANNELS];state=list(centers);targets=list(centers);rho=0;change=0;eta=[0.,0.];noise_rho=[noise.uniform(*ns['rho']) for _ in CHANNELS];scales=[1.,1.]
    background=[];noisy=[];segments=[];noise_segments=[]
    for t in range(n):
        if t>=change:
            targets=[centers[i]+env.gauss(0,bg['target_sd'][i]) for i in range(2)];rho=env.uniform(*bg['correlation']);change=t+env.randint(*bg['segment_s'])
            segments.append(dict(start=t,target=targets.copy(),correlation=rho,next_change=change))
        if t%ns['segment_s']==0:
            scales=[noise.uniform(*ns['scale']) for _ in CHANNELS];noise_segments.append(dict(start=t,scales=scales.copy()))
        z=[env.gauss(0,1),env.gauss(0,1)];z[1]=rho*z[0]+math.sqrt(1-rho*rho)*z[1]
        row={'timestamp':t};obs={'timestamp':t}
        for i,c in enumerate(CHANNELS):
            state[i]+=bg['reversion']*(targets[i]-state[i])+bg['innovation_sd'][i]*z[i]
            innovation=noise.gauss(0,1)
            if noise.random()<ns['tail_probability']:
                innovation+=ns['tail_multiplier']*noise.gauss(0,1)/math.sqrt(noise.gammavariate(1.5,1/1.5))
            eta[i]=noise_rho[i]*eta[i]+math.sqrt(1-noise_rho[i]**2)*innovation
            row[c]=state[i];obs[c]=state[i]+ns['sigma'][i]*scales[i]*eta[i]
        background.append(row);noisy.append(obs)
    latent=deepcopy(background);events=[];schedule=[]
    # Three disjoint placement strata with a random duration/shape permutation.
    # Neither fault streams nor any sampling interval enters event placement.
    bins=list(es['duration_ranges']);er.shuffle(bins);shapes=list(es['shapes']);er.shuffle(shapes)
    event_channels=[] if family=='none' else list(CHANNELS) if family=='both' else [family]
    for c in event_channels:
        for slot,(bounds,duration_bin,name) in enumerate(zip(es['onset_ranges'],bins,shapes)):
            start=er.randint(*bounds);duration=er.randint(*es['duration_ranges'][duration_bin]);amp=er.choice([-1,1])*er.uniform(*es['amplitude'][c]);end=start+duration
            assert end<=n
            schedule.append(dict(event_id=f'{c}-{slot}',channel=c,start_s=start,end_exclusive_s=end,physical_duration_s=duration,scoring_start_s=start,scoring_end_s=end-1,duration_bin=duration_bin,amplitude=amp,shape=name))
            events.append(Event(c,start,end-1))
            for t in range(start,end):
                value=amp*shape(name,(t-start+.5)/duration);latent[t][c]+=value;noisy[t][c]+=value
    observed=deepcopy(noisy);faults=[];fault_schedule=[]
    if kind!='clean':
        fr=stream(seed,'fault:'+channel);start=fr.randint(*fs['onset_s']);duration=fr.randint(*fs['duration_s']);recovery=fr.randint(*fs['recovery_s']);sign=fr.choice([-1,1]);end=start+duration
        params=dict(channel=channel,kind=kind,start_s=start,core_end_s=end,recovery_s=recovery,sign=sign)
        if kind=='range':params['value']=fs['range_values'][channel][0 if sign<0 else 1]
        if kind=='stuck':params['value']=noisy[start][channel]
        if kind=='spike':
            # Three isolated bursts. Each is a separate fault episode, rather than
            # labeling healthy gaps as faulty or assuming a 240 s spike.
            starts=sorted(fr.sample(range(start,end-4),3));intervals=[(s,s+fr.randint(1,3)) for s in starts]
            # Merge touching bursts so counts and injection have identical support.
            merged=[]
            for a,b in intervals:
                if merged and a<=merged[-1][1]:merged[-1]=(merged[-1][0],max(b,merged[-1][1]))
                else:merged.append((a,b))
            intervals=merged;params['amplitude']=sign*fr.uniform(*fs['spike_amplitude'][channel])
        else:intervals=[(start,end+recovery if kind in ('drift','stable_offset') else end)]
        if kind=='stable_offset':params['offset']=sign*fr.uniform(*fs['offset_amplitude'][channel])
        if kind=='drift':params['slopes']=[sign*fr.uniform(*fs['drift_slope'][channel]) for _ in range(3)]
        for a,b in intervals:
            faults.append(Fault(channel,a,b,kind));fault_schedule.append(dict(params,start_s=a,end_exclusive_s=b))
            accumulated=0.
            for t in range(a,b):
                value=noisy[t][channel]
                if kind=='range':value=params['value']
                elif kind=='stuck':value=params['value']
                elif kind=='missing':value=None
                elif kind=='invalid':value=float('nan')
                elif kind=='spike':value+=params['amplitude']
                elif kind=='stable_offset':value+=params['offset']*min(1,(b-t)/recovery)
                elif kind=='drift':
                    if t<end:accumulated+=params['slopes'][min(2,3*(t-start)//duration)]
                    value+=accumulated*(1 if t<end else (b-t)/recovery)
                observed[t][channel]=value
    return TransferTrace(case,relation,'mixed',seed,latent,noisy,observed,sorted(events,key=lambda e:(e.start_s,e.channel)),faults,dict(generator_version=spec['version'],parameters=deepcopy(spec),centers=dict(zip(CHANNELS,centers)),noise_rho=noise_rho,environment_segments=segments,noise_segments=noise_segments,event_schedule=schedule,fault_schedule=fault_schedule,event_family=family,rng_derivation='SHA256(tais-transfer-v1:seed:stream), first128bits; environment/noise/events:family/fault:channel'))

def counterfactual(trace):
    """Remove only faulty observation replacement; never draw RNGs again."""
    cf=deepcopy(trace);cf.observed=deepcopy(trace.noisy);cf.faults=[];cf.metadata['fault_schedule']=[]
    return cf
