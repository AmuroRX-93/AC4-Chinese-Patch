"""AC4 text-only repair. Exact observed record identities; preserve all other bytes."""
import hashlib,json,struct,zlib
from pathlib import Path
MAX=64*1024*1024

def sha(b):return hashlib.sha256(b).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def load():
 p=Path(__file__).with_name('texts.json');raw=p.read_bytes()
 require(sha(raw)==p.with_suffix('.sha256').read_text().strip(),'修复数据损坏')
 return json.loads(raw)
def inflate(raw,size):
 require(0<=size<=MAX,'解压大小超出已支持范围')
 z=zlib.decompressobj();out=z.decompress(raw,size+1)
 require(len(out)==size and z.eof and not z.unused_data and not z.unconsumed_tail,'压缩数据损坏或长度不符')
 return out
def patch_param(data,name,m):
 sc=m['schemas'][name]
 require(len(data)==sc['size'] and data[:48].hex()==sc['header'],name+'：未适配的零件表结构')
 out=bytearray(data);changed=0
 for r in sc['records']:
  s=r['offset'];require(data[s:s+64].hex()==r['identity'],name+'：型号/制造商不符 '+r['model'])
  for slot in r['slots']:
   o,n=slot['offset'],slot['size'];old=data[o:o+n];target=bytes.fromhex(slot['target'])
   require(old in (bytes.fromhex(slot['original']),target),name+'：未登记文本 '+r['model']+' @'+hex(o))
   if old!=target:out[o:o+n]=target;changed+=1
 return bytes(out),changed

def binder(data):
 require(len(data)>=32 and data[:4]==b'BND3' and data[12] in (0xe0,0xe4),'未适配的 BND3')
 stride=24 if data[12]==0xe4 else 20;count=struct.unpack_from('>I',data,16)[0]
 require(0<count<=10000 and 32+count*stride<=len(data),'BND3 成员表损坏')
 end=32+count*stride;out=[];names=set();ranges=[]
 for i in range(count):
  h=32+i*stride;sz,pos,ident,np=struct.unpack_from('>4I',data,h+4)
  require(end<=pos<=len(data) and sz<=len(data)-pos and end<=np<pos,'BND3 成员范围损坏')
  ne=data.find(b'\0',np,pos);require(ne>=np,'BND3 文件名缺少结尾')
  name=data[np:ne].decode('cp932');require(name not in names,'BND3 重复成员');names.add(name)
  raw=data[pos:pos+sz];v=raw
  if data[h]&128:
   require(stride==24,'未支持压缩头');v=inflate(raw,struct.unpack_from('>I',data,h+20)[0])
  require(len(v)<=MAX,'成员过大');out.append(dict(name=name,id=ident,value=v,h=h,raw=raw,pos=pos,stride=stride))
  ranges.append((pos,pos+sz));end=max(end,ne+1)
 ranges.sort();require(all(a[1]<=b[0] for a,b in zip(ranges,ranges[1:])),'BND3 数据区重叠')
 require(end<=min(x['pos'] for x in out),'BND3 名称和数据重叠')
 return out

def pack(data,changes):
 if not changes:return data
 rows=binder(data);require(set(changes)<=set(r['name'] for r in rows),'未知替换成员')
 out=bytearray(data[:min(r['pos'] for r in rows)])
 for r in rows:
  v=changes.get(r['name'],r['value']);raw=r['raw'] if v==r['value'] else zlib.compress(v,9) if data[r['h']]&128 else v
  out.extend(b'\0'*(-len(out)%16));p=len(out);out.extend(raw)
  struct.pack_into('>II',out,r['h']+4,len(raw),p)
  if r['stride']==24:struct.pack_into('>I',out,r['h']+20,len(v))
 actual=binder(bytes(out))
 require([(r['name'],r['id'],r['value']) for r in actual]==[(r['name'],r['id'],changes.get(r['name'],r['value'])) for r in rows],'BND3 重建核对失败')
 return bytes(out)

def patch_reg(data,m):
 outer=binder(data);changes={};n=0;versions=[]
 for row in outer:
  name=row['name']
  if not name.lower().endswith('.bin'):continue
  inner=binder(row['value']);edits={};seen=set()
  for r in inner:
   key=r['name'].replace('\\','/').split('/')[-1].lower()
   if key not in m['schemas']:continue
   require(key not in seen,'规制有重复零件表');seen.add(key)
   v,c=patch_param(r['value'],key,m);n+=c
   if v!=r['value']:edits[r['name']]=v
  require(seen==set(m['schemas']),name+'：未找到完整零件/稳定器表')
  versions.append(name)
  if edits:changes[name]=pack(row['value'],edits)
 require(versions,'未找到规制表')
 return pack(data,changes),n,versions

def unwrap(data):
 rows=binder(data);require(len(rows)==1 and data[12]==0xe4 and data[32]&128,'未支持分卷头')
 return rows[0]['value']
def wrap(data,payload):
 rows=binder(data);out=pack(data,{rows[0]['name']:payload});require(unwrap(out)==payload,'分卷重建失败');return out

def records(table):
 require(len(table)>=80,'分卷索引不完整');count=struct.unpack_from('>I',table)[0]
 require(0<count<=10000 and 80+80*count<=len(table),'分卷索引损坏');out=[]
 for i in range(count):
  h=80+i*80;name=table[h:h+64].split(b'\0')[0].decode('cp932').replace('\\','/')
  c,p,blocks,size=struct.unpack_from('>4I',table,h+64)
  require(c<1000 and blocks*16>=size and size<=MAX,'分卷记录越界')
  out.append((h,name,c,p*16,size))
 return out

def app_plan(root,m,read):
 table=unwrap(read(root/'bind/app.000'));rows=records(table);raw={};chunks={0:table}
 def chunk(c):
  if c not in chunks:
   raw[c]=read(root/f'bind/app.{c:03d}');chunks[c]=unwrap(raw[c])
  return chunks[c]
 def member(r):
  h,name,c,p,s=r;b=chunk(c);require(p+s<=len(b),name+' 分卷截断');return b[p:p+s]
 for name in ['font/ac4_j1/ac4_j1.ccm','font/ac4_e5/ac4_e5.ccm']:
  rr=[r for r in rows if r[1]==name];require(rr and all(sha(member(r))==m['font_sha256'] for r in rr),'归档中文字码表不符：'+name)
 rr=[r for r in rows if r[1]=='param/regulation.bin'];require(len(rr)==1,'规制归档路径不唯一')
 r=rr[0];old=member(r);new,count,versions=patch_reg(old,m)
 if new==old:return {},count,versions
 h,name,c,pos,size=r;payload=bytearray(chunk(c));payload.extend(b'\0'*(-len(payload)%16));np=len(payload);payload.extend(new);payload.extend(b'\0'*(-len(payload)%16))
 newtable=bytearray(payload if c==0 else table);struct.pack_into('>4I',newtable,h+64,c,np//16,(len(new)+15)//16,len(new))
 amended={c:bytes(payload),0:bytes(newtable)}
 newrows=records(amended[0]);require(len(newrows)==len(rows),'成员数量变化')
 for a,b in zip(rows,newrows):
  require(a[1:3]==b[1:3],'成员身份变化');_,bn,bc,bp,bs=b
  after=amended.get(bc,chunks.get(bc))
  if after is None:require(a==b,'未载入成员索引变化');continue
  expected=new if bn=='param/regulation.bin' else member(a)
  require(after[bp:bp+bs]==expected,'非目标成员变化：'+bn)
 return {root/f'bind/app.{c:03d}':wrap(read(root/f'bind/app.{c:03d}'),v) for c,v in amended.items()},count,versions
