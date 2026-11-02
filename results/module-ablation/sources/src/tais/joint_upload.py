"""Stateless-frame emission, last-sent deadband and mandatory state edges."""
from copy import deepcopy
from .replay import finite

class Upload:
    def __init__(self, noise, heartbeat=120):
        self.noise = noise
        self.heartbeat = heartbeat
        self.last = None
        self.time = None

    def decide(self, t, values, active, health):
        now = dict(values={n:v if finite(v) else None for n,v in values.items()},
                   active=dict(active), health=deepcopy(health))
        reasons=[]
        if self.last is None:
            reasons.append('first')
        else:
            for n,v in now['values'].items():
                old=self.last['values'][n]
                if (v is None)!=(old is None):reasons.append('validity:'+n)
                elif v is not None and abs(v-old)>=2*self.noise[n]:reasons.append('deadband:'+n)
                if active[n]!=self.last['active'][n]:reasons.append('event_edge:'+n)
                # Score is NOT discarded: each sent snapshot carries the exact current score.
                h=health[n];p=self.last['health'][n]
                if (h['state'],h['flags'])!=(p['state'],p['flags']):reasons.append('health_edge:'+n)
            if t-self.time>=self.heartbeat:reasons.append('heartbeat')
        if reasons:self.last=now;self.time=t
        return reasons
