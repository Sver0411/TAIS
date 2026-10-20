"""Bounded, signed persistence episode; no trace or label inputs."""
from dataclasses import dataclass

@dataclass
class Episode:
    """Signed displacement candidate retaining its creation-time reference in native units."""
    start: float
    reference: float
    sign: int
    count: int = 1
    phase: str = 'PENDING'

class Evidence:
    """One bounded persistence candidate plus a post-cancellation BLOCKED latch.

    Persistence is sampled evidence, not proof that a change is environmental.
    The legacy latch can remain through health recovery until score falls."""
    def __init__(self, params):
        self.params=params;self.episode=None;self.blocked=False

    def step(self,t,value,state,score,raw_active,reference,threshold,floor):
        """Return (event, pending, lifecycle actions) and mutate candidate/latch state.

        Time uses seconds; threshold is noise-normalized and floor has measurement
        units. Missing/FAULT input cancels and clears the latch. A degraded change
        can create a candidate whose sign/reference stay fixed. Confirmation needs
        sample count, duration and raw detector activity; expiry/return/release
        can block recreation. HEALTHY raw activity is admitted only when unblocked."""
        events=[];event=False
        def log(action,reason):
            e=self.episode
            events.append(dict(t=t,action=action,reason=reason,episode_start=e.start if e else None,
                               reference=e.reference if e else None,count=e.count if e else 0,
                               phase=e.phase if e else 'IDLE'))
        if value is None or state=='FAULT':
            if self.episode:log('cancelled','unusable')
            self.episode=None;self.blocked=False
            return False,False,events
        if self.blocked and score<=threshold:self.blocked=False;log('rearmed','score_low')
        if self.episode is None and state=='DEGRADED' and not self.blocked and score>threshold:
            delta=value-reference
            self.episode=Episode(t,reference,1 if delta>=0 else -1)
            log('created','degraded_change')
        e=self.episode
        if e:
            persistent=(value-e.reference)*e.sign>threshold*floor
            if e.phase=='CONFIRMED':
                event=bool(persistent and raw_active)
                if not event:
                    log('released','evidence_ended');self.episode=None;self.blocked=True
            elif t-e.start>=self.params['max_confirmation_duration_s']:
                log('cancelled','deadline');self.episode=None;self.blocked=True
            elif not persistent:
                log('cancelled','displacement_returned');self.episode=None;self.blocked=True
            else:
                if t>e.start:e.count+=1
                if raw_active and e.count>=self.params['confirmation_samples'] and t-e.start>=self.params['min_duration_s']:
                    e.phase='CONFIRMED';event=True;log('confirmed','sampled_persistence')
                else:log('retained','sampled_persistence')
        # A blocked/cancelled candidate remains blocked through health recovery.
        if self.episode is None and not self.blocked and state=='HEALTHY':event=bool(raw_active)
        pending=bool(self.episode and self.episode.phase=='PENDING')
        return event,pending,events
