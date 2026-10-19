#!/usr/bin/env python3
"""G2 micro outcomes and whole-seed paired bootstrap; never pool G1 and G2."""
import argparse,json,sys
from pathlib import Path
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from analyze_paper import aggregate
from benchmark_transfer import OUT,plan
from benchmark_paper import dump,sha
CONTRASTS=[('JO-SU-40',b) for b in ['GateOnly','AdaptiveSense+TrustLog','Delta-budget-SU40+C11','Variance-budget-SU40+C11','Rao-inspired-budget-SU40+C11']]+[('JO-SU-20','JO-SU-40'),('GateOnly+U','GateOnly')]

def write(p,rows):p.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(p,index=False)
def groups(r):
    return ['overall','scenario:'+r['scenario'],'fault:'+r['fault_kind'],'relation:'+r['relationship'],'fault_channel:'+r['fault_channel']]+(['no_events'] if not r['n_events'] else [])
def main(root,phase):
    base=root/phase;manifest=json.loads((base/'manifest.json').read_text());assert manifest['status']=='COMPLETE'
    for f,h in manifest['outputs'].items():assert sha(base/f)==h
    d=pd.read_csv(base/'metrics.csv');e=pd.read_csv(base/'events.csv');f=pd.read_csv(base/'faults.csv');rows=d.replace({np.nan:None}).to_dict('records');out=base/'analysis';out.mkdir(exist_ok=True);by={}
    for r in rows:
        for group in groups(r):by.setdefault((r['method'],group),[]).append(r)
    ages={r['method']:r for r in pd.read_csv(base/'pooled_age.csv').to_dict('records')};summary=[]
    for (m,g),rr in sorted(by.items()):
        a=aggregate(rr)
        for k in ['type_supported_faults','fault_type_latency_sum_s','false_reports_temperature','false_reports_humidity','no_fault_channel_false_temperature','no_fault_channel_false_humidity','event_edges','event_edges_unreported','health_edges','health_edges_unreported']:a[k]=sum(r[k] for r in rr)
        a['typed_detection_rate']=a['fault_type_detected']/a['type_supported_faults'] if a['type_supported_faults'] else None
        a['typed_delay_s']=a['fault_type_latency_sum_s']/a['fault_type_detected'] if a['fault_type_detected'] else None
        a['any_flag_delay_s']=a['fault_latency_sum_s']/a['fault_detected'] if a['fault_detected'] else None
        a['pooled_age_p95_s']=ages[m]['p95_age_s'] if g=='overall' else None;a['pooled_age_max_s']=ages[m]['max_age_s'] if g=='overall' else None
        summary.append(dict(method=m,group=g,**a))
    write(out/'summary.csv',summary);overall={r['method']:r for r in summary if r['group']=='overall'};write(root/'summary.csv',overall.values())
    # Individual exogenous events remain auditable, including finite and overwritten coverage.
    event_summary=[]
    def event_groups(r):
        groups=['overall','duration:'+r.duration_bin,'channel:'+r.channel,'relation:'+r.relationship,'timing:'+r.temporal_relation,'shape:'+r['shape'],'overlap:'+r.overlap_relation]
        if r.fully_overwritten:groups.append('fully_overwritten')
        if not r.covered:groups.append('no_sample_coverage')
        # Predeclared discrete duration ranges; no fitted curve/interpolation.
        for a,b in [(12,20),(21,40),(41,60),(61,100),(101,160),(161,240)]:
            if a<=r.physical_duration_s<=b:groups.append(f'actual_duration:{a}-{b}')
        return groups
    eb={}
    for _,r in e.iterrows():
        for g in event_groups(r):eb.setdefault((r.method,g),[]).append(r)
    for (m,g),rr in sorted(eb.items()):
        n=len(rr);tp=sum(r.matched for r in rr);rx=sum(r.rx_matched for r in rr);covered=sum(r.covered for r in rr);covered_hits=sum(r.covered and r.matched for r in rr);deltas=[r.report_time-r.truth_start for r in rr if r.matched];rxd=[r.rx_report_time-r.truth_start for r in rr if r.rx_matched]
        event_summary.append(dict(method=m,group=g,events=n,tp=tp,fn=n-tp,recall=tp/n,rx_tp=rx,rx_fn=n-rx,rx_recall=rx/n,covered=covered,coverage=covered/n,covered_tp=covered_hits,covered_success=covered_hits/covered if covered else None,finite_coverage=sum(r.finite_sample_coverage for r in rr)/n,mean_duration_s=np.mean([r.physical_duration_s for r in rr]),delay_s=np.mean(deltas) if deltas else None,rx_delay_s=np.mean(rxd) if rxd else None))
    write(out/'events_grouped.csv',event_summary)
    diag=[]
    for (m,k,c),rr in f.groupby(['method','kind','channel']):
        anyn=int(rr.any_detected.sum());typed=int(rr.type_detected.sum());supported=int(rr.type_supported.sum())
        diag.append(dict(method=m,kind=k,channel=c,episodes=len(rr),sampled_episodes=int((rr.samples_during>0).sum()),any_detected=anyn,any_detection_rate=anyn/len(rr),any_delay_s=rr.any_delay_s.mean(),type_supported_episodes=supported,type_detected=typed,type_detection_rate=typed/supported if supported else None,type_delay_s=rr.type_delay_s.mean()))
    write(out/'fault_diagnostics.csv',diag)
    budgets=[]
    for m in [m for m in overall if '-budget-SU40' in m]:
        a=overall[m];b=overall['JO-SU-40'];gap=a['samples']/b['samples']-1
        budgets.append(dict(method=m,target='JO-SU-40',samples=a['samples'],target_samples=b['samples'],relative_gap=gap,within_5pct=abs(gap)<=.05,f1=a['f1'],target_f1=b['f1'],recall=a['recall'],target_recall=b['recall']))
    write(out/'budget_comparisons.csv',budgets)
    seeds=sorted(d.seed.unique());rng=np.random.default_rng(plan()['bootstrap_seed']);draw=rng.integers(0,len(seeds),(plan()['bootstrap_draws'],len(seeds)));cis=[]
    for A,B in CONTRASTS:
        for group in ['overall','relation:same','relation:cross','fault:drift','fault:stable_offset','fault_channel:temperature','fault_channel:humidity','no_events']:
            aa=[r for r in rows if r['method']==A and group in groups(r)];bb=[r for r in rows if r['method']==B and group in groups(r)]
            if not aa or not bb:continue
            a,b=aggregate(aa),aggregate(bb);pa=[aggregate([r for r in aa if r['seed']==s]) for s in seeds];pb=[aggregate([r for r in bb if r['seed']==s]) for s in seeds]
            def boot(per,k):
                def summed(col):return np.array([r[col] or 0 for r in per])[draw].sum(axis=1)
                def div(x,y):return np.divide(x,y,out=np.full(len(draw),np.nan),where=y>0)
                prefix='rx_' if k.startswith('rx_') else '';kk=k[len(prefix):]
                if kk in ['precision','recall','f1']:
                    tp=summed(prefix+'tp');fp=summed(prefix+'false_reports');n=summed('n_events');return div(tp*(2 if kk=='f1' else 1),{'precision':tp+fp,'recall':n,'f1':n+tp+fp}[kk])
                if k=='coverage':return div(summed('covered_events'),summed('n_events'))
                if k=='covered_success':return div(summed('covered_tp'),summed('covered_events'))
                if k=='fault_detection_rate':return div(summed('fault_detected'),summed('fault_episodes'))
                if kk=='event_delay_s':return div(summed(prefix+'latency_sum_s'),summed(prefix+'latency_n'))
                return summed(k)
            for k in ['precision','recall','f1','rx_precision','rx_recall','rx_f1','samples','uploads','binary_v1_bytes','fault_induced_false','rx_fault_induced_false','coverage','covered_success','fault_detection_rate','event_delay_s','rx_event_delay_s']:
                if a[k] is None or b[k] is None:continue
                delta=boot(pa,k)-boot(pb,k);lo,hi=np.nanpercentile(delta,[2.5,97.5]);cis.append(dict(A=A,B=B,group=group,metric=k,difference=a[k]-b[k],ci95_low=lo,ci95_high=hi,seed_clusters=len(seeds),draws=len(draw)))
    write(out/'paired_intervals.csv',cis)
    # Conditional delays also restricted to common-hit identities.
    common=[]
    for A,B in CONTRASTS:
        ix=['seed','scenario','channel','truth_start','truth_end'];x=e[e.method==A].merge(e[e.method==B],on=ix,suffixes=('_a','_b'))
        for prefix in ['', 'rx_']:
            y=x[x[prefix+'matched_a']&x[prefix+'matched_b']]
            common.append(dict(A=A,B=B,view='receiver' if prefix else 'sender',matched_in_both=len(y),mean_delay_difference_s=(y[prefix+'report_time_a']-y[prefix+'report_time_b']).mean()))
    write(out/'common_event_delays.csv',common)
    old=pd.read_csv(ROOT/'results/tais-paper/test/analysis/summary.csv');old=old[(old['view']=='native')&(old.group=='overall')].set_index('method');direction=[]
    for A,B in CONTRASTS:
        for k in ['recall','f1','samples','binary_v1_bytes','fault_induced_false']:
            x=float(old.loc[A,k]-old.loc[B,k]);y=overall[A][k]-overall[B][k]
            direction.append(dict(A=A,B=B,metric=k,g1_difference=x,g2_difference=y,direction='consistent' if np.sign(x)==np.sign(y) else 'reversed' if x*y<0 else 'zero_in_one_generator',note='Counts are within-generator totals with different scenario/event composition; compare direction only, never pooled.'))
    write(out/'cross_generator_directions.csv',direction)
    dump(out/'manifest.json',dict(status='COMPLETE',input_manifest_sha256=sha(base/'manifest.json'),runs=len(d),seed_clusters=len(seeds),outputs={p.name:sha(p) for p in sorted(out.glob('*.csv'))}))
    print('Analyzed',len(d),'runs;',len(event_summary),'event groups;',len(cis),'paired intervals')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=OUT);p.add_argument('--phase',choices=['smoke','test'],default='test');a=p.parse_args();main(a.root,a.phase)
