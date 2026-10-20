"""Shared one-to-one upstream matcher and explicit application-cost metrics."""
import math
import numpy as np
from simulator.events import match_events
from .replay import finite

def evaluate(trace,result,cfg,counterfactual=None):
    ev=cfg['evaluation'];tol=ev['event_match_tolerance_s']
    match=match_events(trace.events,result['reports'],tol)
    local=match_events(trace.events,result['detections'],tol)
    rows=result['records'];duration=len(trace.observed)
    fault_associated=[]
    for d in match.unmatched_detections:
        if any(f.channel==d.channel and f.start_s<=d.start_s<f.end_s+ev['fault_recovery_attribution_s'] for f in trace.faults):fault_associated.append(d)
    cf=counterfactual['reports'] if counterfactual is not None else []
    induced=[d for d in fault_associated if not any(c.channel==d.channel and abs(c.start_s-d.start_s)<=tol for c in cf)]
    detected=[];latencies=[];typed=[]
    bits={'range':1,'stuck':2,'spike':4,'drift':8,'missing':16,'invalid':16,'stable_offset':0}
    for f in trace.faults:
        observed=[r for r in rows if f.start_s<=r['timestamp']<f.end_s and r['health'].get(f.channel,{}).get('flags',0)]
        detected.append(bool(observed))
        typed.append(any(r['health'][f.channel]['flags']&bits[f.kind] for r in observed))
        if observed:latencies.append(observed[0]['timestamp']-f.start_s)
    out={'n_events':len(trace.events),'tp':match.true_positives,'missed':match.false_negatives,'recall':match.true_positives/len(trace.events) if trace.events else None,
         'local_tp':local.true_positives,'false_reports':match.false_positives,'redundant_reports':len(match.redundant_detections),
         'fault_associated_false':len(fault_associated),'fault_induced_false':len(induced),'false_per_hour':match.false_positives*3600/duration,
         'latency_mean_s':float(np.mean(match.latencies)) if match.latencies else None,'latency_sum_s':sum(match.latencies),'latency_n':len(match.latencies),
         'samples':len(rows),'uploads':sum(r['upload'] for r in rows),'payload_bytes':sum(r['payload_bytes'] for r in rows),
         'fault_episodes':len(trace.faults),'fault_detected':sum(detected),'fault_type_detected':sum(typed),
         'fault_latency_mean_s':float(np.mean(latencies)) if latencies else None,'fault_latency_sum_s':sum(latencies),
         'confirmation_samples':sum(r['confirmation'] for r in rows),'diagnostic_samples':sum(r['diagnostic'] for r in rows),
         'diagnostic_only_samples':sum(r['diagnostic'] and not r['confirmation'] and not any(r['active'].values()) for r in rows),
         'duration_s':duration}
    for name in cfg['channels']:
        for source in ['sample','upload']:
            used=[r for r in rows if finite(r['values'][name]) and (source=='sample' or r['upload'])]
            if not used:
                out[f'{source}_mae_{name}']=None;out[f'{source}_rmse_{name}']=None;out[f'{source}_coverage_{name}']=0
                continue
            times=np.array([r['timestamp'] for r in used]);v=np.array([r['values'][name] for r in used])
            index=np.searchsorted(times,np.arange(duration),side='right')-1;mask=index>=0
            target=np.array([r[name] for r in trace.latent])
            error=v[np.maximum(0,index)][mask]-target[mask]
            out[f'{source}_mae_{name}']=float(np.mean(abs(error)));out[f'{source}_rmse_{name}']=float(np.sqrt(np.mean(error**2)))
            out[f'{source}_coverage_{name}']=float(np.mean(mask))
    return out
