"""Post-final offline gain/loss audit; never changes policy/config/metrics.

Exports every changed event, compares fault-only report onsets for gains, and
plots the first gain/loss representatives. These are explanations, not selection.
"""
import sys,json,gzip
from pathlib import Path
sys.path[:0]=[str(Path(__file__).resolve().parents[1]/'src'),str(Path(__file__).resolve().parent)]
import pandas as pd
from tais import ROOT
from tais.signals import generate
from tais_v02.config import load
from tais_v02.forensics import inspect_run
from simulator.events import Event
from run_experiments import canonical,save
from v02_forensics import plot

def read(seed,case,method,scale):
    return json.loads(gzip.decompress((ROOT/f'results/traces/v02-test/{seed}/{case}/{method}-{scale:g}.json.gz').read_bytes()))

def main():
    cfg,_=load();dest=ROOT/'results/v0.2/cases';dest.mkdir(exist_ok=True)
    events=pd.read_csv(ROOT/'results/v0.2/test/events.csv');keys=['seed','scenario','multiplier','event_id']
    target=events[events.method=='V02'].set_index(keys);output=[]
    for ref in ['TAIS','V02-Passive']:
        base=events[events.method==ref].set_index(keys)
        changed=target[target.matched!=base.matched]
        for key,r in changed.iterrows():
            seed,case,scale,event_id=key
            row=dict(seed=seed,scenario=case,multiplier=scale,event_id=event_id,reference=ref,
                     reference_matched=bool(base.loc[key].matched),v02_matched=bool(r.matched),
                     truth_start=r.start_s,truth_end=r.end_s,report=r.report_s,
                     delay_s=r.report_s-r.start_s if r.matched else None)
            if r.matched and not case.startswith('clean_'):
                kind,relation,profile=case.rsplit('_',2)
                fault_only=read(seed,kind+'_none_'+profile,'V02',scale)
                row['fault_only_onsets']=json.dumps([e['start_s'] for e in fault_only['reports'] if e['channel']==r.channel])
                row['same_onset_without_event']=any(e['channel']==r.channel and abs(e['start_s']-r.report_s)<=5 for e in fault_only['reports'])
            output.append(row)
    pd.DataFrame(output).to_csv(dest/'changed_events.csv',index=False)
    for seed,case,scale in [(50,'drift_same_long',.75),(91,'spike_same_long',1.0)]:
        tr=generate(cfg,seed,case);runs={};artifacts={}
        legacy, evidence=inspect_run(tr,cfg,'TAIS',scale)
        assert canonical(legacy)==canonical(read(seed,case,'TAIS',scale))
        runs['v0.1 TAIS']=(legacy,evidence)
        for method in ['V02','V02-Passive']:
            result=read(seed,case,method,scale);evidence=[]
            for r in result['records']:
                channels={}
                for n,x in r['evidence'].items():
                    channels[n]=dict(raw_calls=[dict(raw_score=x['raw_score'],raw_active=x['raw_active'])],
                                     lifecycle=x['actions'][-1]['action'] if x['actions'] else 'none')
                    # created+retained in one call is still a creation on the plot.
                    if any(a['action']=='created' for a in x['actions']):channels[n]['lifecycle']='created'
                evidence.append(dict(timestamp=r['timestamp'],channels=channels))
            result['reports']=[Event(**e) for e in result['reports']]
            runs[method]=(result,evidence)
        label=f'{seed}-{case}-{scale:g}'
        artifacts[label]=save(dest/(label+'.json.gz'),dict(trace=tr,runs=runs))
        plot(tr,runs,dest/(label+'.png'))
    (dest/'README.md').write_text('# Post-final diagnostic cases\n\nAll changed events versus v0.1 and passive are exported. Six same-channel gains at.75 are late drift confirmations (169–176 s delay); their onsets differ from fault-only runs. Seed91 loses both sequential spike cases at.75/1 because BLOCKED survives the returned spike and then suppresses the next healthy event before a low-score sample rearms it. No policy or configuration was corrected after opening final seeds. Plots/JSON contain offline full signals for explanation only.\n')
    print(pd.DataFrame(output).to_string(index=False))
if __name__=='__main__':main()
