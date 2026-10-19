import sys,gzip,json,csv,collections
from pathlib import Path
sys.path.insert(0,'src')
from tais.config import load
from simulator.events import Event,match_events
root=Path('results/traces/budget-matched/test');out=Path('results/tais-joint/history')
cases=['clean_short','clean_event','drift_none_long','drift_same_long','drift_cross_long','spike_same_long','missing_cross_long','range_same_long','stable_offset_none_long'];rows=[];reasons=collections.Counter()
for seed in range(170,180):
 for c in cases:
  d=json.loads(gzip.decompress((root/str(seed)/c/'GateOnly-1.json.gz').read_bytes()));s=json.loads(gzip.decompress((root/str(seed)/c/'signals.json.gz').read_bytes()));r=d['records']
  match=match_events([Event(**e) for e in s['events']],[Event(**e) for e in d['reports']],5)
  for x in r:
   if x['upload']:reasons.update(x['reasons'])
  for e in s['events']:
   hit=any(x['channel']==e['channel'] and e['start_s']-5<=x['start_s']<=e['end_s']+5 for x in d['reports'])
   sampled=any(e['start_s']<=x['timestamp']<=e['end_s'] for x in r)
   local=any(x['channel']==e['channel'] and x['end_s']>=e['start_s'] and x['start_s']<=e['end_s'] for x in d['detections'])
   rows.append(dict(seed=seed,scenario=c,sampled=sampled,local=local,reported=hit,first_raw_drift=next((x['timestamp'] for x in r if x['health']['temperature']['flags']&8),None),false_reports=match.false_positives))
with (out/'bottlenecks.csv').open('x') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
(out/'upload-reasons.json').write_text(json.dumps(reasons,indent=2))
print(json.dumps(dict(events=len(rows),unsampled=sum(not r['sampled'] for r in rows),sampled_unreported=sum(r['sampled'] and not r['reported'] for r in rows),reasons=reasons),indent=2))
