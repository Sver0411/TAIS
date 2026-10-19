#!/usr/bin/env python3
"""Independent SU archive/bytes/C11/parity checks; no policy rerun or tuning."""
import csv,gzip,hashlib,json,subprocess,sys
import numpy as np
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from tais.config import load
from tais.trust import SensorTrust
from tais.wire_codec import encode,decode,envelope_from_record
from tais.metrics import evaluate
from simulator.events import Event,match_events
from benchmark_su import OUT,sha,fingerprints,canon,receiver_result
BASE='8928fb133cad4b9352fb96db79b79ff40cc4d7c7'

def restore(x):
 x['reports']=[Event(**e) for e in x['reports']];x['detections']=[Event(**e) for e in x['detections']];return x

def main():
 all_runs=frames_checked=0;phases=[];cf_checked=set();signal_checked=set();cfg=load()
 lock=json.loads((OUT/'selection.json').read_text());assert lock['sources']==fingerprints()
 for phase in ['engineering','development','validation','test']:
  manifest=json.loads((OUT/phase/'manifest.json').read_text());assert manifest['status']=='COMPLETE';assert sha(OUT/phase/'metrics.csv')==manifest['metrics_sha256']
  hist={m:np.zeros(1800,dtype=np.int64) for m in manifest['methods']}
  raw=Path(manifest['archive_root'])/phase;table=list(csv.DictReader((OUT/phase/'metrics.csv').open()));keys={(int(r['seed']),r['scenario'],r['method']) for r in table};expected={(s,c,m) for s in manifest['seeds'] for c in manifest['cases'] for m in manifest['methods']};assert keys==expected and len(keys)==len(table)
  for seed in manifest['seeds']:
   cf_cache={}
   for case in manifest['cases']:
    results={};input_hash=None;signal_path=raw/str(seed)/case/'signals.json.gz';signal=json.loads(gzip.decompress(signal_path.read_bytes()));signal_checked.add(str(signal_path))
    class Obj:pass
    trace=Obj();trace.events=[Event(**e) for e in signal['events']];trace.faults=[type('Fault',(),f)() for f in signal['faults']];trace.observed=signal['observed'];trace.latent=signal['latent']
    for method in manifest['methods']:
     row=next(r for r in table if int(r['seed'])==seed and r['scenario']==case and r['method']==method)
     assert sha(signal_path)==row['signals_sha256'];assert input_hash is None or input_hash==row['observed_sha256'];input_hash=row['observed_sha256'];assert hashlib.sha256(canon(signal['observed'])).hexdigest()==input_hash
     p=raw/str(seed)/case/(method+'.json.gz');assert sha(p)==row['result_sha256'];data=json.loads(gzip.decompress(p.read_bytes()));result=restore(data['result']);rs=result['records'];results[method]=rs
     cfkey=(signal['relationship'],signal['profile'],method)
     if cfkey not in cf_cache:
      q=raw/str(seed)/'counterfactuals'/f'{cfkey[0]}-{cfkey[1]}-{method}.json.gz';assert sha(q)==row['counterfactual_sha256'];c=json.loads(gzip.decompress(q.read_bytes()));c['result']=restore(c['result']);cf_cache[cfkey]=c;cf_checked.add(str(q))
     cf=cf_cache[cfkey];stats=evaluate(trace,result,cfg,cf['result'])
     for k in ['tp','false_reports','fault_induced_false','samples','uploads','fault_detected','fault_type_detected']:assert stats[k]==float(row[k]),(phase,seed,case,method,k)
     sent=[r for r in rs if r['upload']];assert len(sent)==len(data['frames']);total=0
     for r,f in zip(sent,data['frames']):
      b=bytes.fromhex(f['frame_hex']);assert b==encode(envelope_from_record(r)) and encode(decode(b))==b and f['bytes']==len(b);total+=len(b);frames_checked+=1
     assert total==float(row['binary_v1_bytes'])
     times=np.array([f['timestamp'] for f in data['frames']]);grid=np.arange(len(signal['observed']));idx=np.searchsorted(times,grid,side='right')-1;assert (idx>=0).all();ages=grid-times[idx];h=np.bincount(ages.astype(int),minlength=1800);assert h.tolist()==data['age_histogram'];hist[method]+=h
     rx,history=receiver_result(result,data['frames']);rxcf,_=receiver_result(cf['result'],cf['frames']);rx_stats=evaluate(trace,rx,cfg,rxcf)
     for k in ['tp','false_reports','fault_induced_false']:assert rx_stats[k]==float(row['rx_'+k])
     assert canon(history)==canon(data['receiver'])
     if method.startswith('JO-SU-') or method=='GateOnly+U':
      assert float(row['important_edges_unreported'])==float(row['important_edge_delay_max_s'])==0
      assert all(h['flags']&~31==0 for r in rs for h in r['health'].values())
     all_runs+=1
    def local(rs):return [{k:v for k,v in r.items() if k not in ['upload','reasons','payload_bytes','su']} for r in rs]
    assert canon(local(results['JO-S']))==canon(local(results['JO-SU-20']))
    assert canon(local(results['GateOnly']))==canon(local(results['GateOnly+U']))
   print(phase,seed,'verified',flush=True)
  for age in csv.DictReader((OUT/phase/'pooled_age.csv').open()):
   h=hist[age['method']];assert float(age['mean_age_s'])==float(np.arange(1800)@h/h.sum());assert int(age['p95_age_s'])==int(np.searchsorted(np.cumsum(h),h.sum()*.95));assert int(age['max_age_s'])==int(np.flatnonzero(h)[-1])
  phases.append(dict(phase=phase,runs=len(table),input_and_bytes_and_receiver_exact=True,counterfactual_metrics_recomputed=True,upload_only_parity=True))
 protected=0;links={}
 for item in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
  if not item:continue
  meta,name=item.split(b'\t');mode,kind,oid=meta.split();name=name.decode()
  if name=='examples/tais-core/run.py':continue
  if kind==b'commit':
   assert subprocess.check_output(['git','-C',str(ROOT/name),'rev-parse','HEAD']).strip()==oid;assert not subprocess.check_output(['git','-C',str(ROOT/name),'status','--porcelain']).strip();links[name]=oid.decode()
  else:
   b=(ROOT/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest().encode()==oid,name;protected+=1
 output=dict(status='PASS',runs=all_runs,frames=frames_checked,signals=len(signal_checked),counterfactuals=len(cf_checked),phases=phases,original_tracked_files_unchanged=protected,upstream_unchanged=links,only_existing_file_changed='examples/tais-core/run.py explicit opt-in SU; default GateOnly intact',source_freeze_unchanged=True)
 with (OUT/'checks/archive-verification.json').open('x') as f:json.dump(output,f,indent=2);f.write('\n')
 print(json.dumps(output,indent=2))
if __name__=='__main__':main()
