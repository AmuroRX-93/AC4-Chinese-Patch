from pathlib import Path
import argparse,sys
import cumulative
from cumulative import e,core,repair,plan
HERE=Path(__file__).resolve().parent
restore=repair.restore
apply=repair.apply
path_input=repair.path_input

def main():
 ap=argparse.ArgumentParser(description='AC4 累计汉化 delta.4：思源黑体与实验性规制修复')
 ap.add_argument('--game',type=Path);ap.add_argument('--rpcs3',type=Path,help='含 dev_hdd0/dev_hdd1 的实际 RPCS3 数据目录')
 ap.add_argument('--hdd0',type=Path);ap.add_argument('--hdd1',type=Path)
 ap.add_argument('--check-only',action='store_true');ap.add_argument('--restore',type=Path);ap.add_argument('--install',action='store_true')
 a=ap.parse_args()
 if a.restore:restore(a.restore);return
 if not a.game:
  print('AC4 累计汉化 delta.4\n1 安装汉化及修复\n2 只检查\n3 恢复\n导入老存档前务必备份；本工具不修改存档。')
  mode=input('选择 1/2/3：').strip()
  if mode=='3':restore(path_input('选择含 repair.json 或 restore.json 的备份目录'));return
  e.require(mode in ('1','2'),'未选择操作');a.check_only=mode=='2'
  a.game=path_input('选择含 PS3_GAME 的游戏目录')
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
