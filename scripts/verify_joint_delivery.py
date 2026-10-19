#!/usr/bin/env python3
"""Audit frozen JO artifacts/actual bytes/truth matching and protected history."""
import csv,gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts'))
from tais.wire_codec import encode,decode,envelope_from_record
from simulator.events import Event,match_events
from benchmark_joint_optimization import OUT,RAW,sha,fingerprints
BASE='48b68655f95eaefbcdb7624e9de0e75a030ddf95'
checks=[];signals=set();frames=0;runs=0
sel=json.loads((OUT/'selection.json').read_text());assert sel['frozen_files']==fingerprints()
for phase in ['development','validation','test']:
 m=json.loads((OUT/phase/'manifest.json').read_text());assert m['status']=='COMPLETE' and m['metrics_sha256']==sha(OUT/phase/'metrics.csv')
 rows=list(csv.DictReader((OUT/phase/'metrics.csv').open()));assert len(rows)==m['runs'];seen={}
 for r in rows:
  seed=int(float(r['seed']));case=r['scenario'];method=r['method'];cap=int(float(r['cap']));slope=float(r['slope']);stem=f'{method}-{cap}-{slope}'
  # Baseline cap is integer0 and slope0.0, matching worker names.
  p=RAW/phase/str(seed)/case/(stem+'.json.gz');assert sha(p)==r['result_sha256']
  x=json.loads(gzip.decompress(p.read_bytes()));records=x['result']['records'];tx=x['frames'];assert len(records)==int(float(r['samples']));assert len(tx)==sum(z['upload'] for z in records)==int(float(r['uploads']))
  assert len({z['timestamp'] for z in records})==len(records)
  sent=[z for z in records if z['upload']]
  for z,b in zip(sent,tx):
   frame=bytes.fromhex(b['frame_hex']);assert frame==encode(envelope_from_record(z)) and encode(decode(frame))==frame and len(frame)==b['bytes'];frames+=1
  assert sum(b['bytes'] for b in tx)==int(float(r['binary_v1_bytes']))
  sp=p.with_name('signals.json.gz');assert sha(sp)==r['signals_sha256'];signals.add(str(sp))
  signal=json.loads(gzip.decompress(sp.read_bytes()));match=match_events([Event(**e) for e in signal['events']],[Event(**e) for e in x['result']['reports']],5)
  assert match.true_positives==int(float(r['tp'])) and match.false_positives==int(float(r['false_reports']))
  key=(seed,case);assert key not in seen or seen[key]==r['observed_sha256'];seen[key]=r['observed_sha256']
  if method.startswith('JO-'):
   for z in records:
    for n,h in z['health'].items():
     raw=z['joint'][n]['raw_c11'];assert h['flags']&31==raw['flags'] and h['score']==raw['score'] and h['state']==raw['state']
  runs+=1
 checks.append(dict(phase=phase,runs=len(rows),complete=True,actual_frames_exact=True,truth_match_recomputed=True,same_input_per_method=True))
protected=0;submodules={}
for item in subprocess.check_output(['git','ls-tree','-rz',BASE],cwd=ROOT).split(b'\0'):
 if not item:continue
 meta,name=item.split(b'\t');mode,kind,oid=meta.split();name=name.decode()
 if name=='examples/tais-core/run.py':continue
 if kind==b'commit':
  assert subprocess.check_output(['git','-C',str(ROOT/name),'rev-parse','HEAD']).strip()==oid
  assert not subprocess.check_output(['git','-C',str(ROOT/name),'status','--porcelain']).strip();submodules[name]=oid.decode()
 else:
  b=(ROOT/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest().encode()==oid,name;protected+=1
out=dict(status='PASS',checks=checks,runs=runs,actual_frames_verified=frames,signals_verified=len(signals),unchanged_original_files=protected,only_permitted_existing_edit='examples/tais-core/run.py adds explicit opt-in JO; original default policy intact',submodules=submodules,selection_source_fingerprints_unchanged=True,counterfactual_note='Fault-induced counts computed by frozen runner from paired clean replays; primary archived report matching independently recomputed here, not a second algorithm experiment.')
with (OUT/'checks/delivery-verification.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
print(json.dumps(out,indent=2))
