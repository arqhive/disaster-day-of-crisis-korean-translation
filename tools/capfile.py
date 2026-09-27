"""Disaster .cap subtitles: u16 header, then events {0x00, u16 frame, sjis text (empty = clear)}."""
def load(path):
    d=open(path,'rb').read();p=2;ev=[]
    while p+3<=len(d) and d[p]==0:
        fr=int.from_bytes(d[p+1:p+3],'big');p+=3
        e=d.find(b'\0',p);e=len(d) if e<0 else e
        ev.append([fr,d[p:e]]);p=e
    return d[:2],ev,d[p:]
def save(path,head,ev,tail):
    out=bytearray(head)
    for fr,t in ev:out+=b'\0'+fr.to_bytes(2,'big')+t
    out+=tail;open(path,'wb').write(out)
