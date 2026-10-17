"""Run unchanged upstream in an isolated copy and retain logs and hashes."""
import hashlib,json,os,platform,shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'results/baseline';out.mkdir(parents=True,exist_ok=True)
report={'python':sys.version,'platform':platform.platform(),'commands':[],'sha256':{}}
report['dependencies']=subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True)
report['compiler']=subprocess.check_output(['cc','--version'],text=True)
for project in ['AdaptiveSense','SensorTrust']:
 source=ROOT/'vendor'/project
 report[project]=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source,text=True).strip()
 with tempfile.TemporaryDirectory(prefix='tais-baseline-') as temp:
  dest=Path(temp)/project
  shutil.copytree(source,dest,ignore=shutil.ignore_patterns('.git','__pycache__','.pytest_cache','build'))
  commands=[[sys.executable,'-m','pytest','tests/','-q']]
  if project=='AdaptiveSense':commands += [[sys.executable,'scripts/check_config_parity.py'],[sys.executable,'dataset/generate_dataset.py'],[sys.executable,'analysis/analyze.py']]
  else:commands += [['cc','-std=c11','-Wall','-Wextra','-Werror','-Icore','core/sensor_trust.c','tests/test_core.c','-lm','-o','test_core'],['./test_core']]
  for i,cmd in enumerate(commands):
   r=subprocess.run(cmd,cwd=dest,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env={**os.environ,'MPLBACKEND':'Agg'})
   name=f'{project}-{i}.log';(out/name).write_text(r.stdout)
   report['commands'].append({'project':project,'argv':cmd,'returncode':r.returncode,'log':name})
   print(project,cmd,'exit',r.returncode,r.stdout[-400:],flush=True)
  if project=='AdaptiveSense':
   for name in ['metrics_all.csv','metrics_summary.csv']:
    p=dest/'results'/name
    if p.exists():
     shutil.copy2(p,out/name);report['sha256'][name]=hashlib.sha256(p.read_bytes()).hexdigest()
     committed=source/'results'/name
     report['sha256']['upstream_'+name]=hashlib.sha256(committed.read_bytes()).hexdigest() if committed.exists() else None
     report['sha256']['byte_equal_'+name]=committed.exists() and p.read_bytes()==committed.read_bytes()
(out/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
if any(c['returncode'] for c in report['commands']):raise SystemExit('Upstream failures retained; inspect logs')
