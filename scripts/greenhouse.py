"""Explicit local-file audit / resolution-supported reconstruction; no bundled raw data.

Column names are intentionally supplied from the actual CSV, not guessed from a
paper. The real file has not been fetched in the initial environment (HTTP 403).
"""
import argparse,hashlib,json,urllib.request
from pathlib import Path
import numpy as np
import pandas as pd


def audit(path,out,mapping=None,time_format=None):
    """Write a source audit and optional explicit-mapping fixed-period reconstruction.

    Require supplied time format and monotonic unique source timestamps. Never
    interpolate within gaps or treat control state as event/fault ground truth.
    Reconstruction error compares available observations, not a latent field."""
    data=pd.read_csv(path)
    report={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'rows':len(data),'columns':list(data),
            'missing_per_column':data.isna().sum().to_dict(),'duplicate_rows':int(data.duplicated().sum()),'status':'header_audit_only'}
    if mapping is not None:
        # Require explicit mapping for unverified field spellings and time layout.
        m=json.loads(mapping.read_text())
        for name in ['date','time','temperature','humidity','state']:
            if m[name] not in data:raise ValueError(f'Missing mapped column {m[name]}')
        if not time_format:raise ValueError('--time-format is required; do not guess date order')
        times=pd.to_datetime(data[m['date']].astype(str)+' '+data[m['time']].astype(str),format=time_format,errors='coerce')
        if times.isna().any():raise ValueError('Unparsed timestamps; inspect raw data before replay')
        if not times.is_monotonic_increasing or times.duplicated().any():raise ValueError('Nonmonotonic/duplicate timestamps; preserve and resolve explicitly')
        seconds=(times-times.iloc[0]).dt.total_seconds().to_numpy()
        gaps=np.diff(seconds)
        report.update(status='mapped_audit_and_fixed_reconstruction',median_interval_s=float(np.median(gaps)),interval_counts=pd.Series(gaps).value_counts().sort_index().to_dict(),gaps_over_300_s=int((gaps>300).sum()))
        processed=pd.DataFrame({'timestamp':seconds,'temperature':pd.to_numeric(data[m['temperature']],errors='coerce'),'humidity':pd.to_numeric(data[m['humidity']],errors='coerce'),'control_state_reference':data[m['state']]})
        report['numeric_missing']=processed[['temperature','humidity']].isna().sum().to_dict()
        processed.to_csv(out/'processed.csv',index=False)
        # Use observed timestamps only, no invention of within-gap values.
        metrics=[]
        for interval in [300,600,900,1800,3600]:
            used=[];due=seconds[0]
            for i,t in enumerate(seconds):
                if t>=due:used.append(i);due=t+interval
            row={'interval_s':interval,'samples':len(used),'uploads':len(used),'event_recall':None,'label_type':'none; control state reference only'}
            for name in ['temperature','humidity']:
                raw=processed[name].to_numpy();valid=[i for i in used if np.isfinite(raw[i])]
                if not valid:row[f'mae_{name}']=None;row[f'rmse_{name}']=None;continue
                ix=np.searchsorted(seconds[valid],seconds,side='right')-1;mask=(ix>=0)&np.isfinite(raw)
                e=raw[np.array(valid)[np.maximum(0,ix)]][mask]-raw[mask]
                row[f'mae_{name}']=float(np.mean(abs(e)));row[f'rmse_{name}']=float(np.sqrt(np.mean(e**2)))
            metrics.append(row)
        pd.DataFrame(metrics).to_csv(out/'fixed_reconstruction.csv',index=False)
    (out/'audit.json').write_text(json.dumps(report,indent=2,default=str)+'\n')
    print(json.dumps(report,indent=2,default=str))


def main():
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='action',required=True)
    d=sub.add_parser('download');d.add_argument('--url',required=True);d.add_argument('--output',type=Path,required=True);d.add_argument('--sha256')
    a=sub.add_parser('audit');a.add_argument('file',type=Path);a.add_argument('--output',type=Path,default=Path('data/processed/greenhouse'));a.add_argument('--mapping',type=Path);a.add_argument('--time-format')
    args=p.parse_args()
    if args.action=='download':
        # URL must be copied from the DOI's official download link, with license checked.
        raw=urllib.request.urlopen(args.url,timeout=60).read();digest=hashlib.sha256(raw).hexdigest()
        if args.sha256 and args.sha256!=digest:raise SystemExit('Checksum mismatch; nothing written')
        if b'<html' in raw[:1000].lower():raise SystemExit('HTML response is not a data file')
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_bytes(raw)
        print(json.dumps({'url':args.url,'sha256':digest,'bytes':len(raw),'path':str(args.output)}))
    else:
        args.output.mkdir(parents=True,exist_ok=True);audit(args.file,args.output,args.mapping,args.time_format)
if __name__=='__main__':main()
