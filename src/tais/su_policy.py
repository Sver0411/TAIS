"""SU-1: frozen JO-S (H=False) or frozen GateOnly, with unchanged Upload.

No new health classifier, residual override or application fault bit. The
underlying policy still maintains its own original upload bookkeeping; this
wrapper only replaces the final emission decision, never feeds U back to it.
"""
from copy import deepcopy
from .scheduler import Scheduler
from .joint_policy import JointPolicy
from .joint_upload import Upload
from .core_stream import CoreSender,render

class SUPolicy:
    def __init__(self,cfg,cap=20,sampling='jo-s'):
        if sampling not in ('jo-s','gateonly') or cap not in (20,30,40):
            raise ValueError('SU supports frozen sampling and caps20/30/40 only')
        self.sampling=sampling
        self.base=(JointPolicy(cfg,dict(idle_interval_s=cap,trend_slope=.005,heartbeat_s=120),variant='JO-S')
                   if sampling=='jo-s' else Scheduler(cfg,confirmation=False,multiplier=1.))
        if sampling=='jo-s':
            assert self.base.health_layer is False and self.base.upload_layer is False
        self.trust=self.base.trust
        b=self.base.b
        self.up=Upload({n:b['adaptive']['channels'][n]['noise_floor'] for n in cfg['channels']},heartbeat=120)
        self.last_diagnostics={}

    def update(self,t,values):
        d=self.base.update(t,values)
        self.last_diagnostics=deepcopy(getattr(self.base,'last_diagnostics',{}))
        original=dict(upload=d.upload,reasons=list(d.reasons))
        d.reasons=self.up.decide(t,values,d.active,d.health)
        d.upload=bool(d.reasons)
        self.original_upload=original
        return d

class SUSender(CoreSender):
    def __init__(self,cfg,cap=20,layout_id=1,sampling='jo-s'):
        super().__init__(cfg,layout_id)
        self.close()
        self.scheduler=SUPolicy(cfg,cap,sampling)

    def push(self,row):
        result=super().push(row)
        if result is not None:
            result['record']['su']=dict(sampling=self.scheduler.sampling,health_layer=False,
                                       original_upload=deepcopy(self.scheduler.original_upload))
            detector=self.scheduler.base.base if self.scheduler.sampling=='jo-s' else self.scheduler.base
            result['record']['su']['candidate_starts']={n:a._potential_start for n,a in detector.analyzers.items()}
            # Exact JO-S diagnostics are exposed for engineering parity only.
            if self.scheduler.sampling=='jo-s':
                result['record']['joint']=deepcopy(self.scheduler.last_diagnostics)
        return result

def su_render(sender,receiver,label):
    name='GateOnly+U' if sender.scheduler.sampling=='gateonly' else 'JO-SU (H disabled)'
    return render(sender,receiver,label).replace('GateOnly |',name+' |')
