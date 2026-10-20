"""Historical publisher targeting main through the GitHub Git Data API.

Executing or importing this file can update remote main without a PR. It is
not a generic maintenance upload helper. Object identities and non-forcing
ancestry are checked, but release authorization must come from the caller."""
import base64,datetime,json,re,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];REPO='repos/Sver0411/TAIS'

def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT)

def api(endpoint,method='GET',body=None):
    command=['gh','api',REPO+endpoint,'--method',method]
    if body is not None:command+=['--input','-']
    r=subprocess.run(command,input=json.dumps(body) if body is not None else None,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,cwd=ROOT)
    if r.returncode:raise RuntimeError(r.stderr)
    return json.loads(r.stdout)

def person(line):
    m=re.fullmatch(r'(.*) <(.*)> (\d+) ([+-])(\d\d)(\d\d)',line)
    name,email,stamp,sign,hour,minute=m.groups()
    zone=datetime.timezone(datetime.timedelta(minutes=(int(hour)*60+int(minute))*(1 if sign=='+' else -1)))
    return dict(name=name,email=email,date=datetime.datetime.fromtimestamp(int(stamp),zone).isoformat())

assert git('remote','get-url','origin').decode().strip() in ['https://github.com/Sver0411/TAIS.git','git@github.com:Sver0411/TAIS.git'], 'Unexpected destination; stop'
remote=api('/git/ref/heads/main')['object']['sha']
head=git('rev-parse','HEAD').decode().strip()
subprocess.run(['git','merge-base','--is-ancestor',remote,head],cwd=ROOT,check=True)
commits=git('rev-list','--reverse',remote+'..'+head).decode().splitlines()
print('Remote',remote,'local',head,'pending',len(commits),flush=True)
for commit in commits:
    raw=git('cat-file','commit',commit).decode();headers,message=raw.split('\n\n',1)
    fields={};parents=[]
    for line in headers.splitlines():
        key,value=line.split(' ',1)
        if key=='parent':parents.append(value)
        else:fields[key]=value
    assert parents==[remote],('Nonlinear or changed history',parents,remote)
    assert set(fields)=={'tree','author','committer'},'Unexpected commit header; stop rather than rewrite'
    parent_tree=git('rev-parse',remote+'^{tree}').decode().strip()
    changed=git('diff-tree','-r','--no-commit-id','--name-only','--no-renames','-z',remote,commit).decode().split('\0')
    entries=[]
    for path in filter(None,changed):
        entry=git('ls-tree','-z',commit,'--',path).decode().strip('\0')
        if not entry:
            entries.append(dict(path=path,mode='100644',type='blob',sha=None));continue
        metadata,name=entry.split('\t',1);mode,kind,sha=metadata.split()
        if kind=='blob':
            try:api('/git/blobs/'+sha)
            except RuntimeError:
                data=git('cat-file','blob',sha)
                out=api('/git/blobs','POST',{'encoding':'base64','content':base64.b64encode(data).decode()})
                assert out['sha']==sha,('Blob mismatch',path)
                time.sleep(.8)
        entries.append(dict(path=path,mode=mode,type=kind,sha=sha))
        print('Verified object',path,sha,flush=True)
    tree=api('/git/trees','POST',{'base_tree':parent_tree,'tree':entries})
    assert tree['sha']==fields['tree'],('Tree mismatch',tree['sha'],fields['tree'])
    made=api('/git/commits','POST',dict(tree=tree['sha'],parents=parents,message=message,author=person(fields['author']),committer=person(fields['committer'])))
    assert made['sha']==commit,('Commit mismatch; ref NOT updated',made['sha'],commit)
    assert api('/git/ref/heads/main')['object']['sha']==remote,'Remote moved; no force permitted'
    ref=api('/git/refs/heads/main','PATCH',{'sha':commit,'force':False})
    assert ref['object']['sha']==commit
    remote=commit
    print('Published exact commit',commit,flush=True)
assert api('/git/ref/heads/main')['object']['sha']==head
subprocess.run(['git','update-ref','refs/remotes/origin/main',head],cwd=ROOT,check=True)
print('VERIFIED_REMOTE_HEAD',head,flush=True)
