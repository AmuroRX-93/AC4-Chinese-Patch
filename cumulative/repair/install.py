"""Companion for the integrated AC4 build; never reads or changes savedata."""
from pathlib import Path
import argparse,json,os,shutil,sys,time,uuid
import core,engine as e
HERE=Path(__file__).resolve().parent

def read(p):
 e.require(p.is_file() and p.stat().st_size<=e.MAX,'文件缺失或超出支持范围：'+str(p))
 return p.read_bytes()
def tree(p):
 result={}
 for f in sorted(p.rglob('*')):
  e.require(not f.is_symlink(),'缓存含符号链接，停止：'+str(f))
  if f.is_file():result[f.relative_to(p).as_posix()]=dict(size=f.stat().st_size,sha256=core.digest(f))
 return result

def plan(game,hdd0,hdd1):
 m=e.load();game=core.game_root(game);core.check_game(game,dict(game='BLJM60012',version='01.05'))
 e.require(not (game/'.ac4-textrepair.lock').exists(),'上次修复中断，请先按 .ac4-textrepair.lock 中的备份路径恢复')
 hdd0=Path(hdd0).expanduser().resolve();hdd1=Path(hdd1).expanduser().resolve()
 e.require(hdd0.is_dir() and hdd1.is_dir(),'必须选择实际使用的 dev_hdd0 和 dev_hdd1 目录')
 u=core.safe(game,'PS3_GAME/USRDIR');roots={'base':game};changes=[];payloads={};observed={};report=[]
 def checked(p):
  b=read(p);observed[str(p)]=e.sha(b);return b
 def add(p,v,scope):
  old=checked(p)
  if old==v:return
  rel=p.relative_to(roots[scope]).as_posix();r=dict(path=rel,size=len(v),sha256=e.sha(v))
  changes.append(dict(scope=scope,row=r,old_sha256=e.sha(old),old_size=len(old)))
  payloads[r['sha256']]=v
 for name in ['font/ac4_j1/ac4_j1.ccm','font/ac4_e5/ac4_e5.ccm']:
  e.require(e.sha(checked(core.safe(u,name)))==m['font_sha256'],'需要本项目 delta.3 / 思源黑体字库，请使用整合包内游戏：'+name)
 for key in m['schemas']:
  p=core.safe(u,'param/'+key);v,n=e.patch_param(checked(p),key,m);add(p,v,'base');report.append(f'本体 {key}: {n} 个文本槽需更新')
 p=core.safe(u,'param/regulation.bin');v,n,vers=e.patch_reg(checked(p),m);add(p,v,'base');report.append(f'本体规制 {vers}: {n} 个文本槽需更新')
 files,n,vers=e.app_plan(u,m,checked)
 for p,v in files.items():add(p,v,'base')
 report.append(f'本体归档规制 {vers}: {n} 个文本槽需更新')
 update=core.safe(hdd0,'game/BLJM60012')
 if update.exists():
  meta=core.sfo(core.safe(update,'PARAM.SFO'))
  e.require(meta.get('TITLE_ID')=='BLJM60012' and meta.get('CATEGORY')=='GD','更新目录游戏编号/类型不符')
  ud=core.safe(update,'USRDIR');e.require(ud.is_dir(),'更新目录缺少 USRDIR')
  e.require({x.name for x in ud.iterdir()}=={'regulation.bin'},'更新目录含未适配的覆盖资源，未修改文件：'+str(ud))
  roots['update']=update;p=core.safe(update,'USRDIR/regulation.bin');v,n,vers=e.patch_reg(checked(p),m);add(p,v,'update');report.append(f'已安装更新规制 {vers}: {n} 个文本槽需更新；保留数值')
 else:report.append('已核对：此 dev_hdd0 没有 AC4 更新目录；不创建/安装更新')
 cache=core.safe(hdd1,'caches/BLJM60012_');cache_files=tree(cache) if cache.is_dir() else None
 e.require(not cache.exists() or cache.is_dir(),'缓存路径不是目录')
 for p in roots.values():e.require(not (p/core.LOCK).exists(),'有未恢复安装，请先使用备份恢复：'+str(p/core.LOCK))
 report.append('AC4 安装缓存将移到备份，下一次冷启动重新生成' if cache_files is not None else '未发现 AC4 安装缓存，无需处理')
 return dict(m=m,roots=roots,changes=changes,payloads=payloads,observed=observed,cache=cache,cache_files=cache_files,report=report)

