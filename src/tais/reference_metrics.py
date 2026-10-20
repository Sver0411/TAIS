"""Offline IRB-1 detection, partial attribution and exact resource accounting."""
from .metrics import evaluate
from .reference_signals import A,main_config
from simulator.events import match_events

EXTRA=('main_reads','reference_reads','local_episodes','received_candidates','received_supported_candidates',
 'unresolved_local','unresolved_received','support_tp','support_missed','support_false','support_induced_false','support_reports',
 'environment_tp','environment_false','environment_induced_false','environment_reports','support_latency_sum_s','support_latency_n','local_support_tp','fault_claim_tp','fault_claim_fp','fault_claim_fn','fault_claim_tn',
 'received_fault_claim_tp','received_fault_claim_fp','received_fault_claim_fn','received_fault_claim_tn',
 'scenario_support','scenario_candidate','scenario_support_wrong','read_denials','upload_denials','proposed_uploads',
 'events_after_denial','tp_after_denial','events_before_denial','tp_before_denial','reference_in_truth_reads')


def evaluate_reference(trace,result,cfg,counterfactual):
    """Score candidate and reference-supported reports separately under synthetic truth.

    ReferenceGate environmental metrics use support; comparators use candidates.
    Any health flag is a run-level fault claim for confusion counts, not a
    verified fault mechanism. Check ledger equality including both A and B reads.
    The received terminology assumes ideal admitted-envelope delivery here."""
    cfg=main_config(cfg);m=evaluate(trace,result,cfg,counterfactual);tol=cfg['evaluation']['event_match_tolerance_s']
    match=match_events(trace.events,result['reports'],tol)
    sr=result['supported_reports'];support=match_events(trace.events,sr,tol)
    cf=counterfactual.get('supported_reports',[])
    induced=[d for d in support.unmatched_detections if any(f.channel==d.channel and f.start_s<=d.start_s<f.end_s+cfg['evaluation']['fault_recovery_attribution_s'] for f in trace.faults) and not any(c.channel==d.channel and abs(c.start_s-d.start_s)<=tol for c in cf)]
    from simulator.events import Event
    local_support=match_events(trace.events,[Event(A,e['decision_time'],e['decision_time']) for e in result['episodes'] if e['status']=='supported'],tol)
    truth=bool(trace.faults);claim=any(r['health'][A]['flags'] for r in result['records']);received=any(r['upload'] and r['health'][A]['flags'] for r in result['records'])
    def confusion(pred,prefix):return {prefix+'tp':int(pred and truth),prefix+'fp':int(pred and not truth),prefix+'fn':int(not pred and truth),prefix+'tn':int(not pred and not truth)}
    denies=[x for x in result['ledger'] if not x['accepted']];first=min((x['time'] for x in denies),default=None)
    m.update(main_reads=len(result['records']),reference_reads=len(result['reference_reads']),local_episodes=len(result['episodes']),
      received_candidates=sum('report_time' in e for e in result['episodes']),received_supported_candidates=sum('support_report_time' in e for e in result['episodes']),
      unresolved_local=sum(e['status']=='undecided' for e in result['episodes']),unresolved_received=sum(e['status']!='not_applicable' and 'report_time' in e and 'support_report_time' not in e for e in result['episodes']),
      support_tp=support.true_positives,support_missed=support.false_negatives,support_false=support.false_positives,support_induced_false=len(induced),support_reports=len(sr),
      support_latency_sum_s=sum(support.latencies),support_latency_n=len(support.latencies),local_support_tp=local_support.true_positives,
      scenario_support=int(bool(sr)),scenario_candidate=int(bool(result['reports'])),scenario_support_wrong=int(bool(support.false_positives)),
      read_denials=sum(x['operation']=='read' for x in denies),upload_denials=sum(x['operation']=='upload' for x in denies),proposed_uploads=sum(x['operation']=='upload' for x in result['ledger']),
      events_after_denial=sum(first is not None and e.start_s>=first for e in trace.events),tp_after_denial=sum(first is not None and x.ground_truth.start_s>=first for x in match.matches),
      events_before_denial=sum(first is None or e.start_s<first for e in trace.events),tp_before_denial=sum(first is None or x.ground_truth.start_s<first for x in match.matches),
      reference_in_truth_reads=sum(any(e.start_s<=r['timestamp']<=e.end_s for e in trace.events) for r in result['reference_reads']),
      **confusion(claim,'fault_claim_'),**confusion(received,'received_fault_claim_'))
    m['environment_tp']=m['support_tp'] if result['method']=='ReferenceGate' else m['tp']
    m['environment_false']=m['support_false'] if result['method']=='ReferenceGate' else m['false_reports']
    m['environment_induced_false']=m['support_induced_false'] if result['method']=='ReferenceGate' else m['fault_induced_false']
    m['environment_reports']=m['support_reports'] if result['method']=='ReferenceGate' else len(result['reports'])
    m['samples']=result['used']['reads']
    if m['samples']!=m['main_reads']+m['reference_reads'] or m['uploads']!=result['used']['uploads'] or m['payload_bytes']!=result['used']['bytes']:raise AssertionError('Resource accounting mismatch')
    return m


