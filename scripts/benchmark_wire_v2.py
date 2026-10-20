#!/usr/bin/env python3
"""Frozen archive-only v1/v2 cost and controlled-link audit; never run a policy."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import argparse
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import subprocess
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit_wire_health import BASE, inputs, read_archive
from benchmark_wire_codec import ROOT, check, sha, canonical, audit_result, stats as frame_stats, write_csv
from tais.wire_codec import encode as encode_v1, decode as decode_v1, envelope_from_record
from tais.wire_link import PERIODS,PROFILES,LINK_SEED,EVENT_COLUMNS,encode_stream,simulate,exact
from tais.config import load


class GzipCSV:
    def __init__(self,path):
        import io
        self.file=path.open('xb');self.gz=gzip.GzipFile(filename='',mode='wb',fileobj=self.file,mtime=0,compresslevel=3)
        self.text=io.TextIOWrapper(self.gz,encoding='utf-8',newline='');self.writer=None
    def write(self,row):
        if self.writer is None:
            self.writer=csv.DictWriter(self.text,fieldnames=list(row));self.writer.writeheader()
        self.writer.writerow(row)
    def close(self):self.text.close();self.file.close()


def percentile(hist, fraction):
    count=sum(hist.values())
    if not count:return None
    cumulative=0
    for value,n in sorted(hist.items()):
        cumulative+=n
        if cumulative>=math.ceil(fraction*count):return value


def plot(rows,path):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    methods=('AdaptiveSense','AdaptiveSense+TrustLog','GateOnly','TAIS')
    fig,axes=plt.subplots(1,2,figsize=(12,5.5))
    primary={r['method']:r for r in rows if r['multiplier']==1 and r['period']==16 and r['profile']=='loss0'}
    for j,(column,label,color) in enumerate([('v1_bytes','v1','#627b95'),('v2_bytes','v2 K16','#187d79')]):
        bars=axes[0].bar([i+(j-.5)*.36 for i in range(4)],[primary[m][column]/1e6 for m in methods],.34,label=label,color=color)
        axes[0].bar_label(bars,fmt='%.3f',padding=4,fontsize=8)
    axes[0].set_xticks(range(4),['AS','AS+TrustLog','GateOnly','TAIS'])
    axes[0].set_ylabel('Sent application bytes (decimal MB)');axes[0].set_title('Native1.0, no loss: all metadata included')
    axes[0].legend(frameon=False)
    for period,color in [(8,'#a87824'),(16,'#187d79'),(32,'#7465a3')]:
        rs=[next(r for r in rows if r['method']=='TAIS' and r['multiplier']==1 and r['period']==period and r['profile']==p) for p in ('loss1','loss5','loss10')]
        axes[1].plot([1,5,10],[100*r['permanently_missing_v2']/r['sent'] for r in rs],marker='o',label=f'v2 K{period}',color=color)
    rs=[next(r for r in rows if r['method']=='TAIS' and r['multiplier']==1 and r['period']==16 and r['profile']==p) for p in ('loss1','loss5','loss10')]
    axes[1].plot([1,5,10],[100*r['dropped']/r['sent'] for r in rs],linestyle='--',color='#627b95',label='v1: physical drops only')
    axes[1].set_xlabel('Assumed independent loss probability (%)');axes[1].set_ylabel('Permanently missing business records (%)')
    axes[1].set_title('TAIS native1.0: received dependency losses included');axes[1].legend(frameon=False,fontsize=9)
    for ax in axes:ax.spines[['top','right']].set_visible(False)
    fig.suptitle('Historical serialization/link engineering review; no radio measurements')
    fig.tight_layout();fig.savefig(path,dpi=180);plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--archive',type=Path,default=ROOT/'results/traces/test')
    p.add_argument('--output',type=Path,default=ROOT/'results/wire-payload-v2/test')
    p.add_argument('--log-dir',type=Path,default=ROOT/'results/traces/wire-payload-v2/test')
    p.add_argument('--smoke',action='store_true')
    args=p.parse_args();check(not args.output.exists() and not args.log_dir.exists(),'Exclusive output/log path exists')
    manifest,selected=inputs(args.smoke)
    cfg=load();args.output.mkdir(parents=True);args.log_dir.mkdir(parents=True)
    verified={};grouped=defaultdict(Counter);by_seed=defaultdict(Counter);by_scenario=defaultdict(Counter)
    waits=defaultdict(lambda: {'frames':Counter(),'seconds':Counter(),'censored':0})
    histograms=defaultdict(Counter)
    old_per_run={(r['seed'],r['scenario'],r['method'],r['multiplier']):r for r in csv.DictReader((ROOT/'results/wire-payload/test/per_run.csv').open())}
    per_run=GzipCSV(args.output/'per_run.csv.gz');episodes_out=GzipCSV(args.output/'recovery_episodes.csv.gz')
    invariants=GzipCSV(args.output/'invariants.csv.gz')
    trace_raw=(args.log_dir/'link_events.jsonl.gz').open('xb')
    trace=gzip.GzipFile(filename='',mode='wb',fileobj=trace_raw,compresslevel=1,mtime=0)
    trace.write(canonical({'type':'header','columns':EVENT_COLUMNS,'seed':LINK_SEED,'version':2})+b'\n')
    excerpts=[];event_count=0;previous=None;truth=None;archived_uploads=0
    for index,original in enumerate(selected):
        seed,scenario=int(original['seed']),original['scenario']
        identity=dict(seed=seed,scenario=scenario,method=original['method'],multiplier=float(original['multiplier']))
        if previous!=(seed,scenario):
            truth=read_archive(args.archive,f'{seed}/{scenario}/signals.json.gz',manifest,verified);previous=seed,scenario
        relative=f"{seed}/{scenario}/{original['method']}-{float(original['multiplier']):g}.json.gz"
        result=read_archive(args.archive,relative,manifest,verified)
        audited,_=audit_result(result,truth,original,cfg['evaluation']['event_match_tolerance_s'])
        v1old=old_per_run[(original['seed'],scenario,original['method'],original['multiplier'])]
        check(audited['binary_bytes']==int(v1old['binary_bytes']),'Archived v1 per-run cost differs')
        check(audited['original_envelopes_sha256']==v1old['original_envelopes_sha256'],'Uploaded envelope stream changed since v1')
        envelopes=[envelope_from_record(r) for r in result['records'] if r['upload']]
        v1_frames=[encode_v1(e) for e in envelopes]
        for e,f in zip(envelopes,v1_frames):check(exact(e,decode_v1(f)),'Stateless baseline decode failed')
        archived_uploads+=len(envelopes)
        hashes=[sha(canonical(e)) for e in envelopes]
        invariants.write({**original,**audited,'archive_sha256':verified[relative],
                          'envelopes_identical_to_v1':True,'loss0_v2_verified_periods':'8;16;32'})
        for period in PERIODS:
            packets=encode_stream(envelopes,period)
            restarted=encode_stream(envelopes,period,restart=True)
            for frame in v1_frames:histograms[(original['method'],float(original['multiplier']),period,'v1')][len(frame)]+=1
            for packet in packets:histograms[(original['method'],float(original['multiplier']),period,'v2')][len(packet.wire)]+=1
            for profile in PROFILES:
                emitted=restarted if profile=='sender_restart' else packets
                measured,episodes,events=simulate(envelopes,emitted,v1_frames,profile,seed,scenario,hashes)
                if profile=='loss0':check(measured['v2_decoded']==len(envelopes),'No-loss reconstruction failed')
                row={**identity,'period':period,'profile':profile,**measured};per_run.write(row)
                key=original['method'],float(original['multiplier']),period,profile
                grouped[key].update(measured);grouped[key]['runs']+=1
                by_seed[(*key,seed)].update(measured);by_seed[(*key,seed)]['runs']+=1
                by_scenario[(*key,scenario)].update(measured);by_scenario[(*key,scenario)]['runs']+=1
                for ep in episodes:
                    epkey=(*key,ep['codec'])
                    if ep['censored']:waits[epkey]['censored']+=1
                    else:
                        waits[epkey]['frames'][ep['wait_frames']]+=1;waits[epkey]['seconds'][ep['wait_s']]+=1
                    episodes_out.write({**identity,'period':period,'profile':profile,**ep})
                trace.write(canonical({'identity':identity,'period':period,'profile':profile,'events':events})+b'\n')
                event_count+=len(events)
                if seed==20 and scenario=='spike_same_short' and original['method']=='TAIS' and float(original['multiplier'])==1 and period==16:
                    for event in events:excerpts.append({**identity,'period':period,'profile':profile,**dict(zip(EVENT_COLUMNS,event))})
        if (index+1)%500==0:print(f'Validated {index+1}/{len(selected)} streams; logged {event_count} link events',flush=True)
    trace.close();trace_raw.close();per_run.close();episodes_out.close();invariants.close()
    source_summary={(r['method'],float(r['multiplier'])):r for r in csv.DictReader((ROOT/'results/wire-payload/test/summary.csv').open()) if r['encoding']=='Binary'}
    summaries=[];wait_rows=[]
    for key,total in sorted(grouped.items()):
        method,multiplier,period,profile=key
        if not args.smoke:check(total['v1_bytes']==int(source_summary[(method,multiplier)]['bytes']),'V1 aggregate changed')
        r=dict(method=method,multiplier=multiplier,period=period,profile=profile,**total)
        r['v2_saving_vs_v1']=1-r['v2_bytes']/r['v1_bytes']
        r['received_unrestored_rate']=r['received_unrestored']/r['received'] if r['received'] else None
        r['permanently_missing_v2_rate']=r['permanently_missing_v2']/r['sent']
        r['decoded_v2_rate']=r['v2_decoded']/r['sent']
        source=source_summary[(method,multiplier)]
        for field in ('samples','tp','missed','false_reports','fault_induced_false','precision','recall','f1'):
            r['frozen_sender_'+field]=source[field] if not args.smoke else 'N/A partial smoke'
        summaries.append(r)
        for codec in ('v1','v2'):
            w=waits[(*key,codec)];n=sum(w['frames'].values())
            item=dict(method=method,multiplier=multiplier,period=period,profile=profile,codec=codec,
                      completed_episodes=n,censored_episodes=w['censored'])
            for unit,hist in w.items():
                if unit=='censored':continue
                item['mean_wait_'+unit]=sum(v*c for v,c in hist.items())/n if n else None
                item['p95_wait_'+unit]=percentile(hist,.95)
                item['max_wait_'+unit]=max(hist) if hist else None
            wait_rows.append(item)
    write_csv(args.output/'summary.csv',summaries)
    write_csv(args.output/'recovery_summary.csv',wait_rows)
    write_csv(args.output/'by_seed.csv',[dict(method=k[0],multiplier=k[1],period=k[2],profile=k[3],seed=k[4],**v) for k,v in sorted(by_seed.items())])
    write_csv(args.output/'by_scenario.csv',[dict(method=k[0],multiplier=k[1],period=k[2],profile=k[3],scenario=k[4],**v) for k,v in sorted(by_scenario.items())])
    write_csv(args.output/'trace_excerpt.csv',excerpts)
    size_rows=[]
    for (method,multiplier,period,codec),hist in sorted(histograms.items()):
        size_rows.append(dict(method=method,multiplier=multiplier,period=period,codec=codec,**frame_stats(hist)))
    write_csv(args.output/'frame_sizes.csv',size_rows)
    write_csv(args.output/'frame_histograms.csv',[dict(method=k[0],multiplier=k[1],period=k[2],codec=k[3],frame_bytes=size,count=n) for k,hist in sorted(histograms.items()) for size,n in sorted(hist.items())])
    # Paired cluster bootstrap on original seed blocks, never individual frames.
    import numpy as np
    rng=np.random.default_rng(2026101809);uncertainty=[]
    for key,total in sorted(grouped.items()):
        blocks=[v for k,v in sorted(by_seed.items()) if k[:4]==key]
        n=len(blocks);indices=rng.integers(0,n,size=(10000,n))
        a=np.array([v['v1_bytes'] for v in blocks]);b=np.array([v['v2_bytes'] for v in blocks]);m=np.array([v['received_unrestored'] for v in blocks])
        samples={'v2_minus_v1_bytes':(b-a)[indices].sum(axis=1),
                 'saving_fraction':1-b[indices].sum(axis=1)/a[indices].sum(axis=1),
                 'additional_missing_v2_minus_v1':m[indices].sum(axis=1)}
        estimates={'v2_minus_v1_bytes':total['v2_bytes']-total['v1_bytes'],
                   'saving_fraction':1-total['v2_bytes']/total['v1_bytes'],
                   'additional_missing_v2_minus_v1':total['received_unrestored']}
        for name,values in samples.items():
            lo,hi=np.quantile(values,[.025,.975]);uncertainty.append(dict(method=key[0],multiplier=key[1],period=key[2],profile=key[3],metric=name,
                estimate=estimates[name],ci95_low=float(lo),ci95_high=float(hi),clusters=n,replicates=10000,bootstrap_seed=2026101809))
    write_csv(args.output/'paired_uncertainty.csv',uncertainty)
    plot(summaries,args.output/'cost_recovery.png')
    primary=next(r for r in summaries if r['method']=='TAIS' and r['multiplier']==1 and r['period']==16 and r['profile']=='loss0')
    verification=dict(scope='partial smoke' if args.smoke else 'full historical format/link engineering review',
        runs=len(selected),archived_uploads=archived_uploads,periods=PERIODS,profiles=PROFILES,
        all_loss0_frames_exact=True,all_reconstructed_received_frames_exact=True,
        sender_policy_outputs_unchanged=True,v1_per_run_bytes_and_envelope_hashes_identical=True,
        primary_tais_v2_bytes=primary['v2_bytes'],primary_saving_vs_v1=primary['v2_saving_vs_v1'],
        challenge_below_1455208=None if args.smoke else primary['v2_bytes']<1455208,link_event_rows=event_count)
    (args.output/'verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    metadata=dict(created_utc=datetime.now(timezone.utc).isoformat(),base=BASE,
        implementation_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),command=sys.argv,
        source_experiment_commit=manifest['source_commit'],source_config_sha256=manifest['config_sha256'],
        source_files={p:sha((ROOT/p).read_bytes()) for p in ['results/test/manifest.json','results/test/metrics.csv','results/test/summary.csv','results/wire-payload/test/manifest.json','results/wire-payload/test/per_run.csv','results/wire-payload/test/summary.csv']},
        implementation_files={p:sha((ROOT/p).read_bytes()) for p in ['src/tais/wire_v2.py','src/tais/wire_link.py','scripts/audit_wire_health.py','scripts/benchmark_wire_v2.py','tests/test_wire_v2.py']},
        verified_archives=len(verified),verified_archive_index_sha256=sha(canonical(verified)),
        original_manifest_pins_all_archive_hashes=True,archive_root=str(args.archive.resolve()),
        main_period=16,sensitivity_periods=[8,32],link_seed=LINK_SEED,event_columns=EVENT_COLUMNS,
        full_trace=dict(path=str((args.log_dir/'link_events.jsonl.gz').resolve()),sha256=sha((args.log_dir/'link_events.jsonl.gz').read_bytes()),bytes=(args.log_dir/'link_events.jsonl.gz').stat().st_size,events=event_count),
        python=sys.version,platform=platform.platform(),outputs={p.name:sha(p.read_bytes()) for p in sorted(args.output.iterdir())})
    (args.output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n')
    print(json.dumps(verification,indent=2),flush=True)

if __name__=='__main__':main()
