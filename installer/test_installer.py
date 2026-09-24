"""Synthetic transaction tests; never open real game files."""
import bsdiff4
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import install as ac


def sha(data):
    return hashlib.sha256(data).hexdigest()


def put(root, name, data):
    p = root / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(data)
    return p


def make_sfo(title='BLJM60012', version='01.05', category='DG'):
    keys = bytearray(); values = bytearray(); entries = bytearray()
    for k,v in [('TITLE_ID',title),('VERSION',version),('CATEGORY',category)]:
        val=v.encode()+b'\0'
        entries += struct.pack('<HHIII',len(keys),0x204,len(val),len(val),len(values))
        keys += k.encode()+b'\0'; values += val
    start=20+len(entries)
    return struct.pack('<4s4I',b'\0PSF',0x101,start,start+len(keys),3)+entries+keys+values


class InstallerTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ac4-test-')
        self.root=Path(self.tmp.name).resolve()
        self.game=self.root/'游戏 A';self.update=self.root/'更新 B';self.pkg=self.root/'独立包'
        self.pkg.mkdir();self.roots={'base':self.game,'update':self.update}
        self.sfo=put(self.game,'PS3_GAME/PARAM.SFO',make_sfo())
        put(self.game,'PS3_GAME/USRDIR/EBOOT.BIN',b'unchanged executable')
        put(self.update,'PARAM.SFO',make_sfo(category='GD'))
        self.m=dict(format=2,release='test',game='BLJM60012',version='01.05',base=[],update=[],unchanged=[],update_unchanged=[])
        for scope,names in [('base',['PS3_GAME/USRDIR/bind/app.000','PS3_GAME/USRDIR/bind/app.001']),('update',['USRDIR/regulation.bin'])]:
            for name in names:
                old=b'original '+name.encode();new=b'translated '+name.encode()
                put(self.roots[scope],name,old)
                data=bsdiff4.diff(old,new);payload='payload/'+name
                put(self.pkg,payload,data)
                self.m[scope].append(dict(path=name,original_size=len(old),original_sha256=sha(old),size=len(new),sha256=sha(new),segments=[dict(payload=payload,old_offset=0,old_size=len(old),output_offset=0,size=len(new),sha256=sha(new),patch_size=len(data),patch_sha256=sha(data))]))
        for scope,key,names in [('base','unchanged',['PS3_GAME/PARAM.SFO','PS3_GAME/USRDIR/EBOOT.BIN']),('update','update_unchanged',['PARAM.SFO'])]:
            for name in names:
                data=(self.roots[scope]/name).read_bytes();self.m[key].append(dict(path=name,size=len(data),sha256=sha(data)))
        self.target=self.game/self.m['base'][0]['path'];self.second=self.game/self.m['base'][1]['path']
        self.initial={p:p.read_bytes() for root in self.roots.values() for p in root.rglob('*') if p.is_file()}
        self.closed=patch.object(ac,'ensure_closed');self.closed.start()

    def tearDown(self):
        self.closed.stop();self.tmp.cleanup()

    def install(self,roots=None):
        roots=roots or self.roots
        return ac.apply(self.pkg,self.m,roots,ac.plan(self.pkg,self.m,roots))

    def unchanged(self):
        for p,data in self.initial.items():self.assertEqual(p.read_bytes(),data,str(p))

    def test_install_repeat_restore(self):
        backup=self.install();self.assertEqual(ac.plan(self.pkg,self.m,self.roots),[])
        self.assertIsNone(self.install())
        ac.restore(backup);self.unchanged();ac.restore(backup);self.unchanged()

    def test_base_only(self):
        backup=self.install({'base':self.game})
        for p,data in self.initial.items():
            if self.update in p.parents:self.assertEqual(p.read_bytes(),data)
        ac.restore(backup);self.unchanged()

    def test_wrong_game_or_version(self):
        for title,version in [('BLJM99999','01.05'),('BLJM60012','01.00')]:
            self.sfo.write_bytes(make_sfo(title,version))
            with self.assertRaisesRegex(ValueError,'版本不符'):ac.plan(self.pkg,self.m,self.roots)
            self.assertEqual(self.target.read_bytes(),self.initial[self.target])

    def test_wrong_update(self):
        (self.update/'PARAM.SFO').write_bytes(make_sfo(category='DG'))
        with self.assertRaisesRegex(ValueError,'版本不符'):self.install()
        self.assertEqual(self.target.read_bytes(),self.initial[self.target])

    def test_unknown_update_overlay(self):
        put(self.update,'USRDIR/EBOOT.BIN',b'other version')
        with self.assertRaisesRegex(ValueError,'覆盖资源'):self.install()
        self.unchanged()

    def test_unknown_patch_rejected_before_write(self):
        for p in [self.second,self.update/'USRDIR/regulation.bin']:
            p.write_bytes(b'other patch')
            with self.assertRaisesRegex(ValueError,'不受支持'):self.install()
            self.assertEqual(self.target.read_bytes(),self.initial[self.target]);p.write_bytes(self.initial[p])

    def test_missing_resource(self):
        self.second.unlink()
        with self.assertRaisesRegex(ValueError,'缺少游戏文件'):self.install()
        self.assertEqual(self.target.read_bytes(),self.initial[self.target])

    def test_payload_corruption(self):
        (self.pkg/self.m['base'][0]['segments'][0]['payload']).write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError,'损坏'):self.install()
        self.unchanged()

    def test_manifest_corruption(self):
        raw=json.dumps(self.m).encode();put(self.pkg,'manifest.json',raw);put(self.pkg,'manifest.sha256',(sha(raw)+'  manifest.json').encode())
        self.assertEqual(ac.load(self.pkg),self.m)
        put(self.pkg,'manifest.json',raw+b'x')
        with self.assertRaisesRegex(ValueError,'清单损坏'):ac.load(self.pkg)

    def test_executable_fingerprint(self):
        p=self.game/'PS3_GAME/USRDIR/EBOOT.BIN';p.write_bytes(b'unknown')
        with self.assertRaisesRegex(ValueError,'原版资源不匹配'):self.install()
        self.assertEqual(self.target.read_bytes(),self.initial[self.target])

    def test_write_failure_rolls_back(self):
        original=ac.os.replace;once=[True]
        def injected(a,b):
            if Path(b)==self.second and once[0]:
                once[0]=False;raise OSError('injected failure')
            return original(a,b)
        with patch.object(ac.os,'replace',injected):
            with self.assertRaisesRegex(OSError,'injected'):self.install()
        self.unchanged();self.assertFalse((self.game/ac.LOCK).exists())

    def test_changes_between_plan_and_install(self):
        changes=ac.plan(self.pkg,self.m,self.roots);self.second.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'发生变化'):ac.apply(self.pkg,self.m,self.roots,changes)
        self.assertEqual(self.target.read_bytes(),self.initial[self.target])

    def test_restore_refuses_later_modifications(self):
        backup=self.install();self.target.write_bytes(b'another patch');before=self.second.read_bytes()
        with self.assertRaisesRegex(ValueError,'其他补丁'):ac.restore(backup)
        self.assertEqual(self.second.read_bytes(),before)

    def test_space_failure(self):
        with patch.object(ac.shutil,'disk_usage',return_value=type('DU',(),{'free':0})()):
            with self.assertRaisesRegex(ValueError,'空间不足'):self.install()
        self.unchanged()

    def test_unsafe_paths(self):
        for name in ['../x','/tmp/a','USRDIR/C:\\test']:
            with self.assertRaises(ValueError):ac.safe(self.game,name)
        if os.name!='nt':
            (self.game/'outside').symlink_to(self.pkg,target_is_directory=True)
            with self.assertRaisesRegex(ValueError,'符号链接'):ac.safe(self.game,'outside/file')

    def test_moved_game_can_restore(self):
        backup=self.install();relative=backup.relative_to(self.game);new=self.root/'搬迁 游戏'
        self.game.rename(new);ac.restore(new/relative,{'base':new,'update':self.update})
        for p,data in self.initial.items():
            dest=new/p.relative_to(self.game) if self.game in p.parents else p
            self.assertEqual(dest.read_bytes(),data)

    def test_known_previous_release_upgrade(self):
        row=self.m['base'][0];previous=b'previous Chinese release'
        current=b'translated '+row['path'].encode();delta=bsdiff4.diff(previous,current)
        put(self.pkg,'payload/upgrade.bsdiff',delta)
        row['alternatives']=[dict(original_size=len(previous),original_sha256=sha(previous),segments=[dict(payload='payload/upgrade.bsdiff',old_offset=0,old_size=len(previous),output_offset=0,size=len(current),sha256=sha(current),patch_size=len(delta),patch_sha256=sha(delta))])]
        self.target.write_bytes(previous);self.initial[self.target]=previous
        backup=self.install();self.assertEqual(self.target.read_bytes(),current)
        ac.restore(backup);self.unchanged()

    def test_upgrade_payload_corruption(self):
        row=self.m['base'][0];previous=b'previous release';delta=bsdiff4.diff(previous,b'translated '+row['path'].encode())
        put(self.pkg,'payload/upgrade.bsdiff',b'corrupt')
        row['alternatives']=[dict(original_size=len(previous),original_sha256=sha(previous),segments=[dict(payload='payload/upgrade.bsdiff',patch_size=len(delta),patch_sha256=sha(delta))])]
        with self.assertRaisesRegex(ValueError,'损坏'):self.install()
        self.unchanged()

    def test_sudden_exit_recovery(self):
        (self.root/'fixture.json').write_text(json.dumps(self.m))
        script='''import install as ac,json,os,pathlib,sys
root=pathlib.Path(sys.argv[1]);m=json.loads((root/'fixture.json').read_text());roots={'base':root/'游戏 A','update':root/'更新 B'}
ac.ensure_closed=lambda:None
original=ac.os.replace
def interrupted(a,b):
 original(a,b)
 if pathlib.Path(b)==roots['base']/'PS3_GAME/USRDIR/bind/app.000':os._exit(77)
ac.os.replace=interrupted
ac.apply(root/'独立包',m,roots,ac.plan(root/'独立包',m,roots))
'''
        env=dict(os.environ,PYTHONPATH=str(Path(ac.__file__).parent))
        result=subprocess.run([sys.executable,'-c',script,str(self.root)],env=env,capture_output=True)
        self.assertEqual(result.returncode,77,result.stderr)
        lock=json.loads((self.game/ac.LOCK).read_text())
        with self.assertRaisesRegex(ValueError,'未恢复'):self.install()
        ac.restore(Path(lock['backup']));self.unchanged()


if __name__=='__main__':unittest.main(verbosity=2)
