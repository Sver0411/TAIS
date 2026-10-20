#!/usr/bin/env python3
"""Offline explanation only: actual Core journals vs independent synthetic truth."""
import csv,gzip,json,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.signals import generate
OUT=ROOT/'results/tais-joint';rows=[]
fig,axes=plt.subplots(2,1,figsize=(12,8))
for ax,case in zip(axes,['clean_short','drift_none_long']):
 tr=generate(load(),20,case)
 for i,policy in enumerate(['gateonly','tais-jo']):
  path=OUT/'core'/(case+'-'+policy)/'journal.jsonl';entries=[json.loads(line) for line in path.open()];samples=[e['record'] for e in entries if e['kind']=='sample']
  tx={e['envelope']['timestamp']:e['frame_bytes'] for e in entries if e['kind']=='tx'}
  for r in samples:
   h=r['health']['temperature'];j=r.get('joint',{}).get('temperature',{});raw=j.get('raw_c11',h)
   rows.append(dict(scenario=case,policy=policy,timestamp=r['timestamp'],value=r['values']['temperature'],score=r['scores']['temperature'],c11_state=raw['state'],c11_flags=raw['flags'],app_suspect=j.get('app_suspect_drift',False),candidate_start=j.get('candidate_start'),event_active=r['active']['temperature'],upload=r['upload'],reasons='|'.join(r['reasons']),bytes=tx.get(r['timestamp'],0)))
  ax.scatter([r['timestamp'] for r in samples],[i]*len(samples),s=8,label=policy+' sample')
  active=[r for r in samples if r['active']['temperature']];ax.scatter([r['timestamp'] for r in active],[i+.2]*len(active),marker='^',s=16,label=policy+' active')
  ax.scatter(list(tx),[i-.15]*len(tx),marker='|',s=30,label=policy+' upload')
  evidence=[r['timestamp'] for r in samples if r['scores']['temperature']>8 and not r['active']['temperature']]
  ax.scatter(evidence,[i+.1]*len(evidence),marker='x',s=12,color='gray',label='score>8, unconfirmed' if i==0 else None)
  for bit,token,color in [(8,'C11 DRIFT','purple'),(32,'APP suspicion','black')]:
   ts=[r['timestamp'] for r in samples if r['health']['temperature']['flags']&bit]
   if ts:ax.scatter(ts,[i+.32 if bit==32 else i-.32]*len(ts),s=9,marker='s',color=color,label=policy+' '+token)
 for e in tr.events:ax.axvspan(e.start_s,e.end_s,color='green',alpha=.15,label='independent event truth')
 for f in tr.faults:ax.axvspan(f.start_s,f.end_s,color='red',alpha=.1,label='injected fault (offline label)')
 ax.set_title(case+' seed20 | actual sampled/read/upload times');ax.set_yticks([0,1],['GateOnly','JO-Full']);ax.set_xlim(450,1400 if 'drift' in case else 950);ax.set_xlabel('source seconds');ax.legend(fontsize=7,ncol=4)
fig.tight_layout();fig.savefig(OUT/'timelines.png',dpi=150);plt.close(fig)
with (OUT/'case-timeline.csv').open('x',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
