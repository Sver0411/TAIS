"""TAIS-JO experimental composition; frozen GateOnly and C11 stay unchanged.

Application bit32 denotes a trend suspicion, NOT a diagnosed physical fault.
The robust predictor only suppresses smooth-trend evidence; an abrupt residual
can independently open an environmental candidate even during a trend.
"""
from collections import deque
from copy import deepcopy
from dataclasses import asdict
from statistics import median
import math
from .scheduler import Scheduler
from .joint_sampling import Rechecks
from .joint_upload import Upload
from .core_stream import CoreSender, render
from .replay import finite
from simulator.scoring import ChangeAnalyzer
from simulator.config import analyzer_config

APP_SUSPECT_DRIFT=32

class Trend:
    def __init__(self, noise, slope):
        self.history=deque(maxlen=9)
        self.noise=noise;self.threshold=slope
        self.suspect=False;self.prediction=None

    def update(self,t,v):
        old=self.suspect
        if not finite(v):
            self.history.clear();self.suspect=False;self.prediction=None
            return old,False,None
        h=self.history
        prediction=None
        if len(h)>=4 and h[-1][0]-h[0][0]>=60:
            slopes=[(b-a)/(tb-ta) for i,(ta,a) in enumerate(h) for tb,b in list(h)[i+1:] if tb>ta]
            slope=median(slopes)
            intercept=median(a-slope*ta for ta,a in h)
            error=median(abs(a-(intercept+slope*ta)) for ta,a in h)
            # Current value is not used in the forecast or its fit.
            prediction=intercept+slope*t
            smooth=error<=2*self.noise and abs(slope)>=self.threshold
            if smooth:self.suspect=True
            elif abs(slope)<self.threshold/2:self.suspect=False
        h.append((t,v))
        self.prediction=prediction
        return old,self.suspect,prediction

class JointPolicy:
    def __init__(self,cfg,options,variant='JO-Full'):
        self.cfg=deepcopy(cfg);self.options=deepcopy(options);self.variant=variant
        self.base=Scheduler(cfg,confirmation=False,multiplier=1.)
        self.trust=self.base.trust
        self.names=tuple(cfg['channels']);self.b=self.base.b
        self.health_layer=variant!='JO-S';self.upload_layer=variant=='JO-Full'
        self.noise={n:self.b['adaptive']['channels'][n]['noise_floor'] for n in self.names}
        self.trend={n:Trend(self.noise[n],options['trend_slope']) for n in self.names}
        self.checks={n:Rechecks() for n in self.names}
        self.previous={n:False for n in self.names}
        self.candidates={n:None for n in self.names}
        self.clean={n:False for n in self.names}
        self.up=Upload(self.noise,options['heartbeat_s'])
        self.last_application={n:False for n in self.names}
        self.last_diagnostics={}

    def update(self,t,values):
        d=self.base.update(t,values)
        intervals=[];app={};diagnostics={};raw=deepcopy(d.health)
        lo=self.cfg['sampling']['min_interval_s'];cap=self.options['idle_interval_s']
        for n in self.names:
            h=raw[n];v=values.get(n);old=False;sus=False;forecast=None
            if self.health_layer:old,sus,forecast=self.trend[n].update(t,v)
            usable=finite(v) and h['state']!='FAULT'
            step=bool(usable and forecast is not None and abs(v-forecast)>8*self.noise[n])
            c=self.candidates[n]
            if step and c is None:c=(t,forecast)
            if c is not None:
                start,reference=c
                if not usable or abs(v-reference)<=8*self.noise[n] or t-start>30:c=None
            special=bool(c and usable and t-c[0]>=10)
            self.candidates[n]=c
            if self.health_layer:
                if old and not sus:
                    # One causal reset at trend clearance; no indefinite mute period.
                    a=ChangeAnalyzer(analyzer_config(self.b));self.base.analyzers[n]=a
                    if usable:a.update(t,{n:v})
                    d.recovery_reset.append(n);d.active[n]=False;d.scores[n]=0.
                if sus or h['flags']&8:
                    # Smooth drift is evidence of ambiguity, not an environment onset.
                    # Abrupt residual must persist for >=10s and >=2 actual observations.
                    d.active[n]=special and not h['flags']&(1|2|4|16)
                    if not d.active[n]:d.scores[n]=0.
                if not usable:d.active[n]=False
            app[n]=sus
            d.health[n]['flags']=h['flags']|(APP_SUSPECT_DRIFT if sus else 0)
            if not usable:
                request=self.cfg['trust']['diagnostic_interval_s']
            elif self.health_layer and (sus or h['flags']&8):
                request=lo if c else cap
            else:
                request=min(d.interval,cap)
            probe=self.checks[n].interval(t,usable and d.scores[n]>=3 and not (sus and not step),lo)
            if probe is not None:request=min(request,probe)
            intervals.append(request)
            diagnostics[n]=dict(raw_c11=h,app_suspect_drift=sus,forecast=forecast,
                                candidate_start=c[0] if c else None,abrupt_residual=step)
        d.interval=max(lo,min(self.cfg['sampling']['max_interval_s'],min(intervals)))
        d.onsets=[n for n in self.names if d.active[n] and not self.previous[n]]
        if self.upload_layer:
            d.reasons=self.up.decide(t,values,d.active,d.health);d.upload=bool(d.reasons)
        elif self.health_layer:
            edges=[n for n in self.names if d.active[n]!=self.previous[n] or app[n]!=self.last_application[n]]
            if edges:d.reasons+=['jo_edge:'+n for n in edges];d.upload=True
        self.previous=dict(d.active);self.last_application=app
        self.last_diagnostics=diagnostics
        return d

class JointSender(CoreSender):
    def __init__(self,cfg,options,layout_id=1,variant='JO-Full'):
        super().__init__(cfg,layout_id)
        self.close()
        self.scheduler=JointPolicy(cfg,options,variant)

    def push(self,row):
        result=super().push(row)
        if result is not None:
            result['record']['joint']=deepcopy(self.scheduler.last_diagnostics)
        return result


def joint_render(sender,receiver,label):
    return render(sender,receiver,label).replace('GateOnly |','TAIS-JO experimental |').replace('0x20','APP_SUSPECT_DRIFT')
