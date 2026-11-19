"""Reviewed UI/title/parameter-label deltas, composed into the cumulative transaction."""
from pathlib import Path
import json,hashlib,struct
from loadguard import archive,delta
import engine as e
HERE=Path(__file__).resolve().parent
PREFIX='PS3_GAME/USRDIR/'
def digest(data):return hashlib.sha256(data).hexdigest()
def manifest():return json.loads((HERE/'latest/manifest.json').read_text())
def transform(row,data):
 if digest(data)==row['sha256']:return data
 if digest(data) not in row['accepted_sha256']:raise ValueError('最新文字/贴图输入未登记：'+row['path'])
 patch=(HERE/'latest'/row['patch']).read_bytes()
 if digest(patch)!=row['patch_sha256']:raise ValueError('最新差分损坏：'+row['path'])
 return delta.apply(data,patch,row['size'],row['sha256'])
def accepted(rel,data,read):
 m=manifest()
 for r in m['files']:
  if r['path']==rel:return digest(data)==r['sha256']
 spec=next((s for s in m['archives'] if rel in s['parts']),None)
 if spec is None:return False
 def get(p):return data if p==rel else read(p)
 try:
  table=archive.unwrap(get(spec['index']));rows=list(archive.records(table));expected=spec['members']
  if len(rows)!=len(expected):return False
  cache={0:table};schema=None
  for _,name,chunk,pos,size in rows:
   if name not in expected:return False
   if chunk not in cache:cache[chunk]=archive.unwrap(get(str(Path(spec['index']).with_suffix('.%03d'%chunk))))
   value=cache[chunk][pos:pos+size]
   if len(value)!=size:return False
   if digest(value)==expected[name]:continue
   if spec['index']==PREFIX+'bind/app.000':
    if schema is None:schema=e.load()
    if name=='param/regulation.bin':e.patch_reg(value,schema);continue
    if name.startswith('param/') and name.split('/')[-1] in schema['schemas']:e.patch_param(value,name.split('/')[-1],schema);continue
   return False
  return True
 except (ValueError,AssertionError,KeyError,FileNotFoundError):return False

def rewrite_archive(index,replacements,read):
 raw={0:read(index)};chunks={0:bytearray(archive.unwrap(raw[0]))};changed=set();found=set()
 original_records=list(archive.records(chunks[0]))
 for off,name,c,pos,n in original_records:
  if name not in replacements:continue
  found.add(name)
  if c not in chunks:raw[c]=read(index.with_suffix('.%03d'%c));chunks[c]=bytearray(archive.unwrap(raw[c]))
  value=replacements[name]
  if bytes(chunks[c][pos:pos+n])==value:continue
  if len(value)==n:chunks[c][pos:pos+n]=value
  else:
   chunks[c].extend(b'\0'*(-len(chunks[c])%16));pos=len(chunks[c]);chunks[c].extend(value);chunks[c].extend(b'\0'*(-len(chunks[c])%16));struct.pack_into('>4I',chunks[0],off+64,c,pos//16,(len(value)+15)//16,len(value));changed.add(0)
  changed.add(c)
 if found!=set(replacements):raise ValueError('归档缺少目标成员：'+str(set(replacements)-found))
 # Compare every untouched member, including ones in modified chunks.
 originals={0:archive.unwrap(raw[0])}
 for a,b in zip(original_records,list(archive.records(chunks[0]))):
  if a[1]!=b[1]:raise ValueError('归档成员身份变化')
  _,name,ac,ap,an=a;_,_,bc,bp,bn=b
  if ac not in originals:originals[ac]=archive.unwrap(raw.get(ac) or read(index.with_suffix('.%03d'%ac)))
  if bc not in chunks:chunks[bc]=bytearray(originals[bc] if bc in originals else archive.unwrap(read(index.with_suffix('.%03d'%bc))))
  expected=replacements.get(name,originals[ac][ap:ap+an])
  if bytes(chunks[bc][bp:bp+bn])!=expected:raise ValueError('归档成员校验失败：'+name)
 return {index.with_suffix('.%03d'%c):archive.wrap(raw[c],chunks[c]) for c in changed}

def stage(game,overlay,observe,update_root=None):
 m=manifest();rows=m['files']
 def read(p):
  original=observe(p);return overlay.get(p,original)
 for r in rows:
  p=game/r['path'];overlay[p]=transform(r,read(p))
 groups={}
 for r in rows:
  name=r['path'][len(PREFIX):]
  if name.startswith('menu/'):index='bind/menu/'+Path(name).stem+'.000'
  elif name.startswith('garage/'):index='bind/init.000'
  else:index='bind/app.000'
  groups.setdefault(index,{})[name]=read(game/r['path'])
 for index,replacements in groups.items():overlay.update(rewrite_archive(game/PREFIX/index,replacements,read))
 if update_root is not None and update_root.is_dir():
  import update_resources
  paths=update_resources.inventory(update_root)
  for r in rows:
   name=r['path'][len(PREFIX):];p=paths.get(name.casefold())
   if p is not None:overlay[p]=transform(r,read(p))
  def uread(p):
   key=p.relative_to(update_root).as_posix().casefold()
   if key not in paths:raise ValueError('更新归档缺少分卷：'+key)
   return read(paths[key])
  for index,replacements in groups.items():
   if index.casefold() not in paths:continue
   for p,v in rewrite_archive(update_root/index,replacements,uread).items():overlay[paths[p.relative_to(update_root).as_posix().casefold()]]=v
