"""AC4 CP932 DRB literal text; keep control identifiers and all old offsets intact."""
import struct

def parse(d):
 assert d[:4]==b'\0BRD'
 sec={};p=0
 while p<len(d):
  tag=d[p:p+4][::-1];sz,n,z=struct.unpack_from('>III',d,p+4);assert z==0
  sec[tag]=(p+16,sz,n);p+=16+sz
 assert p==len(d)
 p,sz,n=sec[b'STR\0'];ss={};o=0
 for _ in range(n):
  e=d.index(0,p+o);ss[o]=d[p+o:e].decode('cp932');o=e-p+1
 p,sz,n=sec[b'SHAP'];q=sec[b'SHPR'][0];rows=[]
 for i in range(n):
  t,o=struct.unpack_from('>II',d,p+i*8)
  if ss[t] in ('Text','ScrollText') and d[q+o+23]==0:
   off=struct.unpack_from('>I',d,q+o+28)[0]
   rows.append(dict(shape=i,original=ss[off],pointer=q+o+28,font=struct.unpack_from('>h',d,q+o+20)[0]))
 return sec,ss,rows

def patch(d,translations,encode):
 sec,ss,rows=parse(d);p,sz,n=sec[b'STR\0'];newstr=bytearray(d[p:p+sz]);b=bytearray(d);added={};changes=[]
 # Strip only padding after last declared string, then append translations.
 end=max(ss);end+=len(ss[end].encode('cp932'))+1;newstr=newstr[:end]
 for r in rows:
  s=r['original'];tr=translations.get(s)
  if not tr or tr==s:continue
  if tr not in added:added[tr]=len(newstr);newstr.extend(encode(tr)+b'\0')
  struct.pack_into('>I',b,r['pointer'],added[tr]);changes.append(r['shape'])
 newstr.extend(b'\0'*(-len(newstr)%16))
 struct.pack_into('>II',b,p-12,len(newstr),n+len(added))
 out=bytes(b[:p])+newstr+bytes(b[p+sz:]);ns,nss,nr=parse(out)
 assert len(rows)==len(nr)
 for a,z in zip(rows,nr):
  expected=encode(translations[a['original']]).decode('cp932') if a['shape'] in changes else a['original']
  assert z['original']==expected and z['font']==a['font']
 # All other sections byte-identical except explicitly patched SHPR pointers.
 for tag,(a,ln,cnt) in sec.items():
  if tag in (b'STR\0',b'SHPR'):continue
  z,zln,zcnt=ns[tag];assert (ln,cnt)==(zln,zcnt) and d[a:a+ln]==out[z:z+ln]
 return out,len(changes)
