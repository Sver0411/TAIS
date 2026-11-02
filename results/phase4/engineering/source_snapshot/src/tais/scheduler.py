"""Causal per-channel trust gate using unchanged AdaptiveSense primitives."""
from dataclasses import asdict, dataclass
import math
from .config import baseline
from .trust import SensorTrust
from simulator.scoring import ChangeAnalyzer
from simulator.config import analyzer_config, ladder, confirmations
from simulator.adaptive import transition,next_rung,hysteresis_bounds

@dataclass
class Decision:
    t: float
    interval: float
    state: str
    scores: dict
    health: dict
    active: dict
    onsets: list
    upload: bool
    reasons: list
    confirmation: bool
    diagnostic: bool
    recovery_reset: list

class Scheduler:
    """Receives current sampled values only. No trace, labels or truth input."""
    def __init__(self,cfg,confirmation=True,multiplier=1.0):
        self.cfg=cfg;self.b=baseline(cfg,multiplier);self.confirmation=confirmation
        self.names=tuple(cfg['channels'])
        self.trust={n:SensorTrust(cfg['channels'][n]['trust']) for n in self.names}
        self.analyzers={n:ChangeAnalyzer(analyzer_config(self.b)) for n in self.names}
        self.previous_health={n:'HEALTHY' for n in self.names}
        self.previous_flags={n:0 for n in self.names}
        self.bad={n:False for n in self.names}
        self.pending={n:None for n in self.names}
        self.blocked={n:False for n in self.names}
        self.previous_active={n:False for n in self.names}
        self.level={n:'STABLE' for n in self.names}
        self.pos={n:0 for n in self.names};self.count={n:0 for n in self.names}
        a=self.b['adaptive']
        self.bounds=hysteresis_bounds(a['stable_threshold'],a['active_threshold'],a['hysteresis_fraction'])
        self.last_t=-1;self.last_upload=None;self.upload_values={}

    def update(self,t,values):
        if not math.isfinite(t) or t<0 or t<=self.last_t:raise ValueError('Nonmonotonic timestamp')
        self.last_t=t
        cfg=self.cfg;tr=cfg['trust'];lo=cfg['sampling']['min_interval_s'];hi=cfg['sampling']['max_interval_s']
        health={n:self.trust[n].update(t,values.get(n)) for n in self.names}
        scores={};active={};intervals=[];onsets=[];reasons=[];reset=[]
        confirming=False;diagnostic=False;changed=False
        trusted_values={}
        for n in self.names:
            h=health[n];v=values.get(n)
            valid=v is not None and math.isfinite(v)
            if h.state!=self.previous_health[n] or h.flags!=self.previous_flags[n]:reasons.append('health:'+n)
            unusable=h.state=='FAULT' or not valid
            if unusable:
                self.bad[n]=True;self.pending[n]=None;self.blocked[n]=False
                score=0.0;event=False
                intervals.append(tr['diagnostic_interval_s']);diagnostic=True
            else:
                rewarming=self.bad[n]
                if rewarming:
                    self.analyzers[n]=ChangeAnalyzer(analyzer_config(self.b))
                    self.level[n]='STABLE';self.pos[n]=self.count[n]=0
                    self.pending[n]=None;self.blocked[n]=False
                    reset.append(n);self.bad[n]=False
                score,_,candidate=self.analyzers[n].update(t,{n:v})
                event=False
                if h.state=='HEALTHY':
                    if self.pending[n] is not None:
                        # A suspect step must persist in value, not merely in the EMA residual.
                        start,count,reference=self.pending[n]
                        persistent=abs(v-reference)/self.b['adaptive']['channels'][n]['noise_floor']>self.b['adaptive']['event_threshold']
                        count=count+1 if persistent else 0
                        event=candidate and persistent and count>=tr['degraded_confirmation_samples'] and t-start>=self.b['adaptive']['event_min_duration_s']
                        if not persistent or event or t-start>=tr['max_confirmation_duration_s']:
                            self.pending[n]=None
                        else:
                            self.pending[n]=(start,count,reference);confirming=True;intervals.append(lo)
                        if not persistent:
                            # Discard the isolated excursion, including its residual score.
                            self.analyzers[n]=ChangeAnalyzer(analyzer_config(self.b))
                            self.analyzers[n].update(t,{n:v});score=0.0
                    else:event=candidate
                    trusted_values[n]=v
                    self.blocked[n]=False
                elif self.confirmation:
                    trigger=score>=self.bounds['active_high']
                    if not trigger:
                        self.pending[n]=None;self.blocked[n]=False
                    elif self.pending[n] is None and not self.blocked[n]:
                        # baseline was updated by scorer; use the previous accepted reading as reference
                        self.pending[n]=(t,1,getattr(self,'last_values',{}).get(n,v))
                    if self.pending[n] is not None:
                        start,count,reference=self.pending[n]
                        persistent=abs(v-reference)/self.b['adaptive']['channels'][n]['noise_floor']>self.b['adaptive']['event_threshold']
                        if t>start:count=count+1 if persistent else 0
                        event=candidate and persistent and count>=tr['degraded_confirmation_samples'] and t-start>=self.b['adaptive']['event_min_duration_s']
                        if event or not persistent or t-start>=tr['max_confirmation_duration_s']:
                            self.pending[n]=None;self.blocked[n]=True
                            if not persistent:
                                self.analyzers[n]=ChangeAnalyzer(analyzer_config(self.b))
                                self.analyzers[n].update(t,{n:v})
                                score=0.0
                        else:
                            self.pending[n]=(start,count,reference);confirming=True;intervals.append(lo)
                    if not event:
                        score=0.0;intervals.append(tr['diagnostic_interval_s']);diagnostic=True
                else:
                    score=0.0;self.pending[n]=None
                    intervals.append(tr['diagnostic_interval_s']);diagnostic=True
            allowed=not unusable and (h.state=='HEALTHY' or event)
            prev=self.level[n]
            self.level[n]=transition(prev,score if allowed else 0.0,self.bounds)
            if prev!=self.level[n]:
                self.pos[n]=self.count[n]=0;changed=True
            interval,self.pos[n],self.count[n]=next_rung(self.pos[n],self.count[n],ladder(self.b,self.level[n]),confirmations(self.b,self.level[n]))
            # Unusable channels do not impose a STABLE ladder on healthy ones.
            if allowed:intervals.append(interval)
            scores[n]=score;active[n]=bool(event and allowed)
            if active[n] and not self.previous_active[n]:onsets.append(n)
        interval=max(lo,min(hi,min(intervals,default=hi)))
        if changed:reasons.append('scheduler_state')
        if interval!=getattr(self,'last_interval',None):reasons.append('interval')
        if onsets:reasons.append('environment_event')
        if self.last_upload is None:reasons.append('first')
        elif t-self.last_upload>=cfg['sampling']['heartbeat_s']:reasons.append('heartbeat')
        for n,v in trusted_values.items():
            if n in self.upload_values and abs(v-self.upload_values[n])/self.b['adaptive']['channels'][n]['noise_floor']>=self.b['adaptive']['upload']['delta_threshold']:
                reasons.append('trusted_delta:'+n)
        upload=bool(reasons)
        if upload:self.last_upload=t;self.upload_values.update(trusted_values)
        self.previous_health={n:h.state for n,h in health.items()};self.previous_active=active
        self.previous_flags={n:h.flags for n,h in health.items()}
        self.last_values={n:v for n,v in values.items() if v is not None and math.isfinite(v)}
        self.last_interval=interval
        state=max(self.level.values(),key=lambda x:('STABLE','ACTIVE','ALERT').index(x))
        return Decision(t,interval,state,scores,{n:asdict(h) for n,h in health.items()},active,onsets,upload,reasons,confirming,diagnostic,reset)
