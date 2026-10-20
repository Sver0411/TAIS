"""Replay legacy policies with passive event-level forensic exports."""
import sys, csv, json, gzip, hashlib, subprocess, platform
from pathlib import Path
from dataclasses import asdict
sys.path[:0] = [str(Path(__file__).resolve().parents[1]/'src'), str(Path(__file__).resolve().parent)]
from tais import ROOT
from tais.config import load
from tais.signals import generate, scenarios
from tais.replay import run, finite
from tais_v02.forensics import inspect_run
from simulator.events import match_events
from run_experiments import canonical, save
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

PROBES=['range_same_long','missing_same_long','stable_offset_none_long','stuck_none_long',
        'spike_same_short','drift_same_long','range_cross_short']

def export_event(trace, result, evidence, cfg, method):
    rows=[]; tol=cfg['evaluation']['event_match_tolerance_s']
    match=match_events(trace.events, result['reports'], tol)
    for i,e in enumerate(trace.events):
        window=[(r,a['channels'][e.channel]) for r,a in zip(result['records'],evidence)
                if e.start_s-tol<=r['timestamp']<=e.end_s+tol]
        detected=next((m.detected.start_s for m in match.matches if m.ground_truth==e),None)
        erased=any(f.channel==e.channel and f.start_s<=e.start_s and f.end_s>e.end_s
                   and f.kind in ('range','missing','invalid','stuck') for f in trace.faults)
        raw=[c for _,a in window for c in a['raw_calls']]
        active=any(r['active'][e.channel] for r,_ in window)
        if detected is not None: stage='reported_match'
        elif erased: stage='information_erased'
        elif not window: stage='no_sample_in_match_window'
        elif not any(finite(r['values'][e.channel]) for r,_ in window): stage='no_valid_sample'
        elif active: stage='report_or_episode_onset_outside_window'
        elif any(x['raw_active'] for x in raw): stage='health_or_confirmation_gate'
        elif any(x['raw_score']>baseline_threshold(cfg) for x in raw): stage='debounce_or_reset'
        else: stage='score_below_threshold_at_samples'
        rows.append(dict(seed=trace.seed,scenario=trace.scenario,method=method,event_id=i,
                         channel=e.channel,start_s=e.start_s,end_s=e.end_s,duration_s=e.duration_s,
                         amplitude=cfg['synthetic']['event_amplitude'][e.channel],
                         fault_kind=trace.faults[0].kind if trace.faults else 'clean',
                         fault_start=trace.faults[0].start_s if trace.faults else None,
                         fault_end=trace.faults[0].end_s if trace.faults else None,
                         intensity=cfg['synthetic']['profiles'][trace.profile]['intensity'],
                         sampled_times=json.dumps([r['timestamp'] for r,_ in window]),
                         health_states=json.dumps([r['health'].get(e.channel,a.get('offline_health')) for r,a in window]),
                         raw_scores=json.dumps([x['raw_score'] for x in raw]),
                         lifecycle=json.dumps([(r['timestamp'],a['lifecycle']) for r,a in window]),
                         uploaded_event_s=detected,loss_stage=stage,information_erased=erased))
    return rows

def baseline_threshold(cfg):
    from tais.config import baseline
    return baseline(cfg)['adaptive']['event_threshold']

