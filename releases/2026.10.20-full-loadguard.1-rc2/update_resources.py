"""Recognize update overlays by path and content; never delete unknown game data."""
from pathlib import Path
import os
from loadguard import hotfix as h
import engine as e

def inventory(root):
 result={}
 for directory,dirs,files in os.walk(root,followlinks=False):
  for name in dirs+files:
   p=Path(directory)/name
   e.require(not p.is_symlink(),'更新目录含链接，未修改：'+str(p))
  for name in files:
   p=Path(directory)/name;key=p.relative_to(root).as_posix().casefold()
   e.require(key not in result,'更新目录存在大小写重复文件：'+key)
   result[key]=p
 return result

def plan(root,game,bm,fm,ff,schema,observe,transform,finale,guard):
 paths=inventory(root);staged={};notes=[];processed=set();ignored=0
 prefix='PS3_GAME/USRDIR/'
 base={r['path'][len(prefix):].casefold():r for r in bm['base'] if r['path'].startswith(prefix)}
 font={r['path'][len(prefix):].casefold():r for r in fm['base'] if r['path'].startswith(prefix)}
 finals={r['path'][len(prefix):].casefold():r for r in ff['files'] if r['path'].startswith(prefix)}
 package=Path(__file__).resolve().parent
 def key(p):return p.relative_to(root).as_posix().casefold()
 def physical(p):
  k=key(p);e.require(k in paths,'更新归档缺少配套分卷，未修改：'+k);return paths[k]
 def read(p):
  actual=physical(p)
  if actual in staged:return staged[actual]
  return observe(actual)
 def put(p,new):
  actual=physical(p);old=observe(actual)
  if old!=new:staged[actual]=new
  processed.add(key(actual))
 for k,p in sorted(paths.items()):
  if k=='eboot.bin':
   old=observe(p);r=h.read_manifest()['eboot'];sha=h.digest(old)
   if sha==r['target_sha256']:new=old
   else:
    e.require(sha==r['source_sha256'],'更新程序版本未知，保留全部文件并停止；EBOOT.BIN SHA256='+sha)
    new=h.apply_delta(old,(h.HERE/r['patch']).read_bytes(),r['target_size'],r['target_sha256'])
   put(p,new)
  elif k in ('regulation.bin','param/regulation.bin'):
   old=observe(p);new=old
   for row in bm['update']:
    if row['path'].casefold()=='usrdir/regulation.bin':
     if any(len(old)==v['original_size'] and e.sha(old)==v['original_sha256'] for v in [row]+row.get('alternatives',[])):
      new=transform(package/'base',old,row)
   new,n,versions=e.patch_reg(new,schema);put(p,new);notes.append('更新规制 '+str(p.relative_to(root))+': '+str(n)+' 个文本槽修复，数值保留')
  elif k in base:
   row=base[k];old=observe(p);fr=font.get(k)
   if guard.compatible_menu(row['path'],old):new=old
   elif k in finals and finale.is_target(old,finals[k]):new=old
   elif fr and len(old)==fr['size'] and e.sha(old)==fr['sha256']:new=old
   else:
    new=transform(package/'base',old,row)
    if fr:new=transform(package/'font',new,fr)
   if k in finals:new=finale.transform(package/'finale',new,finals[k])
   put(p,new)
  elif k.startswith('param/') and k.split('/')[-1] in schema['schemas']:
   new,n=e.patch_param(observe(p),k.split('/')[-1],schema);put(p,new)
  elif k in finals:
   put(p,finale.transform(package/'finale',observe(p),finals[k]))
  else:
   # Preserve OS metadata and human-readable sidecars; do not treat arbitrary BIN/SELF as harmless.
   name=p.name.casefold()
   if name in ('.ds_store','desktop.ini','thumbs.db') or name.startswith('._') or p.suffix.casefold() in ('.txt','.md','.log','.bak'):
    ignored+=1;continue
   counterpart=game/'PS3_GAME/USRDIR'/p.relative_to(root)
   if counterpart.is_file() and observe(p)==observe(counterpart):processed.add(k);continue
   raise ValueError('更新中有尚未识别的覆盖资源，未修改任何文件：'+str(p.relative_to(root))+'；SHA256='+e.sha(observe(p)))
 # Fix nested raw parameter tables after their cumulative deltas have been composed.
 for k in list(processed):
  if k.startswith('param/') and k.split('/')[-1] in schema['schemas']:
   p=paths[k];new,n=e.patch_param(read(p),k.split('/')[-1],schema);put(p,new)
 if any(k.startswith('bind/app.') for k in paths):
  e.require('bind/app.000' in paths,'更新归档缺少 app.000，未修改')
  edits,n,vers=e.app_plan(root,schema,read)
  for p,new in edits.items():put(p,new)
 if 'menu/actest.drb' in paths:
  p=paths['menu/actest.drb'];put(p,h.normal(read(p)))
 if 'bind/menu/actest.000' in paths:
  for p,new in h.normal_archive(root/'bind/menu/actest.000',read).items():put(p,new)
 notes.append('更新目录自动识别 '+str(len(processed))+' 个资源，保留 '+str(ignored)+' 个附属文件；支持文件名大小写差异')
 return staged,notes
