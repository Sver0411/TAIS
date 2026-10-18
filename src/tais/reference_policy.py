"""IRB-1 causal hard-budget admission around unchanged main-channel schedulers."""
from dataclasses import asdict
import json
import math
from .config import baseline
from .scheduler import Scheduler
from .reference_signals import A,B,main_config
from simulator.events import Event


def json_bytes(envelope):return json.dumps(envelope,sort_keys=True,separators=(',',':'),allow_nan=False).encode()


class Budget:
    def __init__(self,caps):
        if set(caps)!=set(('reads','uploads','bytes')) or any(type(v)is not int or v<0 for v in caps.values()):raise ValueError('Invalid hard caps')
        self.caps=dict(caps);self.used=dict.fromkeys(caps,0);self.ledger=[]
    def read(self,t,sensor):
        accepted=self.used['reads']<self.caps['reads']
        if accepted:self.used['reads']+=1
        self.ledger.append(dict(time=t,operation='read',sensor=sensor,accepted=accepted,cost=1 if accepted else 0,used=dict(self.used)))
        return accepted
    def upload(self,t,envelope):
        cost=len(json_bytes(envelope))
        accepted=self.used['uploads']<self.caps['uploads'] and self.used['bytes']+cost<=self.caps['bytes']
        if accepted:self.used['uploads']+=1;self.used['bytes']+=cost
        reason=None if accepted else 'uploads' if self.used['uploads']>=self.caps['uploads'] else 'bytes'
        self.ledger.append(dict(time=t,operation='upload',accepted=accepted,cost=cost if accepted else 0,proposed_bytes=cost,reason=reason,used=dict(self.used)))
        return accepted,cost


def run(trace,cfg,method,caps):
    if method not in ('GateOnly','TAIS','ReferenceGate'):raise ValueError('Unknown policy')
    cfg=main_config(cfg);scheduler=Scheduler(cfg,confirmation=method=='TAIS',multiplier=1.)
    budget=Budget(caps);rules=baseline(cfg)['adaptive'];threshold=rules['event_threshold']*rules['channels'][A]['noise_floor'];delay=rules['event_min_duration_s']
    records=[];reports=[];supported=[];detections=[];envelopes=[];ref_reads=[];episodes=[]
    next_t=0;opened=None;last_active=None;sent=False;episode=None;baseline_a=None;baseline_b=None;job=None;pending_refs=[];pending_evidence=[]
    def get_b(row,roles):
        t=row['timestamp']
        if not budget.read(t,'B'):return None,'read_budget'
        value=row[B];item=dict(timestamp=t,value=value,roles=roles);ref_reads.append(item);pending_refs.append(item)
        return value,None if value is not None and math.isfinite(value) else 'missing'
    def consistent(da,db):return abs(da)>threshold and abs(db)>threshold and da*db>0
    def finish(item,t,status,reason):
        item.update(status=status,decision_time=t,reason=reason)
        pending_evidence.append(dict(candidate_id=item['id'],candidate_start=item['start_s'],decision_time=t,status=status,reason=reason))
    for row in trace.observed:
        t=row['timestamp']
        if t<next_t:continue
        if not budget.read(t,'A'):break
        value=row[A]
        d=scheduler.update(t,{A:value});active=d.active[A]
        if baseline_a is None:
            baseline_a=value
            if method=='ReferenceGate':baseline_b,_=get_b(row,['baseline'])
        if active:
            last_active=t
            if opened is None:
                opened=t;sent=False
                episode=dict(id=len(episodes),start_s=t,status='not_applicable' if method!='ReferenceGate' else 'undecided',decision_time=None,reason='no_reference' if method!='ReferenceGate' else 'pending')
                episodes.append(episode)
                if method=='ReferenceGate':
                    if job is not None:finish(episode,t,'undecided','busy')
                    elif baseline_b is None:finish(episode,t,'undecided','baseline_unavailable')
                    else:
                        b,error=get_b(row,['candidate'])
                        if error:finish(episode,t,'undecided',error)
                        else:job=dict(episode=episode,start=t,da=value-baseline_a,db=b-baseline_b)
        elif opened is not None:
            detections.append(Event(A,opened,last_active));opened=None
        if job is not None and t-job['start']>=delay:
            b,error=get_b(row,['followup'])
            status='supported' if not error and consistent(job['da'],job['db']) and consistent(value-baseline_a,b-baseline_b) else 'undecided'
            finish(job['episode'],t,status,error or ('consistent' if status=='supported' else 'channel_only_or_inconsistent'))
            job=None
        evidence_proposal=bool(pending_evidence)
        proposal=d.upload or evidence_proposal
        envelope=dict(timestamp=t,values={A:value},environment_active=dict(d.active),health=d.health)
        if method=='ReferenceGate':
            envelope['reference']=dict(measurements=list(pending_refs),evidence=list(pending_evidence))
        admitted=False;size=0
        if proposal:
            admitted,size=budget.upload(t,envelope)
            if admitted:
                envelopes.append(envelope)
                if active and not sent:
                    reports.append(Event(A,t,t));sent=True
                    episode['report_time']=t
                if method=='ReferenceGate':
                    for e in pending_evidence:
                        original=episodes[e['candidate_id']]
                        if 'report_time' not in original:
                            reports.append(Event(A,t,t));original['report_time']=t
                            if original is episode:sent=True
                        if e['status']=='supported':
                            supported.append(Event(A,t,t));original['support_report_time']=t
                    pending_refs=[];pending_evidence=[]
        records.append(dict(timestamp=t,values={A:value},interval=d.interval,upload=admitted,payload_bytes=size if admitted else 0,
                            active=dict(d.active),health=d.health,**{k:v for k,v in asdict(d).items() if k not in ('interval','upload','active','health')},
                            proposed_upload=bool(proposal)))
        next_t=t+d.interval
    if opened is not None:detections.append(Event(A,opened,last_active))
    if job is not None:finish(job['episode'],records[-1]['timestamp'],'undecided','run_or_read_budget_end')
    # A candidate is never removed when B is flat/missing. Support is a second label.
    return dict(method=method,records=records,reports=reports,detections=detections,supported_reports=supported,
                reference_reads=ref_reads,episodes=episodes,envelopes=envelopes,ledger=budget.ledger,used=budget.used,caps=budget.caps)
