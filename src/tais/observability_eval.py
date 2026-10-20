"""Offline FO-1 diagnostics: detection, flags and physical attribution kept distinct."""
from .budget_eval import aggregate as original_aggregate
from simulator.events import match_events

EXTRA_COUNTS = ('fault_flagged_event_missed','event_detected_no_fault_flag',
                'event_detected_wrong_fault_type','event_and_fault_detected',
                'sampled_fault_points','sampled_event_points','sampled_overlap_points',
                'report_interval_sum_s','report_interval_n',
                'counterfactual_samples','counterfactual_uploads','counterfactual_payload_bytes',
                'fault_incremental_samples','fault_incremental_uploads','fault_incremental_payload_bytes')


def extra_metrics(trace, result, cfg, metrics, counterfactual=None):
    """Add offline health/event joint outcomes and clean-world cost differences.

    Any health flag and a correct fault-type bit are separate outcomes; neither
    is an environmental detection. Event support is inclusive, fault support
    half-open. Missing counterfactual counts default to zero in this helper."""
    rows = result['records']
    in_event = lambda t: any(e.start_s <= t <= e.end_s for e in trace.events)
    in_fault = lambda t: any(f.start_s <= t < f.end_s for f in trace.faults)
    event_present = bool(trace.events)
    fault_present = bool(trace.faults)
    found = bool(metrics['tp'])
    flagged = bool(metrics['fault_detected'])
    wrong = flagged and not metrics['fault_type_detected']
    # Interval immediately preceding each environmental upload onset, not next interval.
    previous = {r['timestamp']: rows[i-1]['interval'] if i else None for i,r in enumerate(rows)}
    report_intervals = [previous[r.start_s] for r in result['reports'] if previous[r.start_s] is not None]
    cf=counterfactual or {}
    cf_counts={k:cf[k] if k in cf else (len(cf.get('records',[])) if k=='samples' else sum(r['upload'] for r in cf.get('records',[])) if k=='uploads' else sum(r['payload_bytes'] for r in cf.get('records',[]))) for k in ('samples','uploads','payload_bytes')}
    costs={**{'counterfactual_'+k:v for k,v in cf_counts.items()}, **{'fault_incremental_'+k:metrics[k]-v for k,v in cf_counts.items()}}
    return dict(**costs, fault_flagged_event_missed=int(event_present and flagged and not found),
                event_detected_no_fault_flag=int(fault_present and found and not flagged),
                event_detected_wrong_fault_type=int(fault_present and found and wrong),
                event_and_fault_detected=int(found and flagged),
                sampled_fault_points=sum(in_fault(r['timestamp']) for r in rows),
                sampled_event_points=sum(in_event(r['timestamp']) for r in rows),
                sampled_overlap_points=sum(in_event(r['timestamp']) and in_fault(r['timestamp']) for r in rows),
                report_interval_sum_s=sum(report_intervals), report_interval_n=len(report_intervals))


def aggregate(rows):
    result = original_aggregate(rows)
    result.pop('binary_v1_bytes', None)
    result.update({k:sum(float(r.get(k) or 0) for r in rows) for k in EXTRA_COUNTS})
    result['report_preceding_interval_mean_s'] = (result['report_interval_sum_s']/result['report_interval_n'] if result['report_interval_n'] else None)
    return result


def groups(row):
    names = ['overall', 'cohort:'+row['cohort'], 'kind:'+row['fault_kind'],
             'profile:'+row['profile'], 'scenario:'+row['scenario'],
             'temporal:'+row['temporal'], 'order:'+row['event_start_order'],
             'events:present' if row['n_events'] else 'events:absent']
    if row['fault_kind']!='clean':
        names.append('relationship:'+row['relationship'])
    if row['fault_kind'] in ('spike','drift') and row['n_events']:
        kind=row['fault_kind'];offset=int(row['offset_s'])
        names += [f'{kind}:dt:{offset}', f'{kind}:{row["relationship"]}',
                  f'{kind}:temporal:{row["temporal"]}',
                  f'{kind}:{row["relationship"]}:{row["profile"]}:dt:{offset}']
    return names


def event_rows(trace, result, cfg):
    """Return per-truth-event sender matching and sampled opportunity diagnostics.

    Delays are conditional on matched reports and never fill missed events."""
    match = match_events(trace.events, result['reports'], cfg['evaluation']['event_match_tolerance_s'])
    by_truth = {m.ground_truth:m.detected for m in match.matches}
    rows=result['records'];output=[]
    for e in trace.events:
        d=by_truth.get(e)
        points=[r for r in rows if e.start_s<=r['timestamp']<=e.end_s]
        fault=trace.faults[0] if trace.faults else None
        flagged=[r for r in rows if fault and fault.start_s<=r['timestamp']<fault.end_s and r['health'].get(fault.channel,{}).get('flags',0)]
        output.append(dict(channel=e.channel,truth_start=e.start_s,truth_end=e.end_s,
                           matched=d is not None, report_time=d.start_s if d else None,
                           latency_s=max(0,d.start_s-e.start_s) if d else None,
                           sampled_event_points=len(points),first_sample_in_event=points[0]['timestamp'] if points else None,
                           first_fault_flag=flagged[0]['timestamp'] if flagged else None))
    return output
