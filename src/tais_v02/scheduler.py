"""Narrow fork of v0.1 update: only candidate policy and its demand change.

Legacy scheduler.py remains byte-identical. AdaptiveSense scoring, transition,
ladders and real C11 SensorTrust are imported unchanged. See V02_DESIGN.md.
"""
from dataclasses import dataclass, asdict
import math
from tais.scheduler import Scheduler as LegacyScheduler, Decision
from tais.config import baseline
from tais.trust import SensorTrust
from simulator.scoring import ChangeAnalyzer
from simulator.config import analyzer_config, ladder, confirmations
from simulator.adaptive import transition, next_rung, hysteresis_bounds
from .evidence import Evidence

@dataclass
class DecisionV02(Decision):
    evidence: dict

class Scheduler(LegacyScheduler):
    def __init__(self,cfg,confirmation=True,multiplier=1.0):
        super().__init__(cfg,confirmation=True,multiplier=multiplier)
        self.accelerated=confirmation
        self.evidence={n:Evidence(cfg['v02']) for n in self.names}

    def update(self,t,values):
        if not math.isfinite(t) or t<0 or t<=self.last_t:raise ValueError('Nonmonotonic timestamp')
        self.last_t=t
        cfg=self.cfg;tr=cfg['v02'];lo=cfg['sampling']['min_interval_s'];hi=cfg['sampling']['max_interval_s']
        health={n:self.trust[n].update(t,values.get(n)) for n in self.names}
        scores={};active={};intervals=[];onsets=[];reasons=[];reset=[];evidence={}
        confirming=False;diagnostic=False;changed=False
        trusted_values={}
        for n in self.names:
            h=health[n];v=values.get(n)
            valid=v is not None and math.isfinite(v)
            if h.state!=self.previous_health[n] or h.flags!=self.previous_flags[n]:reasons.append('health:'+n)
            unusable=h.state=='FAULT' or not valid
            raw_score=0.0;candidate=False;reference=v if valid else None
            if unusable:
                self.bad[n]=True
                score=0.0
            else:
                if self.bad[n]:
                    self.analyzers[n]=ChangeAnalyzer(analyzer_config(self.b))
                    self.level[n]='STABLE';self.pos[n]=self.count[n]=0
                    self.evidence[n].episode=None;self.evidence[n].blocked=False
                    reset.append(n);self.bad[n]=False
                reference=self.analyzers[n].baseline(n)
                if reference is None:reference=v
                raw_score,_,candidate=self.analyzers[n].update(t,{n:v})
                score=raw_score
            event,pending,actions=self.evidence[n].step(
                t,v if valid else None,h.state,raw_score,candidate,reference,
                self.b['adaptive']['event_threshold'],self.b['adaptive']['channels'][n]['noise_floor'])
            evidence[n]=dict(raw_score=raw_score,raw_active=candidate,pre_ema=reference,
                             phase=self.evidence[n].episode.phase if self.evidence[n].episode else ('BLOCKED' if self.evidence[n].blocked else 'IDLE'),
                             actions=actions)
            if any(a['reason']=='displacement_returned' for a in actions):
                self.analyzers[n]=ChangeAnalyzer(analyzer_config(self.b))
                self.analyzers[n].update(t,{n:v});score=0.0
            if pending and self.accelerated:
                confirming=True;intervals.append(tr['confirmation_interval_s'])
            if pending:
                remaining=self.evidence[n].episode.start+tr['max_confirmation_duration_s']-t
                intervals.append(max(lo,remaining))
            if unusable or (h.state=='DEGRADED' and not event):
                score=0.0;intervals.append(tr['diagnostic_interval_s']);diagnostic=True
            if h.state=='HEALTHY' and valid:trusted_values[n]=v
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
        return DecisionV02(t,interval,state,scores,{n:asdict(h) for n,h in health.items()},active,onsets,upload,reasons,confirming,diagnostic,reset,evidence)