def restore(backup):
 backup=Path(backup).resolve();core.ensure_closed()
 if not (backup/'repair.json').is_file():return core.restore(backup)
 j=json.loads((backup/'repair.json').read_text());e.require(j['format']=='ac4-text-repair-1','不支持此备份')
 if j['state']=='restored':print('此备份已恢复');return
 c=j.get('cache');relocated=False;fresh=None
 if c:
  src=Path(c['path']);dst=Path(c['backup'])
  if dst.exists():
   e.require(tree(dst)==c['files'],'缓存备份校验失败')
   if src.exists():
    fresh=src.parent.parent/'AC4_TextRepair_Backups'/('after-repair-'+uuid.uuid4().hex)
    fresh.parent.mkdir(parents=True,exist_ok=True)
    j['cache_created_since_install']=str(fresh);core.write_json(backup/'repair.json',j)
    os.replace(src,fresh)
   os.replace(dst,src);relocated=True
  else:e.require(src.is_dir() and tree(src)==c['files'],'缓存原件及备份状态不符')
 try:
  if j.get('resource_backup'):core.restore(Path(j['resource_backup']))
 except BaseException:
  if relocated:
   os.replace(src,dst)
   if fresh:os.replace(fresh,src)
  raise
 j['state']='restored';core.write_json(backup/'repair.json',j)
 lp=backup.parent.parent/'.ac4-textrepair.lock'
 if lp.exists() and json.loads(lp.read_text()).get('backup')==str(backup):lp.unlink()
 print('已恢复本次修改；存档未改动。')

def _apply(p):
 core.ensure_closed()
 if not p['changes'] and p['cache_files'] is None:print('所有已检查资源均已汉化，没有旧缓存需要处理。');return None
 for name,h in p['observed'].items():e.require(core.digest(Path(name))==h,'预检后文件变化：'+name)
 if p['cache_files'] is not None:e.require(tree(p['cache'])==p['cache_files'],'预检后缓存变化')
 ident=time.strftime('%Y%m%d-%H%M%S-')+uuid.uuid4().hex[:8]
 b=core.safe(p['roots']['base'],'AC4_TextRepair_Backups/'+ident);b.mkdir(parents=True)
 j=dict(format='ac4-text-repair-1',release=p['m']['release'],state='preparing',resource_backup=None,cache=None,report=p['report'])
 if p['cache_files'] is not None:
  dest=core.safe(p['cache'].parent.parent,'AC4_TextRepair_Backups/'+ident+'/BLJM60012_')
  j['cache']=dict(path=str(p['cache']),backup=str(dest),files=p['cache_files'])
 core.write_json(b/'repair.json',j)
 core.write_json(p['roots']['base']/'.ac4-textrepair.lock',{'backup':str(b)})
 old_prepare=core.prepare
 def prepare(package,source,dst,row):
  dst.parent.mkdir(parents=True,exist_ok=True)
  with dst.open('xb') as f:f.write(p['payloads'][row['sha256']]);f.flush();os.fsync(f.fileno())
  shutil.copymode(source,dst);e.require(core.digest(dst)==row['sha256'],'准备输出校验失败')
 try:
  core.prepare=prepare
  def on_backup(rb):
   j['resource_backup']=str(rb);core.write_json(b/'repair.json',j)
  rb=core.apply(HERE,p['m'],p['roots'],p['changes'],on_backup=on_backup);j['resource_backup']=str(rb) if rb else None
  j['state']='resources-installed';core.write_json(b/'repair.json',j)
  core.ensure_closed()
  if j['cache']:
   e.require(tree(p['cache'])==p['cache_files'],'安装期间缓存变化，正在恢复资源')
   dest.parent.mkdir(parents=True,exist_ok=True);j['state']='moving-cache';core.write_json(b/'repair.json',j);os.replace(p['cache'],dest)
   e.require(tree(dest)==p['cache_files'],'缓存备份校验失败')
  j['state']='installed';core.write_json(b/'repair.json',j)
 except BaseException:
  if j.get('resource_backup') or (j.get('cache') and Path(j['cache']['backup']).exists()):restore(b)
  raise
 finally:core.prepare=old_prepare
 print('实验性修复完成。恢复入口所需备份目录：\n'+str(b));return b

