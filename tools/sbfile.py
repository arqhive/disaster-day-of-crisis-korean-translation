"""Disaster .sb script: header 'SB  ', 6 section offsets at 0x08; section at hdr[2] = string pool
(u32 8, u32 count, u32 offsets[count], NUL-terminated strings, padding). Later sections shift."""
import struct
ALIGN=4
class SB:
    def __init__(s,path):
        d=s.d=open(path,'rb').read()
        s.hdr=list(struct.unpack('>6I',d[8:0x20]))
        b=s.hdr[2];n=struct.unpack('>I',d[b+4:b+8])[0]
        offs=struct.unpack('>%dI'%n,d[b+8:b+8+4*n]);base=b+8+4*n
        s.strs=[d[base+o:d.index(b'\0',base+o)] for o in offs]
        s.offs=offs
    def build(s):
        d=s.d;b=s.hdr[2];n=len(s.strs)
        body=bytearray();offs=[];seen={}
        for x in s.strs:
            offs.append(len(body));body+=x+b'\0'
        pool=struct.pack('>II',8,n)+struct.pack('>%dI'%n,*offs)+body
        while (b+len(pool))%ALIGN:pool+=b'\0'
        delta=b+len(pool)-s.hdr[3]
        hdr=s.hdr[:3]+[h+delta if h else 0 for h in s.hdr[3:]]
        return d[:8]+struct.pack('>6I',*hdr)+d[0x20:b]+pool+d[s.hdr[3]:]