def plot(trace, runs, path):
    fig, axes=plt.subplots(5,1,figsize=(12,12),sharex=True,constrained_layout=True)
    n='temperature';ts=[r['timestamp'] for r in trace.latent]
    axes[0].plot(ts,[r[n] for r in trace.latent],label='Latent (offline)',color='black')
    axes[0].plot(ts,[r[n] for r in trace.observed],label='Faulted (offline)',alpha=.5)
    axes[1].plot(ts,[r['humidity'] for r in trace.latent],label='Humidity latent (offline)',color='black')
    axes[1].plot(ts,[r['humidity'] for r in trace.observed],label='Humidity faulted (offline)',alpha=.5)
    for j,(method,(result,evidence)) in enumerate(runs.items()):
        records=result['records']; tt=[r['timestamp'] for r in records]; color=f'C{j+2}'
        axes[0].scatter(tt,[r['values'][n] for r in records],s=10,label=method+' samples',color=color)
        axes[1].scatter(tt,[r['values']['humidity'] for r in records],s=8,label=method+' samples',color=color)
        h=[r['health'].get(n,a['channels'][n].get('offline_health')) for r,a in zip(records,evidence)]
        axes[2].step(tt,[x['score'] for x in h],where='post',label=method+' C health',color=color)
        axes[2].scatter(tt,[{'HEALTHY':100,'DEGRADED':75,'FAULT':25}[x['state']] for x in h],s=5,color=color)
        axes[3].plot(tt,[max([x['raw_score'] for x in a['channels'][n]['raw_calls']],default=0) for a in evidence],label=method+' raw score',color=color)
        for r,a in zip(records,evidence):
            action=a['channels'][n]['lifecycle']
            if action in ('created','confirmed','cancelled'):axes[4].scatter(r['timestamp'],j+.3,marker={'created':'o','confirmed':'*','cancelled':'x'}[action],color=color,s=40)
        axes[4].scatter([r['timestamp'] for r in records if r['upload']],[j]*sum(r['upload'] for r in records),marker='|',color=color,label=method+' upload')
        axes[4].scatter([e.start_s for e in result['reports'] if e.channel==n],[j+.6]*sum(e.channel==n for e in result['reports']),marker='^',color=color)
    for ax in axes:
        for f in trace.faults:ax.axvspan(f.start_s,f.end_s,color='red',alpha=.08)
        for e in trace.events:ax.axvspan(e.start_s,e.end_s,color='green',alpha=.12)
        ax.grid(alpha=.2);ax.legend(fontsize=7,loc='upper right')
    axes[0].set_ylabel('Temperature C');axes[0].set_title(trace.scenario+' seed '+str(trace.seed)+'; green truth / red fault')
    axes[1].set_ylabel('Humidity %RH')
    axes[2].set_ylabel('C health score / state');axes[3].set_ylabel('Raw AS score')
    axes[4].set_ylabel('Lifecycle: o create, x cancel\n* confirm, ^ report, | upload');axes[4].set_xlabel('Seconds')
    axes[-1].set_xlim(500,1450)
    fig.savefig(path,dpi=150);plt.close(fig)

def main():
    cfg=load();dest=ROOT/'results/v0.2/forensics';dest.mkdir(parents=True,exist_ok=True)
    archive=ROOT/'results/traces/v02-forensics';rows=[];checks=[];artifacts={};probes=[]
    for seed in range(20,50):
        for case in scenarios():
            trace=generate(cfg,seed,case);runs={}
            for method in ['AdaptiveSense','GateOnly','TAIS']:
                result,evidence=inspect_run(trace,cfg,method)
                # Byte equality to original archive proves observer passivity and v0.1 replay.
                original=ROOT/f'results/traces/test/{seed}/{case}/{method}-1.json.gz'
                assert canonical(result)==gzip.decompress(original.read_bytes()),(seed,case,method)
                checks.append((seed,case,method))
                name=f'{seed}/{case}/{method}.json.gz'
                artifacts[name]=save(archive/name,dict(result=result,evidence=evidence))
                rows.extend(export_event(trace,result,evidence,cfg,method))
                if seed==20 and case in PROBES:
                    runs[method]=(result,evidence)
                    save(dest/(case+'-'+method+'.json.gz'),dict(trace=trace,result=result,evidence=evidence))
                    for r,a in zip(result['records'],evidence):
                        if 500<=r['timestamp']<=1450:
                            probes.append(dict(seed=seed,scenario=case,method=method,t=r['timestamp'],
                                value=r['values']['temperature'],health=json.dumps(r['health'].get('temperature',a['channels']['temperature'].get('offline_health'))),
                                score=json.dumps(a['channels']['temperature']['raw_calls']),
                                lifecycle=a['channels']['temperature']['lifecycle'],interval=r['interval'],
                                active=r['active']['temperature'],upload=r['upload'],reasons=json.dumps(r['reasons'])))
            if runs:plot(trace,runs,dest/(case+'.png'))
        print('forensics seed',seed,'passive replays',len(checks),flush=True)
    for name,data in [('events.csv',rows),('probe_samples.csv',probes)]:
        with (dest/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    (dest/'manifest.json').write_text(json.dumps(dict(source_commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        python=sys.version,platform=platform.platform(),command=sys.argv,seeds=list(range(20,50)),
        passive_byte_equal_replays=len(checks),event_rows=len(rows),artifacts=artifacts),indent=2)+'\n')
if __name__=='__main__': main()
