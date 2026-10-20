"""Reuse frozen matcher/codec, independently score received decoded edges."""
import numpy as np
from benchmark_joint_optimization import metrics as base_metrics
from benchmark_su import receiver_result
from tais.metrics import evaluate
from simulator.events import match_events

def metrics(trace,result,cfg,cf,cf_frames):
    out,frames=base_metrics(trace,result,cfg,cf)
    rr,rx=receiver_result(result,frames);rcf,_=receiver_result(cf,cf_frames)
    ev=evaluate(trace,rr,cfg,rcf)
    for k in ['tp','false_reports','fault_induced_false','missed','latency_sum_s','latency_n']:out['rx_'+k]=ev[k]
    times=np.array([f['timestamp'] for f in frames]);grid=np.arange(len(trace.observed));ix=np.searchsorted(times,grid,side='right')-1
    assert np.all(ix>=0)
    age=grid-times[ix];hist=np.bincount(age.astype(int),minlength=len(grid))
    rows=result['records'];sent={x['envelope']['timestamp']:x['envelope'] for x in rx};edges=missed=0;delays=[];event_delays=[];health_delays=[]
    for i,r in enumerate(rows):
        if not i:continue
        for n in cfg['channels']:
            h=r['health'].get(n);old=rows[i-1]['health'].get(n)
            for field,changed in [('event',r['active'][n]!=rows[i-1]['active'][n]),('health',h is not None and (h['state'],h['flags'])!=(old['state'],old['flags']))]:
                if not changed:continue
                edges+=1;t=r['timestamp'];delay=None
                for tx,env in sent.items():
                    if tx<t:continue
                    same=env['environment_active'][n]==r['active'][n] if field=='event' else (env['health'][n]['state'],env['health'][n]['flags'])==(h['state'],h['flags'])
                    if same:delay=tx-t
                    break
                if delay is None:missed+=1
                else:
                    delays.append(delay);(event_delays if field=='event' else health_delays).append(delay)
    out.update(important_edges=edges,important_edges_unreported=missed,important_edge_delay_max_s=max(delays,default=0),event_edge_delay_max_s=max(event_delays,default=0),health_edge_delay_max_s=max(health_delays,default=0))
    by={p.ground_truth:p.detected for p in match_events(trace.events,result['reports'],5).matches}
    br={p.ground_truth:p.detected for p in match_events(trace.events,rr['reports'],5).matches}
    events=[dict(channel=e.channel,truth_start=e.start_s,truth_end=e.end_s,covered=any(e.start_s<=r['timestamp']<=e.end_s for r in rows),matched=e in by,rx_matched=e in br,report_time=by[e].start_s if e in by else None,rx_report_time=br[e].start_s if e in br else None) for e in trace.events]
    out.update(covered_tp=sum(e['covered'] and e['matched'] for e in events),covered_events=sum(e['covered'] for e in events),uncovered_matched=sum(not e['covered'] and e['matched'] for e in events))
    has_health=bool(rows[0]['health'])
    out['health_available']=has_health
    if not has_health:
        for k in ['fault_detected','fault_type_detected','fault_latency_mean_s','fault_latency_sum_s']:out[k]=None
    return out,frames,rx,events,hist
