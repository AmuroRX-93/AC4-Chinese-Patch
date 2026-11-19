"""AC4 delta.5 load guard / Normal hotfix. Standard library only."""
from pathlib import Path
import argparse,hashlib,json,os,sys,struct,time,uuid,subprocess
from .delta import apply as apply_delta
from . import drb_text,archive
HERE=Path(__file__).resolve().parent

def digest(b):return hashlib.sha256(b).hexdigest()
def read_manifest():
 m=json.loads((HERE/'manifest.json').read_text(encoding='utf-8'))
 p=HERE/m['eboot']['patch']
 if digest(p.read_bytes())!=m['eboot']['patch_sha256']:raise ValueError('程序差分损坏，请重新下载。')
 return m

def game_root(p):
 p=Path(p).expanduser().resolve()
 if p.name=='USRDIR' and p.parent.name=='PS3_GAME':p=p.parent.parent
 elif p.name=='PS3_GAME':p=p.parent
 if not (p/'PS3_GAME/USRDIR/EBOOT.BIN').is_file():raise ValueError('请选择包含 PS3_GAME 的 AC4 游戏目录。')
 return p

def inside(root,rel):
 p=root/rel
 if not p.resolve().is_relative_to(root.resolve()):raise ValueError('拒绝修改指向游戏目录之外的链接：'+str(p))
 return p

def normal(data):
 sec,ss,rows=drb_text.parse(data);targets=[x for x in rows if x['shape']==98]
 if len(targets)!=1 or {x['shape']:x['original'] for x in rows if x['shape'] in (95,100)}!={95:'MT',100:'Next'}:raise ValueError('AC TEST 菜单结构不匹配。')
 row=targets[0]
 if row['original']=='Normal':return data
 if row['original'] not in ('NORMAL','普通'):raise ValueError('未知目标名称，拒绝覆盖：'+row['original'])
 p,size,count=sec[b'STR\0'];end=max(ss)+len(ss[max(ss)].encode('cp932'))+1
 strings=bytearray(data[p:p+end]);off=len(strings);strings+=b'Normal\0';strings+=b'\0'*(-len(strings)%16)
 out=bytearray(data);struct.pack_into('>II',out,p-12,len(strings),count+1);struct.pack_into('>I',out,row['pointer'],off)
 out=bytes(out[:p])+strings+bytes(out[p+size:]);ns,_,nr=drb_text.parse(out)
 if len(rows)!=len(nr):raise ValueError('菜单对象数变化。')
 for a,b in zip(rows,nr):
  if a['shape']!=b['shape'] or a['font']!=b['font'] or b['original']!=('Normal' if a['shape']==98 else a['original']):raise ValueError('菜单非目标文本变化。')
 for tag,(a,n,c) in sec.items():
  if tag in (b'STR\0',b'SHPR'):continue
  b,nn,cc=ns[tag]
  if (n,c)!=(nn,cc) or data[a:a+n]!=out[b:b+nn]:raise ValueError('菜单非文本区变化。')
 return bytes(out)

def normal_archive(p,reader=Path.read_bytes):
 raw=archive.unwrap(reader(p));rows=list(archive.records(raw));selected=[x for x in rows if x[1]=='menu/actest.drb']
 if len(selected)!=1:raise ValueError('菜单归档缺失唯一 actest.drb。')
 _,_,c,o,n=selected[0];chunk=raw if c==0 else archive.unwrap(reader(p.with_suffix('.%03d'%c)));old=chunk[o:o+n];new=normal(old)
 if old==new:return {}
 result=archive.repack(p,{'menu/actest.drb':new},reader)
 nt=archive.unwrap(result[p]);nr=list(archive.records(nt))
 if len(rows)!=len(nr):raise ValueError('封包成员数变化。')
 oldchunks={0:raw};newchunks={0:nt}
 for a,b in zip(rows,nr):
  _,name,cc,oo,nn=a;_,name2,cc2,oo2,nn2=b
  if (name,cc)!=(name2,cc2):raise ValueError('封包成员身份变化。')
  if cc not in oldchunks:oldchunks[cc]=archive.unwrap(reader(p.with_suffix('.%03d'%cc)))
  if cc2 not in newchunks:
   cp=p.with_suffix('.%03d'%cc2);newchunks[cc2]=archive.unwrap(result.get(cp,reader(cp)))
  before=oldchunks[cc][oo:oo+nn];after=newchunks[cc2][oo2:oo2+nn2]
  if after!=(new if name=='menu/actest.drb' else before):raise ValueError('封包非目标成员变化：'+name)
 return result

def plan(root,rpcs3=None):
 m=read_manifest();root=game_root(root);roles={'game':root};out={}
 for x in m['required_fonts']:
  p=root/x['path']
  if not p.is_file() or digest(p.read_bytes())!=x['sha256']:raise ValueError('缺少兼容的 delta.5 思源字库：'+x['path'])
 if rpcs3:
  r=Path(rpcs3).expanduser().resolve()
  roles.update(update=r/'dev_hdd0/game/BLJM60012',cache=r/'dev_hdd1/caches/BLJM60012_')
 for role,base in roles.items():
  prefix='PS3_GAME/USRDIR/' if role=='game' else 'USRDIR/' if role=='update' else ''
  e=inside(base,prefix+'EBOOT.BIN')
  if role!='cache' and e.exists():
   old=e.read_bytes();h=digest(old);row=m['eboot']
   if h!=row['target_sha256']:
    if h!=row['source_sha256']:raise ValueError('不支持的 EBOOT，未写入：'+str(e))
    out[e]=(role,prefix+'EBOOT.BIN',old,apply_delta(old,(HERE/row['patch']).read_bytes(),row['target_size'],row['target_sha256']))
  loose=inside(base,prefix+'menu/actest.drb')
  if loose.exists():
   old=loose.read_bytes();new=normal(old)
   if old!=new:out[loose]=(role,prefix+'menu/actest.drb',old,new)
  ar=inside(base,prefix+'bind/menu/actest.000')
  if ar.exists():
   for p,new in normal_archive(ar).items():
    rel=p.relative_to(base).as_posix();inside(base,rel);old=p.read_bytes()
    if old!=new:out[p]=(role,rel,old,new)
 return roles,out

