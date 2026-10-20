"""Synchronize an observed unconfirmed return with v0.2's existing reseed."""
import math
from tais_v02.evidence import Evidence as FrozenEvidence

class ReturnedReferenceEvidence(FrozenEvidence):
    def step(self,t,value,state,score,raw_active,reference,threshold,floor):
        prior=self.episode
        prior_pending=prior is not None and prior.phase=='PENDING' and t>prior.start
        event,pending,actions=super().step(t,value,state,score,raw_active,reference,threshold,floor)
        returned=(prior_pending and value is not None and math.isfinite(value)
                  and state in ('HEALTHY','DEGRADED')
                  and abs(value-prior.reference)<=threshold*floor)
        cancelled=any(a['action']=='cancelled' and a['reason']=='displacement_returned' for a in actions)
        if returned and cancelled and self.episode is None:
            # The unchanged scheduler resets its scorer on the cancellation action.
            # Never authorize the cancellation sample from its stale raw debounce.
            self.blocked=False
            actions.append(dict(t=t,action='rearmed',reason='reference_return_reset',
                                episode_start=prior.start,reference=prior.reference,
                                count=prior.count,phase='IDLE'))
            return False,False,actions
        return event,pending,actions
