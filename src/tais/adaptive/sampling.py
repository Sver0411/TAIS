"""Bounded, deterministic samplers using only acquired values and raw health."""
from collections import deque
import math
from statistics import median


class SamplingHistory:
    def __init__(self, noise, options):
        self.noise = dict(noise)
        self.o = dict(options)
        o = self.o
        if any(isinstance(v,(int,float)) and not math.isfinite(v) for v in o.values()):
            raise ValueError('Sampling parameters must be finite')
        if not self.noise or any(not math.isfinite(v) or v <= 0 for v in self.noise.values()):
            raise ValueError('Positive finite channel scales required')
        if not 0 < o['min_interval_s'] <= o['watch_interval_s'] <= o['cooldown_interval_s'] <= o['idle_interval_s'] <= o['max_interval_s']:
            raise ValueError('Invalid interval ordering')
        if not o['min_interval_s'] <= o['diagnostic_interval_s'] <= o['max_interval_s']:
            raise ValueError('Invalid diagnostic interval')
        if o['window_samples'] < 3 or o['fast_limit'] < 1 or o['confirm_samples'] < 2:
            raise ValueError('Invalid sample windows')
        if not 0 < o['exit_z'] < o['enter_z'] or min(o['fast_window_s'],o['cooldown_s'],o['max_burst_s'],o['mad_multiplier']) <= 0:
            raise ValueError('Invalid hysteresis/budget parameters')
        self.history = {n: deque(maxlen=o['window_samples']) for n in noise}
        self.fast = deque()
        self.last_t = None
        self.last_interval = None
        self.state = 'QUIET'
        self.cool_until = -1
        self.burst_start = None
        self.confirmed = 0
        self.lead = None

    def features(self, t, values, health):
        features = {}
        diagnostic = False
        for n, nf in self.noise.items():
            value = values[n]
            eligible = value is not None and math.isfinite(value) and health[n]['state'] == 'HEALTHY'
            h = self.history[n]
            if not eligible:
                h.clear()
                diagnostic = True
                continue
            center = median(v for _, v in h) if h else value
            scale = max(nf, self.o['mad_multiplier']*median(abs(v-center) for _, v in h)) if h else nf
            slope = 0.;prediction = None;consistency = 0.
            if len(h) >= 3:
                slopes = [(b-a)/(tb-ta) for i,(ta,a) in enumerate(h) for tb,b in list(h)[i+1:]]
                slope = median(slopes)
                prediction = median(v-slope*tt for tt,v in h)+slope*t
                changes = [b-a for (_,a),(_,b) in zip(h,list(h)[1:]) if b != a]
                consistency = sum(d*slope > 0 for d in changes)/len(changes) if changes else 0.
            delta = value-center
            features[n] = dict(z=abs(delta)/scale, scale=scale, center=center,
                               sign=1 if delta > 0 else -1 if delta < 0 else 0,
                               slope=slope,prediction=prediction,consistency=consistency,
                               residual=value-prediction if prediction is not None else None)
            h.append((t,value))
        return features, diagnostic

    def update(self, t, values, health):
        o = self.o
        if not math.isfinite(t) or t < 0 or self.last_t is not None and t < self.last_t+self.last_interval-1e-9:
            raise ValueError('Acquisitions must increase and respect the previously requested interval')
        if self.last_t is not None and t-self.last_t <= o['min_interval_s']+1e-9:
            self.fast.append(t)
        while self.fast and self.fast[0] <= t-o['fast_window_s']:
            self.fast.popleft()
        if len(self.fast) > o['fast_limit']:
            raise ValueError('Actual acquisitions exceeded rolling fast budget')
        features, diagnostic = self.features(t,values,health)
        interval, score = self.request(t,features)
        if diagnostic:
            interval = min(interval,o['diagnostic_interval_s'])
        blocked = False
        # Admission at the proposed due time, using ACTUAL past acquisitions.
        if interval <= o['min_interval_s']:
            due = t+o['min_interval_s']
            used = sum(s > due-o['fast_window_s'] for s in self.fast)
            if used >= o['fast_limit']:
                blocked = True
                self.cool(t)
                interval = o['cooldown_interval_s']
        interval = max(o['min_interval_s'],min(o['max_interval_s'],interval))
        self.last_t = t;self.last_interval = interval
        return interval,dict(state=self.state,score=score,features=features,
                             fast_used=len(self.fast),fast_blocked=blocked,
                             diagnostic=diagnostic,cool_until=self.cool_until,
                             confirmations=self.confirmed)

    def cool(self,t):
        self.state='COOLDOWN';self.cool_until=t+self.o['cooldown_s']
        self.burst_start=None;self.confirmed=0;self.lead=None

    def active_request(self,t,score,lead,enter,retain,quiet):
        """Shared physical persistence/cooldown limits, not an event detector."""
        o=self.o
        if self.state=='COOLDOWN':
            if t<self.cool_until:return o['cooldown_interval_s']
            self.state=quiet
        if self.burst_start is not None:
            if t-self.burst_start>=o['max_burst_s'] or score<retain or lead!=self.lead:
                self.cool(t);return o['cooldown_interval_s']
            self.confirmed+=1
            self.state='TRACK' if self.confirmed>=o['confirm_samples'] else 'PROBE'
            return o['min_interval_s']
        if score>=enter:
            self.burst_start=t;self.confirmed=1;self.lead=lead;self.state='PROBE'
            return o['min_interval_s']
        self.state=quiet
        return o['idle_interval_s']


class RobustSampler(SamplingHistory):
    """Median/MAD displacement, signed persistence, bounded probes."""
    def request(self,t,features):
        name=max(features,key=lambda n:features[n]['z']) if features else None
        score=features[name]['z'] if name is not None else 0.
        lead=(name,features[name]['sign']) if name is not None else None
        return self.active_request(t,score,lead,self.o['enter_z'],self.o['exit_z'],'QUIET'),score


class RiskAwareSampler(SamplingHistory):
    """Past-only robust trend forecast plus displacement/forecast residual risk."""
    def __init__(self,noise,options):
        super().__init__(noise,options)
        if not 0<self.o['risk_exit']<self.o['risk_enter'] or not 0<self.o['trend_consistency']<=1 or self.o['horizon_s']<=0:
            raise ValueError('Invalid risk parameters')

    def request(self,t,features):
        for f in features.values():
            trend=abs(f['slope'])*self.o['horizon_s']/(self.o['enter_z']*f['scale']) if f['consistency']>=self.o['trend_consistency'] else 0.
            residual=abs(f['residual'])/(self.o['enter_z']*f['scale']) if f['residual'] is not None else 0.
            f['risk']=max(f['z']/self.o['enter_z'],trend,residual)
            f['risk_sign']=(1 if f['slope']>0 else -1) if trend>=max(residual,f['z']/self.o['enter_z']) and trend>0 else f['sign']
        name=max(features,key=lambda n:features[n]['risk']) if features else None
        score=features[name]['risk'] if name is not None else 0.
        lead=(name,features[name]['risk_sign']) if name is not None else None
        interval=self.active_request(t,score,lead,self.o['risk_enter'],self.o['risk_exit'],'LOW')
        if self.burst_start is not None:
            self.state='HIGH' if self.confirmed>=self.o['confirm_samples'] else 'HIGH_PROBE'
        if self.state=='LOW' and score>=self.o['risk_exit']:
            self.state='WATCH';interval=self.o['watch_interval_s']
        return interval,score
