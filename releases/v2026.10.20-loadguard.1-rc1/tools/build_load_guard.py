from pathlib import Path
import struct,json,hashlib,sys
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_PPC,CS_MODE_64,CS_MODE_BIG_ENDIAN
import argparse
parser=argparse.ArgumentParser(description='Build the BLJM60012 AcParts description-load guard from owned baseline files.')
parser.add_argument('--elf',required=True)
parser.add_argument('--parts',required=True)
parser.add_argument('--out',required=True)
parser.add_argument('--rows',default=str(Path(__file__).with_name('description-layout.json')))
args=parser.parse_args()
D=Path(args.out).resolve()
A=Path(args.elf).resolve()
sha=lambda b:hashlib.sha256(b).hexdigest()
elf=A.read_bytes();assert sha(elf)=='2fc6e0c283ed0a070eeabc4836841df6cd6aebedea103f4c427ce96666fd13f7'
parts=Path(args.parts).read_bytes();assert sha(parts)=='9cacef5c652691c85e086242a0e5eac290fbfae4c58e5243dc6f74cdde96d666'
rows=json.loads(Path(args.rows).read_text());assert len(rows)==202
payload=bytearray(parts[:48]+struct.pack('>I',len(rows)))
for r in rows:
 o,n=r['offset'],r['size'];assert n==256
 txt=parts[o:o+n].split(b'\0')[0];assert len(txt)<n
 entry=struct.pack('>III',o,len(txt),0)+parts[o-96:o-64]+txt
 entry+=b'\0'*(-len(entry)%4);entry=entry[:8]+struct.pack('>I',len(entry))+entry[12:];payload+=entry
BASE=0xdb5000;DATA=0xdb5800;HOOK=0x5234a8
code=[];labels={};fix=[]
def emit(w):code.append(w&0xffffffff)
def label(n):labels[n]=BASE+len(code)*4
def d(op,rt,ra,imm):emit((op<<26)|(rt<<21)|(ra<<16)|(imm&65535))
def ds(op,rt,ra,imm,xo=0):assert imm%4==0;emit((op<<26)|(rt<<21)|(ra<<16)|(imm&0xfffc)|xo)
def cmp(a,b):emit((31<<26)|(a<<16)|(b<<11)) # cmpw cr0
def cmpi(a,v):d(11,0,a,v)
def branch(target):fix.append((len(code),'b',target));emit(0)
def cond(bo,bi,target):fix.append((len(code),(bo,bi),target));emit(0)
def bne(t):cond(4,2,t)
def beq(t):cond(12,2,t)
def add(rt,ra,rb):emit((31<<26)|(rt<<21)|(ra<<16)|(rb<<11)|(266<<1))
def address(rt,addr):d(15,rt,0,(addr+0x8000)>>16);d(14,rt,rt,addr&65535)
# Preserve every register touched, CR and original stack. LR/CTR/XER untouched.
ds(62,1,1,-0xa0,1);ds(62,0,1,0x10)
emit(0x7c000026);ds(62,0,1,0x18) # mfcr r0
for reg in range(5,13):ds(62,reg,1,0x20+(reg-5)*8)
cmpi(4,0);beq('done')
# Header comparison, bytewise (does not rely on source alignment).
d(14,5,4,0);address(6,DATA);d(14,7,0,48)
label('header');d(34,8,5,0);d(34,9,6,0);cmp(8,9);bne('done');d(14,5,5,1);d(14,6,6,1);d(14,7,7,-1);cmpi(7,0);bne('header')
# Complete model-identity preflight before modifying any byte.
d(32,7,6,0);d(14,6,6,4)
label('entry_check');d(32,8,6,0);add(8,4,8);d(14,8,8,-96);d(14,9,6,12);d(14,10,0,32)
label('model');d(34,11,8,0);d(34,12,9,0);cmp(11,12);bne('done');d(14,8,8,1);d(14,9,9,1);d(14,10,10,-1);cmpi(10,0);bne('model')
d(32,11,6,8);add(6,6,11);d(14,7,7,-1);cmpi(7,0);bne('entry_check')
# Copy descriptions and clear padding only; numeric bytes stay untouched.
address(6,DATA+48);d(32,7,6,0);d(14,6,6,4)
label('entry_copy');d(32,8,6,0);add(8,4,8);d(14,9,6,44);d(32,10,6,4);d(14,12,0,256)
cmpi(10,0);beq('zero_start')
label('copy');d(34,11,9,0);d(38,11,8,0);d(14,8,8,1);d(14,9,9,1);d(14,10,10,-1);d(14,12,12,-1);cmpi(10,0);bne('copy')
label('zero_start');d(14,11,0,0)
label('zero');d(38,11,8,0);d(14,8,8,1);d(14,12,12,-1);cmpi(12,0);bne('zero')
d(32,11,6,8);add(6,6,11);d(14,7,7,-1);cmpi(7,0);bne('entry_copy')
label('done')
for reg in range(5,13):ds(58,reg,1,0x20+(reg-5)*8)
ds(58,0,1,0x18);emit(0x7c0ff120) # mtcrf 255,r0
ds(58,0,1,0x10);d(14,1,1,0xa0)
original=struct.unpack_from('>I',elf,HOOK-0x10000)[0];assert original==0xf821fd61
emit(original);branch(HOOK+4)
for i,kind,target in fix:
 target=labels[target] if isinstance(target,str) else target;delta=target-(BASE+i*4);assert delta%4==0
 if kind=='b':assert -0x2000000<=delta<0x2000000;code[i]=0x48000000|(delta&0x3fffffc)
 else:
  assert -32768<=delta<32768;bo,bi=kind;code[i]=(16<<26)|(bo<<21)|(bi<<16)|(delta&0xfffc)
