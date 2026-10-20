"""Sample-driven causal replay, same observed stream for every method."""
from dataclasses import asdict
import json,math
from .scheduler import Scheduler
from .config import baseline
from .trust import SensorTrust
from simulator.adaptive import AdaptiveScheduler
from simulator.scoring import ChangeAnalyzer
from simulator.config import analyzer_config
from simulator.events import Event


def finite(v):return v is not None and math.isfinite(v)

def run(trace,cfg,method,multiplier=1.0):
    """Replay one observed trace through a named policy at actual sample times.

    Fixed-N reads at its requested N-second interval and uploads every sample.
    AdaptiveSense+TrustLog adds C11 metadata without gating baseline decisions;
    TAIS and GateOnly use the trust gate with and without confirmation.
    Detectors see sampled usable values only; labels are unused here.
    Return local episodes, first-upload reports and sampled records. Reports
    are sender intentions, not decoded receiver edges. payload_bytes counts
    serialized JSON envelope bytes; Binary studies encode records separately."""
    names=tuple(cfg['channels']);b=baseline(cfg,multiplier)
    gated=method in ('TAIS','GateOnly')
    fixed=float(method.split('-')[1]) if method.startswith('Fixed-') else None
    scheduler=Scheduler(cfg,confirmation=method=='TAIS',multiplier=multiplier) if gated else (None if fixed else AdaptiveScheduler(b))
    # Health logging never changes the raw baseline decisions.
    trust={n:SensorTrust(cfg['channels'][n]['trust']) for n in names} if method=='AdaptiveSense+TrustLog' else {}
    detectors={n:ChangeAnalyzer(analyzer_config(b)) for n in names}
    next_sample=0;records=[];detections=[];reported=[]
    opened={n:None for n in names};last_active={n:0 for n in names};sent={n:False for n in names}
    last_values={}
    for row in trace.observed:
        t=row['timestamp']
        if t<next_sample-1e-9:continue
        values={n:row[n] for n in names}
        if gated:
            d=scheduler.update(t,values);active=d.active
            interval=d.interval;upload=d.upload;health=d.health
            detail=asdict(d)
        else:
            # Upstream scorer lacks an invalid contract: invalid fields are omitted.
            # This common input sanitation is explicit, never interpolated/held online.
            usable={n:v for n,v in values.items() if finite(v)}
            if fixed:interval=fixed;upload=True;state='FIXED';scores={}
            else:
                d=scheduler.update(t,usable);interval=d.interval_s;upload=d.upload_requested;state=d.state;scores=d.channel_scores
            active={}
            for n in names:
                _,_,a=detectors[n].update(t,{n:values[n]} if finite(values[n]) else {})
                active[n]=a
            health={n:asdict(c.update(t,values[n])) for n,c in trust.items()}
            detail={'state':state,'scores':scores,'reasons':['baseline_policy'] if upload else [],'confirmation':False,'diagnostic':False,'recovery_reset':[]}
        # An active sampled detection is reported at its first requested upload.
        for n in names:
            if active[n]:
                last_active[n]=t
                if opened[n] is None:opened[n]=t;sent[n]=False
                if upload and not sent[n]:reported.append(Event(n,t,t));sent[n]=True
            elif opened[n] is not None:
                detections.append(Event(n,opened[n],last_active[n]));opened[n]=None
        envelope={'timestamp':t,'values':{n:v if finite(v) else None for n,v in values.items()},'environment_active':active,'health':health}
        size=len(json.dumps(envelope,sort_keys=True,separators=(',',':'),allow_nan=False).encode()) if upload else 0
        records.append({'timestamp':t,'values':values,'interval':interval,'upload':upload,'payload_bytes':size,'active':dict(active),'health':health,**detail})
        next_sample=t+interval
    for n in names:
        if opened[n] is not None:detections.append(Event(n,opened[n],last_active[n]))
    return {'records':records,'detections':detections,'reports':reported}
