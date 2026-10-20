"""AC4 split archive inventory and append-only replacement in staging."""
from pathlib import Path
import struct,zlib,json,hashlib

def unwrap(data):
    assert data[:4]==b'BND3' and data[12]==0xe4
    assert struct.unpack_from('>I',data,16)[0]==1
    size,offset=struct.unpack_from('>2I',data,36)
    result=zlib.decompress(data[offset:offset+size])
    assert len(result)==struct.unpack_from('>I',data,52)[0]
    return result

def wrap(original,payload):
    offset=struct.unpack_from('>I',original,40)[0]
    result=bytearray(original[:offset]);compressed=zlib.compress(payload,9)
    struct.pack_into('>I',result,36,len(compressed))
    struct.pack_into('>I',result,52,len(payload))
    result.extend(compressed)
    assert unwrap(result)==payload
    return bytes(result)

def records(table):
    count=struct.unpack_from('>I',table)[0]
    assert 80+80*count<=len(table)
    for i in range(count):
        offset=80+i*80
        name=table[offset:offset+64].split(b'\0')[0].decode('cp932').replace('\\','/')
        chunk,position,blocks,size=struct.unpack_from('>4I',table,offset+64)
        assert blocks*16>=size
        yield offset,name,chunk,position*16,size

def repack(base,replacements,reader=Path.read_bytes):
    """Return changed archive bytes, preserving all existing member positions."""
    raw={0:reader(base.with_suffix('.000'))}
    chunks={0:bytearray(unwrap(raw[0]))}
    found=set();expected=[]
    for offset,name,chunk,position,size in list(records(chunks[0])):
        if name not in replacements:continue
        if chunk not in chunks:
            raw[chunk]=reader(base.with_suffix(f'.{chunk:03d}'))
            chunks[chunk]=bytearray(unwrap(raw[chunk]))
        value=replacements[name];found.add(name)
        chunks[chunk].extend(b'\0'*(-len(chunks[chunk])%16))
        newpos=len(chunks[chunk]);chunks[chunk].extend(value)
        chunks[chunk].extend(b'\0'*(-len(chunks[chunk])%16))
        struct.pack_into('>4I',chunks[0],offset+64,chunk,newpos//16,(len(value)+15)//16,len(value))
        expected.append((chunk,newpos,value))
    assert found==replacements.keys(),replacements.keys()-found
    for chunk,position,value in expected:assert chunks[chunk][position:position+len(value)]==value
    return {base.with_suffix(f'.{chunk:03d}'):wrap(raw[chunk],data) for chunk,data in chunks.items()}
