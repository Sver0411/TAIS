#!/usr/bin/env python3
"""Import verified numeric-seconds real records; never invent Hull Date mapping."""
import argparse,csv,hashlib,json,math
from pathlib import Path

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--input',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--time-column',default='timestamp');p.add_argument('--temperature-column',default='temperature');p.add_argument('--humidity-column',default='humidity');p.add_argument('--time-semantics',required=True,help='document the independently verified timestamp meaning; not a timezone guess');a=p.parse_args()
 if a.output.exists():raise FileExistsError('Never overwrite source or existing imports')
 with a.input.open(newline='',encoding='utf-8-sig') as f:
  r=csv.DictReader(f);columns=[a.time_column,a.temperature_column,a.humidity_column]
  if not set(columns)<=set(r.fieldnames or []):raise ValueError('BLOCKED: verified numeric-seconds columns missing; Hull Date/Time is not automatically mapped. Supply authoritative mapping before import.')
  rows=[];last=-1
  for i,row in enumerate(r,2):
   t=float(row[a.time_column])
   if not math.isfinite(t) or t<0 or t<=last:raise ValueError(f'Nonmonotonic/invalid timestamp at row{i}; no sorting or repair')
   last=t;values=[float(row[c]) if row[c].strip() else None for c in columns[1:]]
   rows.append(dict(timestamp=t,temperature=values[0],humidity=values[1]))
 with a.output.open('x',newline='') as f:
  w=csv.DictWriter(f,fieldnames=['timestamp','temperature','humidity']);w.writeheader();w.writerows(rows)
 a.output.with_suffix(a.output.suffix+'.provenance.json').write_text(json.dumps(dict(input=str(a.input),sha256=hashlib.sha256(a.input.read_bytes()).hexdigest(),rows=len(rows),time_semantics=a.time_semantics,interpolation=False,natural_truth_labels=False),indent=2)+'\n')
if __name__=='__main__':main()
