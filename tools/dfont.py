"""Disaster \x01ARC font: char table + I4 TPL atlas (24x28 cells, 16 cols x 26 rows per sheet)."""
import struct
from PIL import Image
CW=24;CH=28;COLS=16;ROWS=26
class Font:
    def __init__(s,path):
        d=s.d=bytearray(open(path,'rb').read())
        s.tl=struct.unpack('>I',d[0x14:0x18])[0]
        s.tex=struct.unpack('>I',d[0x18:0x1c])[0]  # 0x2b40
        p=0x20;s.ents=[]  # (code bytes, width, table pos of width byte)
        while p<0x20+s.tl:
            b=d[p]
            if b==0:break
            if b<0x80 or 0xa0<=b<0xe0:s.ents.append((bytes([b]),d[p+1],p+1));p+=2
            else:s.ents.append((bytes(d[p:p+2]),d[p+2],p+2));p+=3
        t=s.tex;n=struct.unpack('>I',d[t+4:t+8])[0];s.sheets=[]
        for i in range(n):
            io=struct.unpack('>I',d[t+12+i*8:t+16+i*8])[0]
            h,w,f,off=struct.unpack('>HHII',d[t+io:t+io+12]);s.sheets.append((w,h,t+off))
        s.index={c:i for i,(c,w,p) in enumerate(s.ents)}
    def _px(s,sheet,x,y):
        w,h,off=s.sheets[sheet]
        bi=((y//8)*(w//8)+(x//8))*32+(y%8)*4+(x%8)//2
        return off+bi,(x%2==0)
    def get(s,idx):
        sh,r=divmod(idx,COLS*ROWS);cy,cx=divmod(r,COLS)
        im=Image.new('L',(CW,CH))
        for y in range(CH):
            for x in range(CW):
                a,hi=s._px(sh,cx*CW+x,cy*CH+y);v=s.d[a]
                im.putpixel((x,y),((v>>4) if hi else v&15)*17)
        return im
    def put(s,idx,im):
        sh,r=divmod(idx,COLS*ROWS);cy,cx=divmod(r,COLS)
        for y in range(CH):
            for x in range(CW):
                v=min(15,(im.getpixel((x,y))+8)//17);a,hi=s._px(sh,cx*CW+x,cy*CH+y)
                s.d[a]=(s.d[a]&0x0f)|(v<<4) if hi else (s.d[a]&0xf0)|v
    def setwidth(s,idx,w):s.d[s.ents[idx][2]]=w
    def save(s,path):open(path,'wb').write(s.d)