def apply(p):
 lock=p['roots']['base']/'.ac4-textrepair.lock'
 with lock.open('x') as f:json.dump({'backup':None},f)
 try:return _apply(p)
 finally:
  if lock.exists():lock.unlink()

def path_input(prompt,default=None):
 print(prompt)
 if default:print('默认：'+str(default))
 text=input('路径：').strip().strip('"\'')
 e.require(text or default,'未提供路径，未修改文件');return Path(text).expanduser() if text else Path(default)

def main():
 ap=argparse.ArgumentParser(description='AC4 本体/更新规制零件说明实验性修复（不改存档）')
 ap.add_argument('--game',type=Path);ap.add_argument('--rpcs3',type=Path,help='含 dev_hdd0/dev_hdd1 的实际 RPCS3 数据目录')
 ap.add_argument('--hdd0',type=Path);ap.add_argument('--hdd1',type=Path)
 ap.add_argument('--check-only',action='store_true');ap.add_argument('--restore',type=Path);ap.add_argument('--install',action='store_true')
 a=ap.parse_args()
 if a.restore:restore(a.restore);return
 if not a.game:
  print('AC4 实验性规制说明修复\n1 检查并修复\n2 只检查\n3 恢复\n导入老存档前务必备份；本工具不修改存档。')
  mode=input('选择 1/2/3：').strip()
  if mode=='3':restore(path_input('选择含 repair.json 或 restore.json 的备份目录'));return
  e.require(mode in ('1','2'),'未选择操作');a.check_only=mode=='2'
  default=HERE.parent/'游戏/AC4_BLJM60012'
  a.game=default if default.is_dir() else path_input('选择含 PS3_GAME 的游戏目录')
 if not (a.hdd0 and a.hdd1):
  if not a.rpcs3:
   default=Path.home()/'Library/Application Support/rpcs3' if sys.platform=='darwin' else None
   a.rpcs3=path_input('选择正在使用的 RPCS3 数据目录（含 dev_hdd0、dev_hdd1）。Windows 通常是 rpcs3.exe 所在目录。',default)
  a.hdd0=a.hdd0 or a.rpcs3/'dev_hdd0';a.hdd1=a.hdd1 or a.rpcs3/'dev_hdd1'
  # Custom VFS mappings need explicit roots; never silently patch a stale default directory.
  vf=a.rpcs3/'vfs.yml'
  if vf.is_file():
   lines=vf.read_text(errors='replace').splitlines()
   for key in ('/dev_hdd0/','/dev_hdd1/'):
    for line in lines:
     if line.lstrip().startswith(key+':'):
      value=line.split(':',1)[1].strip().strip('"\'')
      e.require(value in ('', '""', "''", '$(EmulatorDir)'+key[1:]),'检测到自定义虚拟磁盘映射，请用 --hdd0 和 --hdd1 明确指定实际目录')
 p=plan(a.game,a.hdd0,a.hdd1)
 print('\n'.join(p['report']));print('需要改写文件：',len(p['changes']))
 if a.check_only:print('只读检查完成');return
 if not a.install:
  if input('这是实验性修改。确认已退出 RPCS3 并保留存档备份后，输入 y 安装：').strip().lower()!='y':return
 apply(p)
if __name__=='__main__':
 try:main()
 except (Exception,KeyboardInterrupt) as ex:print('\n未完成：'+str(ex),file=sys.stderr);sys.exit(1)
