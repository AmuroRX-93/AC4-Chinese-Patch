"""Validated AC4 finale resources, applied in the cumulative backup transaction."""
from pathlib import Path
import base64,gzip,hashlib,json
sha=lambda data:hashlib.sha256(data).hexdigest()
def require(ok,message):
 if not ok:raise ValueError(message)
def load(package):
 raw=(package/'manifest.json').read_bytes()
 require(sha(raw)==(package/'manifest.sha256').read_text().strip(),'结尾修复清单损坏')
 m=json.loads(raw);require(m['format']=='ac4-finale-1','未知结尾修复格式')
 paths=set()
 for r in m['files']:
  require(r['path'] not in paths,'修复路径重复');paths.add(r['path'])
  require(Path(r['payload']).name==r['payload'],'补丁路径不正确')
  packed=(package/r['payload']).read_bytes()
  require(len(packed)==r['patch_size'] and sha(packed)==r['patch_sha256'],'结尾差分损坏：'+r['path'])
 return m
def is_target(data,row):return len(data)==row['size'] and sha(data)==row['sha256']
def read_large(path,row):
 # Extend the resource reader only for this exact known movie, not arbitrary files.
 require(row['kind']=='movie_sectors' and row['path']=='PS3_GAME/USRDIR/movie/staff roll.pam' and row['size']==712337408,'影片范围未登记')
 require(path.is_file() and path.stat().st_size==row['size'],'片尾影片缺失或大小不符')
 return path.read_bytes()
def transform(package,old,row):
 if is_target(old,row):return old
 require(len(old)==row['original_size'] and sha(old)==row['original_sha256'],'结尾资源版本未登记，未修改文件：'+row['path'])
 packed=(package/row['payload']).read_bytes()
 require(len(packed)==row['patch_size'] and sha(packed)==row['patch_sha256'],'结尾差分损坏')
 raw=gzip.decompress(packed)
 if row['kind']=='resource':out=raw
 else:
  require(row['kind']=='movie_sectors' and row['size']==len(old),'未知结尾差分格式')
  edits=json.loads(raw);out=bytearray(old);end=0
  for edit in edits:
   offset=edit['offset'];before=base64.b64decode(edit['old'],validate=True);after=base64.b64decode(edit['new'],validate=True)
   require(isinstance(offset,int) and before and len(before)==len(after) and offset>=end and offset+len(before)<=len(old),'影片差分越界或重叠')
   require(old[offset:offset+len(before)]==before,'影片原字节校验失败')
   out[offset:offset+len(after)]=after;end=offset+len(before)
  out=bytes(out)
 require(is_target(out,row),'结尾资源重建校验失败')
 return out
