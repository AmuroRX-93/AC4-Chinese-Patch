from pathlib import Path
import argparse,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()
def verify():
 rows=json.loads((ROOT/'全包校验清单.json').read_text(encoding='utf-8'))['files']
 for i,r in enumerate(rows,1):
  p=ROOT/r['path']
  if not p.resolve().is_relative_to(ROOT):raise ValueError('清单路径越界')
  if not p.is_file() or p.stat().st_size!=r['size'] or sha(p)!=r['sha256']:raise ValueError('缺失或变化：'+r['path'])
  if i%1000==0:print('已校验 %d/%d'%(i,len(rows)),flush=True)
 print('全包文件 SHA-256 校验通过。')
def doctor():
 import cumulative
 print('AC4 delta.5 三平台累计包 · 2026-10-10')
 print('包内解释器：',sys.executable)
 print('Python：',sys.version.split()[0])
 print('累计补丁、最终关与规制模块导入通过。')
def main():
 ap=argparse.ArgumentParser(description='AC4 离线安装、校验与恢复工具')
 ap.add_argument('action',nargs='?',choices=['verify','doctor','install']);a=ap.parse_args().action
 if not a:
  print('AC4 delta.5 三平台累计汉化包\n1 安装／更新／恢复\n2 校验此下载包\n3 检查内置环境\n0 退出')
  a={'1':'install','2':'verify','3':'doctor','0':'exit'}.get(input('选择：').strip())
 if a=='exit':return 0
 if a=='verify':verify();return 0
 if a=='doctor':doctor();return 0
 if a=='install':
  # Official installer has its own install/check/restore menu and precise path checks.
  return subprocess.call([sys.executable,'-E','-s','-B',str(ROOT/'install.py')],cwd=str(ROOT))
 raise ValueError('未选择有效操作')
if __name__=='__main__':
 try:raise SystemExit(main())
 except (Exception,KeyboardInterrupt) as e:print('未完成：'+str(e),file=sys.stderr);raise SystemExit(1)
