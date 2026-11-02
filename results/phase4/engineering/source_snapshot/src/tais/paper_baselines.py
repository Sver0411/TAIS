"""Independent causal samplers for the paper; frozen TAIS code is not imported.

Only sampled (t, values) enter these policies. Units are normalized by the
public detector noise floors, not by latent observations or fault/event labels.
Rao-inspired is an engineering adaptation, NOT a reproduction of CS+prediction.
"""
from collections import deque
from dataclasses import asdict
import math
from .config import baseline
from .replay import finite,run as frozen_run
from .trust import SensorTrust
from .joint_upload import Upload
from simulator.scoring import ChangeAnalyzer
from simulator.config import analyzer_config
from simulator.events import Event

class IndependentSampler:
    def __init__(self,kind,noise,cap=60,threshold=4,center=None,minimum=5):
        if kind not in ('Delta','Variance','Rao-inspired'):raise ValueError(kind)
        if not 5<=minimum<=cap<=60 or threshold<=0:raise ValueError('invalid operating point')
        self.minimum=minimum;self.kind=kind;self.noise=noise;self.cap=cap;self.threshold=threshold
        self.center=center or {};self.last_t=None;self.previous={};self.interval=cap
        self.stable_since=None;self.mean={};self.var={};self.history={n:deque(maxlen=4) for n in noise}
    def update(self,t,values):
        if not math.isfinite(t) or t<0 or (self.last_t is not None and t<=self.last_t):raise ValueError('nonmonotonic timestamp')
        dt=t-self.last_t if self.last_t is not None else 0
        trigger=False
        for n,nf in self.noise.items():
            v=values.get(n);old=self.previous.get(n)
            if self.last_t is not None and finite(v)!=finite(old):trigger=True
            if not finite(v):continue
            if self.kind=='Delta' and finite(old) and dt>0:
                change=abs(v-old)/nf
                trigger|=max(change,20*change/dt)>=self.threshold
            elif self.kind=='Variance':
                if n not in self.mean:self.mean[n]=v;self.var[n]=0.
                else:
                    a=-math.expm1(-dt/60);d=v-self.mean[n]
                    self.mean[n]+=a*d;self.var[n]=(1-a)*(self.var[n]+a*d*d)
                trigger|=math.sqrt(max(0,self.var[n]))/nf>=self.threshold
            elif self.kind=='Rao-inspired':
                h=self.history[n];h.append((t,v));band=self.threshold*nf;c=self.center[n]
                trigger|=abs(v-c)>=band
                if len(h)>=2:
                    mt=sum(x for x,y in h)/len(h);mv=sum(y for x,y in h)/len(h)
                    den=sum((x-mt)**2 for x,y in h)
                    slope=sum((x-mt)*(y-mv) for x,y in h)/den if den else 0
                    if abs(slope)>1e-12:
                        boundary=c+(band if slope>0 else -band)
                        crossing=(boundary-(mv+slope*(t-mt)))/slope
                        trigger|=0<=crossing<=self.cap
                # Return to sparse only after sampled observations are inside
                # a narrower band; this is our hysteresis, not Rao's APDT.
                if self.interval<self.cap and abs(v-c)>=.75*band:trigger=True
        if trigger:
            self.interval=self.minimum;self.stable_since=None
        else:
            if self.stable_since is None:self.stable_since=t
            if t-self.stable_since>=60:
                self.interval=min(self.cap,max(self.minimum,self.interval*2));self.stable_since=t
        self.last_t=t;self.previous=dict(values)
        return self.interval

def episodes(records,names):
    detections=[];reports=[]
    for n in names:
        start=last=None;sent=False
        for r in records:
            if r['active'][n]:
                if start is None:start=r['timestamp'];sent=False
                last=r['timestamp']
                if r['upload'] and not sent:reports.append(Event(n,r['timestamp'],r['timestamp']));sent=True
            elif start is not None:detections.append(Event(n,start,last));start=None
        if start is not None:detections.append(Event(n,start,last))
    return dict(records=records,detections=detections,reports=sorted(reports,key=lambda e:(e.start_s,e.channel)))

def run_independent(trace,cfg,spec):
    if spec['kind']=='Fixed':
        # Exactly reuse existing scheduling / detection / upload semantics.
        return frozen_run(trace,cfg,'Fixed-'+str(spec['cap']))
    b=baseline(cfg);names=tuple(cfg['channels'])
    sampler=IndependentSampler(spec['kind'],{n:b['adaptive']['channels'][n]['noise_floor'] for n in names},spec['cap'],spec['threshold'],cfg['synthetic']['baseline'],spec.get('minimum',5))
    detectors={n:ChangeAnalyzer(analyzer_config(b)) for n in names}
    next_sample=0;records=[];previous=-1
    for row in trace.observed:
        t=row['timestamp']
        if not math.isfinite(t) or t<=previous:raise ValueError('invalid source timestamps')
        previous=t
        if t<next_sample:continue
        values={n:row[n] for n in names};interval=sampler.update(t,values);active={};scores={}
        for n in names:
            score,_,a=detectors[n].update(t,{n:values[n]} if finite(values[n]) else {})
            active[n]=a;scores[n]=score
        records.append(dict(timestamp=t,values=values,interval=interval,upload=True,payload_bytes=0,active=active,health={},state=spec['kind'],scores=scores,reasons=['every_sample'],confirmation=False,diagnostic=False,recovery_reset=[]))
        next_sample=t+interval
    return episodes(records,names)

def decorate(result,cfg,common=False,health=True,upload=False):
    """Public adapters; never feed these results back to native schedules.

    common=True replaces detection and emission, preserving actual sample times.
    health=True attaches raw unchanged C11; it does not gate independent methods.
    upload=True explicitly adds the common TAIS U emission diagnostic.
    """
    b=baseline(cfg);names=tuple(cfg['channels']);trust={n:SensorTrust(cfg['channels'][n]['trust']) for n in names} if health else {}
    detectors={n:ChangeAnalyzer(analyzer_config(b)) for n in names} if common else {}
    up=Upload({n:b['adaptive']['channels'][n]['noise_floor'] for n in names},120) if upload else None
    records=[]
    try:
        for old in result['records']:
            r=dict(old);t=r['timestamp'];values=r['values']
            if common:
                r['active']={n:detectors[n].update(t,{n:values[n]} if finite(values[n]) else {})[2] for n in names}
                r['upload']=True;r['reasons']=['common_detector_every_sample']
            r['health']={n:asdict(c.update(t,values[n])) for n,c in trust.items()}
            if up:r['reasons']=up.decide(t,values,r['active'],r['health']);r['upload']=bool(r['reasons'])
            records.append(r)
    finally:
        for c in trust.values():c.close()
    return episodes(records,names)
