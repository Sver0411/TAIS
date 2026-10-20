"""G2 offline supplements; frozen sender/receiver event scoring is unchanged."""
from paper_metrics import metrics as frozen_metrics
from tais.replay import finite
from simulator.events import match_events
BITS={'range':1,'stuck':2,'spike':4,'drift':8,'missing':16,'invalid':16,'stable_offset':0}
OVERWRITES={'range','stuck','missing','invalid'}

def diagnostics(trace,result):
    rows=result['records'];out=[]
    for i,f in enumerate(trace.faults):
        sampled=[r for r in rows if f.start_s<=r['timestamp']<f.end_s]
        def raw(r):return r.get('joint',{}).get(f.channel,{}).get('raw_c11',r['health'].get(f.channel,{}))
        any_t=next((r['timestamp'] for r in sampled if raw(r).get('flags',0)),None)
        type_t=next((r['timestamp'] for r in sampled if raw(r).get('flags',0)&BITS[f.kind]),None)
        out.append(dict(fault_id=i,channel=f.channel,kind=f.kind,start_s=f.start_s,end_exclusive_s=f.end_s,samples_during=len(sampled),any_detected=any_t is not None,type_supported=BITS[f.kind]!=0,type_detected=type_t is not None,any_delay_s=None if any_t is None else any_t-f.start_s,type_delay_s=None if type_t is None else type_t-f.start_s))
    return out

def event_details(trace,result,events):
    by={(e['channel'],e['start_s']):e for e in trace.metadata['event_schedule']}
    for row in events:
        s=by[row['channel'],row['truth_start']];fs=trace.faults;a=s['start_s'];b=s['end_exclusive_s'];c=s['channel']
        overlap=[f for f in fs if f.start_s<b and f.end_s>a]
        mask={t for f in fs if f.channel==c and f.kind in OVERWRITES for t in range(max(a,int(f.start_s)),min(b,int(f.end_s)))}
        same=[f for f in overlap if f.channel==c];cross=[f for f in overlap if f.channel!=c]
        if not fs:timing='no_fault'
        elif overlap:timing='overlap'
        elif b<=min(f.start_s for f in fs):timing='event_before_fault'
        elif a>=max(f.end_s for f in fs):timing='fault_before_event'
        else:timing='nonoverlap_between_episodes'
        row.update(s,relationship=trace.relationship,temporal_relation=timing,overlap_relation='same' if same else 'cross' if cross else 'none',overwritten_fraction=len(mask)/(b-a),fully_overwritten=len(mask)==b-a,finite_sample_coverage=any(a<=r['timestamp']<b and finite(r['values'][c]) for r in result['records']))
    return events

def metrics(trace,result,cfg,cf,cf_frames):
    out,frames,rx,events,hist=frozen_metrics(trace,result,cfg,cf,cf_frames)
    events=event_details(trace,result,events);faults=diagnostics(trace,result)
    assert out['fault_detected']==sum(f['any_detected'] for f in faults)
    assert out['fault_type_detected']==sum(f['type_detected'] for f in faults)
    out.update(type_supported_faults=sum(f['type_supported'] for f in faults),fault_type_latency_sum_s=sum(f['type_delay_s'] for f in faults if f['type_delay_s'] is not None))
    matches=match_events(trace.events,result['reports'],cfg['evaluation']['event_match_tolerance_s'])
    for channel in cfg['channels']:
        out['false_reports_'+channel]=sum(e.channel==channel for e in matches.unmatched_detections)
        out['no_fault_channel_false_'+channel]=sum(e.channel==channel for e in matches.unmatched_detections) if not any(f.channel==channel for f in trace.faults) else 0
    # First subsequent received snapshot must preserve each sampled edge. Split
    # misses by event and health, including clearing edges, not only rises.
    for field in ('event','health'):
        total=missed=0
        for old,new in zip(result['records'],result['records'][1:]):
            for c in cfg['channels']:
                def sig(r):
                    return r['active'][c] if field=='event' else (r['health'][c]['state'],r['health'][c]['flags'])
                if sig(old)==sig(new):continue
                total+=1;received=next((r['envelope'] for r in rx if r['timestamp']>=new['timestamp']),None)
                target=received['environment_active'][c] if received and field=='event' else (received['health'][c]['state'],received['health'][c]['flags']) if received else None
                missed+=target!=sig(new)
        out[field+'_edges']=total;out[field+'_edges_unreported']=missed
    assert out['important_edges_unreported']==out['event_edges_unreported']+out['health_edges_unreported']
    return out,frames,rx,events,faults,hist
