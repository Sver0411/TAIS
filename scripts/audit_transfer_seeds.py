"""Reuse the previous exhaustive audit; inspect new current and historical metadata."""
import hashlib,json,os,re,subprocess
from pathlib import Path
from audit_budget_seeds import parse_text
ROOT=Path(__file__).resolve().parents[1]
def compact_inventory(records):
    archives=[r for r in records if r.get("kind")=="archive_identity"]
    names=sorted(r["path"] for r in archives)
    return [r for r in records if r.get("kind")!="archive_identity"],dict(paths=len(names),path_inventory_sha256=hashlib.sha256("\n".join(names).encode()).hexdigest(),seeds=sorted({s for r in archives for s in r["seeds"]}))

def main():
    out=ROOT/'results/tais-transfer/seed-audit.json'
    assert not out.exists()
    prior=json.loads((ROOT/'results/tais-paper/seed-audit.json').read_text())
    used=set(range(600))|{s for _,ss in prior['inventory'] for s in ss}|{s for ss in prior['seeds'].values() for s in ss};inventory=[];errors=[];seen=set()
    for root in [ROOT,Path('/Users/mac/Documents/TAIS-external-data')]:
        if not root.exists():continue
        for parent,dirs,names in os.walk(root):
            dirs[:]=[d for d in dirs if d not in ('.git','.venv','__pycache__','build','node_modules')]
            for name in names:
                p=Path(parent)/name
                if name.endswith('.gz'):
                    seeds={int(v) for v in re.findall(r'(?:^|/)(\d+)(?:/|[-_])',str(p.relative_to(root)))}
                    if seeds:used|=seeds;inventory.append(dict(path=str(p),kind='archive_identity',seeds=sorted(seeds)))
                if p.suffix not in ('.json','.yaml','.yml','.csv'):continue
                try:
                    data=p.read_bytes();seeds=parse_text(data.decode('utf-8-sig'),p.suffix);h=hashlib.sha256(data).hexdigest();seen.add(h)
                    if seeds:used|=seeds;inventory.append(dict(path=str(p),sha256=h,seeds=sorted(seeds)))
                except (ValueError,UnicodeError,OSError) as e:errors.append(dict(path=str(p),error=str(e)))
    # Also inspect deleted/replaced structured blobs across all refs. Avoid reading
    # duplicate content already audited from the working tree.
    objects=subprocess.check_output(['git','rev-list','--all','--objects','--','results','configs','src','scripts','tests','docs'],cwd=ROOT,text=True)
    historical=0
    for line in objects.splitlines():
        fields=line.split(' ',1)
        if len(fields)!=2:continue
        oid,path=fields
        if Path(path).suffix not in ('.json','.yaml','.yml','.csv'):continue
        data=subprocess.check_output(['git','cat-file','blob',oid],cwd=ROOT)
        if hashlib.sha256(data).hexdigest() in seen:continue
        try:seeds=parse_text(data.decode('utf-8-sig'),Path(path).suffix)
        except (ValueError,UnicodeError) as e:errors.append(dict(path=path,error=str(e)));continue
        historical+=1
        if seeds:used|=seeds;inventory.append(dict(path='git:'+oid+':'+path,seeds=sorted(seeds)))
    assert not errors,errors
    final=list(range(700,720));engineering=[690,691]
    assert not used.intersection(final+engineering),'Choose fresh range before generating any data'
    result=dict(status='PASS',base_commit='0170196dda10f78b85d5e4b685d56331a0021083',prior_audit_sha256=hashlib.sha256((ROOT/'results/tais-paper/seed-audit.json').read_bytes()).hexdigest(),all_observed_seed_values=sorted(used),final_seeds=final,engineering_seeds=engineering,collisions=[],historical_extra_blobs=historical,inventory=inventory,limitations='Accessible repository/ref histories and local external-data metadata; inaccessible external runs cannot be audited.')
    result['inventory'],result['archive_inventory']=compact_inventory(inventory)
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print('PASS: engineering690,691; final700–719 unused')
if __name__=='__main__':main()
