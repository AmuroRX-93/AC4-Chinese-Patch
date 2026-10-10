"""Plan all cumulative resource deltas and regulation repairs before a single commit."""
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'repair'))
import core,engine as e
from repair import install as repair
from delta import apply as decode_delta
RELEASE='2026.10.01-delta.5'
import finale_patch as finale

def transform(package,old,row):
 if len(old)==row['size'] and e.sha(old)==row['sha256']:return old
 variants=[row]+row.get('alternatives',[])
 v=next((v for v in variants if len(old)==v['original_size'] and e.sha(old)==v['original_sha256']),None)
 e.require(v is not None,'资源版本未登记，未修改文件：'+row['path'])
 r=dict(row,**{k:v[k] for k in ('original_size','original_sha256','segments')})
 prefix=v.get('prefix_size',r.get('prefix_size',0));e.require(0<=prefix<=len(old),'差分前缀越界')
 out=bytearray(old[:prefix])
 for seg in r['segments']:
  pos,size=seg['old_offset'],seg['old_size'];pad=seg['output_offset']-len(out)
  e.require(0<=pos<=len(old) and 0<=size<=len(old)-pos and 0<=pad<=15,'差分范围不正确')
  patch=core.safe(package,seg['payload']).read_bytes()
  e.require(len(patch)==seg['patch_size'] and e.sha(patch)==seg['patch_sha256'],'差分文件损坏')
  out.extend(b'\0'*pad);out.extend(decode_delta(old[pos:pos+size],patch,seg['size'],seg['sha256']))
 e.require(len(out)==row['size'] and e.sha(out)==row['sha256'],'累计差分重建校验失败')
 return bytes(out)

def plan(game,hdd0,hdd1):
 game=core.game_root(game);hdd0=Path(hdd0).expanduser().resolve();hdd1=Path(hdd1).expanduser().resolve()
 bm=core.load(HERE/'base');fm=core.load(HERE/'font');core.check_game(game,bm)
 ff=finale.load(HERE/'finale');final={r['path']:r for r in ff['files']}
 e.require(hdd0.is_dir() and hdd1.is_dir(),'需要实际使用的 dev_hdd0、dev_hdd1 目录')
 for package,m in [(HERE/'base',bm),(HERE/'font',fm)]:core.payload_check(package,m)
 font={r['path']:r for r in fm['base']};overlay={};before={};old_read=repair.read
 def resource_read(p):
  rel=p.relative_to(game).as_posix() if p.is_relative_to(game) else None
  return finale.read_large(p,final[rel]) if rel in final and final[rel]['kind']=='movie_sectors' else old_read(p)
 def observed(p):
  data=resource_read(p);before[str(p)]=e.sha(data);return data
 for r in bm['unchanged']:
  p=core.safe(game,r['path']);data=observed(p)
  e.require(len(data)==r['size'] and e.sha(data)==r['sha256'],'原版程序/版本不符：'+r['path'])
 for i,row in enumerate(bm['base']):
  p=core.safe(game,row['path']);old=observed(p);fr=font.get(row['path'])
  if row['path'] in final and finale.is_target(old,final[row['path']]):new=old
  elif fr and len(old)==fr['size'] and e.sha(old)==fr['sha256']:new=old
  else:
   new=transform(HERE/'base',old,row)
   if fr:new=transform(HERE/'font',new,fr)
  if old!=new:overlay[p]=new
  if (i+1)%50==0:print('累计资源预检：',i+1,'/',len(bm['base']),flush=True)
 e.require(set(font)<=set(r['path'] for r in bm['base']),'字体清单出现未纳入的资源')
 for row in ff['files']:
  path=core.safe(game,row['path']);old=observed(path)
  new=finale.transform(HERE/'finale',overlay.get(path,old),row)
  if new!=old:overlay[path]=new
 update=core.safe(hdd0,'game/BLJM60012')
 if update.is_dir():
  for row in bm['update']:
   p=core.safe(update,row['path']);old=observed(p)
   known=any(len(old)==v['original_size'] and e.sha(old)==v['original_sha256'] for v in [row]+row.get('alternatives',[]))
   if known:overlay[p]=transform(HERE/'base',old,row)
 # The repair planner sees the staged final bytes, but keeps all roots pointing to actual files.
 def projected(p):return overlay[p] if p in overlay else old_read(p)
 try:
  repair.read=projected;p=repair.plan(game,hdd0,hdd1)
 finally:repair.read=old_read
 for change in p['changes']:
  path=core.safe(p['roots'][change['scope']],change['row']['path'])
  overlay[path]=p['payloads'][change['row']['sha256']]
 # Rebuild the one transaction against original on-disk bytes, never intermediate hashes.
 before.update({name:h for name,h in p['observed'].items() if name not in before})
 changes=[];payloads={}
 for path,new in overlay.items():
  old=resource_read(path);e.require(e.sha(old)==before[str(path)],'预检期间文件变化：'+str(path))
  if old==new:continue
  scope='base' if path.is_relative_to(game) else 'update';r=dict(path=path.relative_to(p['roots'][scope]).as_posix(),size=len(new),sha256=e.sha(new))
  changes.append(dict(scope=scope,row=r,old_sha256=e.sha(old),old_size=len(old)));payloads[r['sha256']]=new
 p.update(changes=changes,payloads=payloads,observed=before)
 p['m']=dict(p['m'],release=RELEASE)
 p['report']=['游戏目录：'+str(game),'实际 dev_hdd0：'+str(hdd0),'实际 dev_hdd1：'+str(hdd1),'累计汉化、思源黑体、最终关和片尾预检完成；全部资源统一提交。']+p['report']
 return p