def aggregate(rows):
    """Aggregate support, unresolved coverage, fault claims and resource counts.

    Use None for undefined ratios and unsupported comparator-only capabilities;
    absence of support must not silently become a successful negative diagnosis."""
    from .budget_eval import aggregate as base
    m=base(rows);m.pop('binary_v1_bytes',None)
    m.update({k:sum(float(r.get(k) or 0) for r in rows) for k in EXTRA})
    m['runs']=len(rows)
    def ratio(a,b):return a/b if b else None
    m.update(supported_recall=ratio(m['support_tp'],m['n_events']),local_candidate_recall=ratio(m['local_tp'],m['n_events']),
        supported_false_rate=ratio(m['support_false'],m['support_reports']),decisive_candidate_coverage=ratio(m['received_supported_candidates'],m['received_candidates']),
        unresolved_received_rate=ratio(m['unresolved_received'],m['received_candidates']),unresolved_local_rate=ratio(m['unresolved_local'],m['local_episodes']),
        decisive_scenario_coverage=ratio(m['scenario_support'],len(rows)),decisive_candidate_scenario_coverage=ratio(m['scenario_support'],m['scenario_candidate']),
        fault_claim_precision=ratio(m['fault_claim_tp'],m['fault_claim_tp']+m['fault_claim_fp']),fault_claim_recall=ratio(m['fault_claim_tp'],m['fault_claim_tp']+m['fault_claim_fn']),
        received_fault_claim_precision=ratio(m['received_fault_claim_tp'],m['received_fault_claim_tp']+m['received_fault_claim_fp']),received_fault_claim_recall=ratio(m['received_fault_claim_tp'],m['received_fault_claim_tp']+m['received_fault_claim_fn']),
        reference_read_fraction=ratio(m['reference_reads'],m['samples']),post_denial_recall=ratio(m['tp_after_denial'],m['events_after_denial']),pre_denial_recall=ratio(m['tp_before_denial'],m['events_before_denial']))
    m['environment_recall']=ratio(m['environment_tp'],m['n_events'])
    if rows and rows[0].get('method')!='ReferenceGate':
        for key in ('supported_recall','supported_false_rate','decisive_candidate_coverage','unresolved_received_rate','unresolved_local_rate','decisive_scenario_coverage','decisive_candidate_scenario_coverage'):m[key]=None
    return m


def groups(r):
    result=['overall','cohort:'+r['cohort'],'temporal:'+r['temporal'],'scenario:'+r['scenario'],
        'events:present' if r['n_events'] else 'events:absent','drift:present' if r['fault_episodes'] else 'drift:absent']
    if r['duration_scenario'] is not None:result.append('duration:'+str(int(r['duration_scenario'])))
    if r['shape']:result.append('shape:'+r['shape'])
    if r['alpha'] is not None:result.append('alpha:'+str(float(r['alpha'])))
    core=r['cohort'] in ('mixed','event_only','drift_only','clean')
    if core:
        result.append('core')
        if r['n_events'] and r['alpha'] in (.5,1.):
            result+=['responsive','alpha1' if r['alpha']==1 else 'alpha0.5']
    else:result.append('stress')
    return result