def stopped():
 cmd=['tasklist','/FI','IMAGENAME eq rpcs3.exe','/NH'] if os.name=='nt' else ['pgrep','-x','rpcs3']
 try:r=subprocess.run(cmd,capture_output=True,text=True,timeout=8)
 except (FileNotFoundError,subprocess.TimeoutExpired):raise ValueError('无法自动检查模拟器进程；请关闭模拟器并确认系统进程查询工具可用。')
 active='rpcs3.exe' in r.stdout.lower() if os.name=='nt' else r.returncode==0
 if active:raise ValueError('请先正常退出 RPCS3，再安装或回退。')

def atomic(p,data):
 tmp=p.with_name(p.name+'.ac4-'+uuid.uuid4().hex+'.tmp')
 try:
  mode=p.stat().st_mode if p.exists() else 0o644
  with tmp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
  os.chmod(tmp,mode & 0o777);os.replace(tmp,p)
 finally:
  if tmp.exists():tmp.unlink()

def install(root,rpcs3=None):
 stopped();roles,changes=plan(root,rpcs3)
 if not changes:return None
 backup=roles['game']/'.ac4-cn-backups'/('20261020-loadguard-'+time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]);backup.mkdir(parents=True)
 journal={'release':read_manifest()['release'],'roots':{k:str(v) for k,v in roles.items()},'files':[],'state':'prepared'}
 for i,(p,(role,rel,old,new)) in enumerate(changes.items()):
  if p.read_bytes()!=old:raise ValueError('预检后文件变化，停止：'+str(p))
  name='%03d.original'%i;(backup/name).write_bytes(old)
  journal['files'].append(dict(role=role,path=rel,backup=name,before=digest(old),after=digest(new)))
 j=backup/'restore.json';j.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8');written=[]
 try:
  for p,(role,rel,old,new) in changes.items():
   if p.read_bytes()!=old:raise ValueError('写入前文件变化：'+str(p))
   atomic(p,new);written.append(p)
   if digest(p.read_bytes())!=digest(new):raise ValueError('写入回读不一致：'+str(p))
  journal['state']='installed';j.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8')
 except BaseException:
  for p in reversed(written):
   old,new=changes[p][2:]
   if p.read_bytes()==new:atomic(p,old)
  journal['state']='installation_failed_rollback_attempted';j.write_text(json.dumps(journal,ensure_ascii=False,indent=2),encoding='utf-8');raise
 return j

def restore(path):
 stopped();j=Path(path).expanduser().resolve();m=json.loads(j.read_text(encoding='utf-8'));changes=[]
 for row in m['files']:
  root=Path(m['roots'][row['role']]).resolve();p=inside(root,row['path']);b=inside(j.parent,row['backup']).read_bytes()
  if digest(b)!=row['before']:raise ValueError('备份校验失败：'+str(p))
  current=p.read_bytes()
  if digest(current)==row['before']:continue
  if digest(current)!=row['after']:raise ValueError('文件已被后续修改，拒绝覆盖：'+str(p))
  changes.append((p,b))
 for p,b in changes:atomic(p,b)
 m['state']='restored';j.write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8');return len(changes)

def main():
 ap=argparse.ArgumentParser(description='AC4 delta.5 增量测试包：Normal 与零件说明加载保护')
 ap.add_argument('--game');ap.add_argument('--rpcs3',help='RPCS3 数据目录；用于同步菜单缓存/更新副本')
 ap.add_argument('--apply',action='store_true');ap.add_argument('--restore');ap.add_argument('--doctor',action='store_true');a=ap.parse_args()
 if a.doctor:read_manifest();print('内置 Python 与差分载荷校验通过。');return
 if a.restore:print('已恢复文件数：',restore(a.restore));return
 if not a.game:
  print('依赖现有 delta.5 思源字库。此包为测试版，旧档菜单读档与实机尚未验收。\n1 安装增量\n2 仅预检\n3 回退\n0 退出')
  choice=input('选择：').strip()
  if choice=='0':return
  if choice=='3':print('已恢复文件数：',restore(input('restore.json 路径：').strip().strip('\"\'')));return
  if choice not in ('1','2'):raise ValueError('无效选择。')
  a.apply=choice=='1';a.game=input('游戏目录（含 PS3_GAME，可粘贴路径）：').strip().strip('\"\'')
  a.rpcs3=input('RPCS3 数据目录（可选；用于同步菜单缓存；回车跳过）：').strip().strip('\"\'') or None
 roles,changes=plan(a.game,a.rpcs3)
 for p in changes:print('待更新：',p)
 if not changes:print('所选目录已是本版。');return
 if not a.apply:print('预检通过，尚未写入。');return
 j=install(a.game,a.rpcs3);print('安装及回读校验完成。回退清单：',j)
if __name__=='__main__':
 try:main()
 except (Exception,KeyboardInterrupt) as e:print('未完成：'+str(e),file=sys.stderr);sys.exit(1)
