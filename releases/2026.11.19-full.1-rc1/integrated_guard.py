"""Compose the load guard with cumulative deltas before the existing single transaction."""
from pathlib import Path
import json
from loadguard import hotfix as h
HERE=Path(__file__).resolve().parent

def compatible_menu(rel,data):
 rows=json.loads((HERE/'loadguard/menu-compatible.json').read_text())
 return h.digest(data) in rows.get(rel,[])

def accepted_executable(rel,data):
 m=h.read_manifest()['eboot']
 return rel=='PS3_GAME/USRDIR/EBOOT.BIN' and len(data)==m['target_size'] and h.digest(data)==m['target_sha256']

def stage(game,overlay,observe):
 def read(p):
  original=observe(p)
  return overlay.get(p,original)
 m=h.read_manifest()
 for f in m['required_fonts']:
  if h.digest(read(game/f['path']))!=f['sha256']:raise ValueError('累计字库与加载保护不兼容：'+f['path'])
 ep=game/'PS3_GAME/USRDIR/EBOOT.BIN';old=read(ep);r=m['eboot']
 if h.digest(old)!=r['target_sha256']:
  if h.digest(old)!=r['source_sha256']:raise ValueError('未知程序，拒绝安装。')
  overlay[ep]=h.apply_delta(old,(h.HERE/r['patch']).read_bytes(),r['target_size'],r['target_sha256'])
 p=game/'PS3_GAME/USRDIR/menu/actest.drb';overlay[p]=h.normal(read(p))
 p=game/'PS3_GAME/USRDIR/bind/menu/actest.000'
 overlay.update(h.normal_archive(p,read))
