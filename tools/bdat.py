"""Disaster bdat.bin: u32 count, u32 total_size, u32 section_offsets[count]; each section 'BDAT'
header: 0x06 names_off, 0x08 row_len, 0x0a rows_off, 0x0c row_count; column infos at 0x20 (u8 type, u8 vtype, u16 off);
vtype 7 = string = u16 offset (section-relative) into string area after rows."""
import struct
def load(path):
    d=open(path,'rb').read()
    n=struct.unpack('>I',d[:4])[0]
    offs=list(struct.unpack('>%dI'%(n+1),d[4:8+4*n]))
    secs=[d[offs[i+1]:(offs[i+2] if i+1<n else offs[0])] for i in range(n)]
    return d[:offs[1]],secs,d[offs[0]:]
class Table:
    def __init__(s,sec):
        s.sec=sec
        names,s.rl,s.ro,s.rc=struct.unpack('>HHHH',sec[6:14])
        s.cols=[];p=0x20
        while p<names:s.cols.append(struct.unpack('>BBH',sec[p:p+4]));p+=4
        s.name=sec[names:sec.index(b'\0',names)].decode()
        s.scols=[i for i,(t,vt,o) in enumerate(s.cols) if t==1 and vt==7]
        s.rows=[]
        for r in range(s.rc):
            b=s.ro+r*s.rl;row={}
            for i in s.scols:
                o=struct.unpack('>H',sec[b+s.cols[i][2]:b+s.cols[i][2]+2])[0]
                row[i]=sec[o:sec.index(b'\0',o)]
            s.rows.append(row)
        s.sstart=s.ro+s.rl*s.rc
    def build(s,pad=16):
        out=bytearray(s.sec[:s.sstart]);pool={}
        for r,row in enumerate(s.rows):
            b=s.ro+r*s.rl
            for i in s.scols:
                x=row[i]
                o=len(out);out+=x+b'\0'
                assert o<0x10000
                struct.pack_into('>H',out,b+s.cols[i][2],o)
        while len(out)%pad:out+=b'\0'
        return bytes(out)
def save(path,head,secs,tail):
    n=len(secs);o=len(head);offs=[]
    for s in secs:offs.append(o);o+=len(s)
    out=bytearray(head);struct.pack_into('>%dI'%(n+1),out,4,o,*offs)
    for s in secs:out+=s
    open(path,'wb').write(out+tail)