blob=b''.join(struct.pack('>I',x) for x in code);assert len(blob)<=DATA-BASE
phoff=struct.unpack_from('>Q',elf,32)[0];ph=struct.unpack_from('>II6Q',elf,phoff);assert ph==(1,5,0,0x10000,0x10000,0xda4bd8,0xda4bd8,0x10000)
assert not any(elf[0xda4bd8:0xdb0000]);assert DATA-0x10000+len(payload)<=0xdb0000
out=bytearray(elf);struct.pack_into('>QQ',out,phoff+32,0xdb0000,0xdb0000)
struct.pack_into('>I',out,HOOK-0x10000,0x48000000|((BASE-HOOK)&0x3fffffc))
out[BASE-0x10000:BASE-0x10000+len(blob)]=blob;out[DATA-0x10000:DATA-0x10000+len(payload)]=payload
# Declare the injected executable section so static PPU recompilers discover it.
shoff=struct.unpack_from('>Q',elf,40)[0];shsize,shnum=struct.unpack_from('>HH',elf,58)
assert shsize==64 and shoff+shsize*shnum==len(elf)
out.extend(struct.pack('>II4QII2Q',0,1,6,BASE,BASE-0x10000,len(blob),0,0,4,0))
out.extend(struct.pack('>II4QII2Q',0,1,2,DATA,DATA-0x10000,len(payload),0,0,4,0))
struct.pack_into('>H',out,60,shnum+2)
cs=Cs(CS_ARCH_PPC,CS_MODE_64|CS_MODE_BIG_ENDIAN);dis=list(cs.disasm(blob,BASE));assert len(dis)==len(code)
D.mkdir(parents=True,exist_ok=True)
(D/'hook.bin').write_bytes(blob);(D/'payload.bin').write_bytes(payload);(D/'EBOOT.candidate.elf').write_bytes(out)
(D/'hook-disassembly.txt').write_text('\n'.join(f'{i.address:08x}: {i.bytes.hex()} {i.mnemonic} {i.op_str}' for i in dis))
report=dict(original_elf_sha256=sha(elf),candidate_elf_sha256=sha(out),hook=hex(HOOK),code=hex(BASE),data=hex(DATA),code_bytes=len(blob),data_bytes=len(payload),description_count=len(rows),segment_before=ph[5],segment_after=0xdb0000,status='static_candidate_not_runtime_verified')
(D/'build-report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
