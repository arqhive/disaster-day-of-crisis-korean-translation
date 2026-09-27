"""Symbol table (sec h[4]) and function table (sec h[3]) of a Disaster .sb."""
import struct
def cstr(b,o):return b[o:b.index(b'\0',o)].decode('ascii','replace')
def meta(sb):
    d=sb.d;h=sb.hdr
    n4=struct.unpack('>I',d[h[4]+4:h[4]+8])[0]
    e4=[struct.unpack('>HH',d[h[4]+8+4*i:h[4]+12+4*i]) for i in range(n4)]
    blob=d[h[4]+8+4*n4:h[5]]
    syms=[(cstr(blob,p),cstr(blob,o)) for p,o in e4]
    n3=struct.unpack('>I',d[h[3]+4:h[3]+8])[0]
    base3=h[3]+8
    funcs=[]
    for i in range(n3):
        no,co=struct.unpack('>II',d[base3+8*i:base3+8*i+8])
        funcs.append((co,cstr(d,base3+no)))
    return syms,funcs
