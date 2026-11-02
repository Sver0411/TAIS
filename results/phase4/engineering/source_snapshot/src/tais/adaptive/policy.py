"""Optional sampling replacement: original C11, detector, U and wire contract."""
from copy import deepcopy

from tais.scheduler import Scheduler
from tais.trust import Health
from tais.joint_upload import Upload
from tais.core_stream import CoreSender
from .sampling import RobustSampler, RiskAwareSampler


class NeutralHealth:
    def update(self,t,value):
        return Health(100,'HEALTHY',0)

    def close(self):
        pass


class Phase4Policy:
    def __init__(self,cfg,plan,kind,trust=True,selective=True):
        if kind not in ('Robust','Risk'):
            raise ValueError(kind)
        self.base=Scheduler(cfg,confirmation=False)
        if not trust:
            for engine in self.base.trust.values():engine.close()
            self.base.trust={n:NeutralHealth() for n in cfg['channels']}
        self.trust=self.base.trust
        self.selective=selective
        noise={n:self.base.b['adaptive']['channels'][n]['noise_floor'] for n in cfg['channels']}
        options={**plan['common'],**plan['robust' if kind=='Robust' else 'risk']}
        self.sampler=(RobustSampler if kind=='Robust' else RiskAwareSampler)(noise,options)
        self.up=Upload(noise,heartbeat=120)
        self.last_diagnostics={}

    def update(self,t,values):
        d=self.base.update(t,values)
        d.interval,self.last_diagnostics=self.sampler.update(t,values,d.health)
        d.reasons=self.up.decide(t,values,d.active,d.health) if self.selective else ['every_sample']
        d.upload=bool(d.reasons)
        return d


class Phase4Sender(CoreSender):
    def __init__(self,cfg,plan,kind,trust=True,selective=True,layout_id=1):
        super().__init__(cfg,layout_id)
        self.close()
        self.scheduler=Phase4Policy(cfg,plan,kind,trust,selective)

    def push(self,row):
        item=super().push(row)
        if item is not None:
            item['record']['adaptive']=deepcopy(self.scheduler.last_diagnostics)
            item['record']['candidate_starts']={n:a._potential_start for n,a in self.scheduler.base.analyzers.items()}
            from math import isfinite
            item['record']['detector_candidates']={n:bool(a.event_active and row[n] is not None and isfinite(row[n]) and
                                                         item['record']['health'][n]['state']!='FAULT')
                                                   for n,a in self.scheduler.base.analyzers.items()}
        return item
