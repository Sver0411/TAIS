"""Offline acquisition/burst diagnostics; no truth is available to samplers."""
import numpy as np


def sampling_metrics(result,events,duration,pre_window=20,fast_interval=5,window=120):
    rows=result['records'];times=np.array([r['timestamp'] for r in rows])
    gaps=np.diff(times);fast=np.r_[False,gaps<=fast_interval+1e-9]
    fast_times=times[fast]
    used=np.searchsorted(fast_times,times,side='right')-np.searchsorted(fast_times,times-window,side='right')
    in_event=np.array([any(e.start_s<=t<=e.end_s for e in events) for t in times])
    bursts=[];start=None;last=None
    for i,is_fast in enumerate(fast):
        if is_fast:
            if start is None:start=times[i-1]
            last=times[i]
        elif start is not None:
            bursts.append((start,last));start=None
    if start is not None:bursts.append((start,last))
    unproductive=sum(not any(e.start_s<=b and e.end_s>=a for e in events) for a,b in bursts)
    local_onsets=[r['timestamp'] for i,r in enumerate(rows) if i and any(
        r['active'][n] and not rows[i-1]['active'][n] for n in r['active'])]
    no_local=sum(not any(a<=t<=b+10 for t in local_onsets) for a,b in bursts)
    event_rows=[]
    for e in events:
        previous=times[times<e.start_s];after=times[times>=e.start_s]
        event_rows.append(dict(channel=e.channel,truth_start=e.start_s,
                               pre_coverage=bool(len(previous) and e.start_s-previous[-1]<=pre_window),
                               last_sample_before_s=float(previous[-1]) if len(previous) else None,
                               first_sample_after_s=float(after[0]) if len(after) else None,
                               first_observation_delay_s=float(after[0]-e.start_s) if len(after) else None))
    out=dict(fast_samples=int(fast.sum()),fast_share=float(fast.sum()/max(1,len(rows)-1)),
             fast_samples_outside_events=int((fast & ~in_event).sum()),fast_window_max=int(used.max()),
             fast_bursts=len(bursts),fast_bursts_without_truth=unproductive,
             fast_bursts_without_local_onset=no_local,
             fast_budget_blocks=sum(r.get('adaptive',{}).get('fast_blocked',False) for r in rows),
             interval_switches=int(np.count_nonzero(np.diff([r['interval'] for r in rows]))),
             pre_covered_events=sum(e['pre_coverage'] for e in event_rows),
             first_observation_delay_sum_s=sum(e['first_observation_delay_s'] for e in event_rows if e['first_observation_delay_s'] is not None),
             first_observation_delay_n=sum(e['first_observation_delay_s'] is not None for e in event_rows))
    # Histogram is separate, rather than a variable-column metrics schema.
    hist=[dict(interval_s=float(v),count=int(np.count_nonzero(gaps==v))) for v in sorted(set(gaps))]
    return out,event_rows,hist,used.tolist()
