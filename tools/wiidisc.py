"""Wii 디스크 이미지(복호화/암호화 공용) DATA 파티션 구조 읽기.
클러스터 0x8000 = 해시 헤더 0x400 + 데이터 0x7C00, 64클러스터(2MB) = 한 그룹(H3 한 칸)."""
import struct

CL, HDR, DATA = 0x8000, 0x400, 0x7C00
GROUP = 64


class Part:
    def __init__(self, f, poff):
        self.f = f; self.poff = poff
        f.seek(poff + 0x2A4)
        self.tmd_size, self.tmd_off, self.cert_size, self.cert_off, self.h3_off, self.data_off, self.data_size = \
            struct.unpack('>IIIIIII', f.read(28))
        self.tmd_off <<= 2; self.cert_off <<= 2; self.h3_off <<= 2; self.data_off <<= 2; self.data_size <<= 2

    def cluster_pos(self, c):
        return self.poff + self.data_off + c * CL

    def read_data(self, off, size):
        """(복호화 이미지 전용) 파티션 데이터 공간에서 읽기"""
        out = bytearray()
        while size > 0:
            c, r = divmod(off, DATA); n = min(size, DATA - r)
            self.f.seek(self.cluster_pos(c) + HDR + r); out += self.f.read(n)
            off += n; size -= n
        return bytes(out)

    def write_data(self, off, data):
        p = 0
        while p < len(data):
            c, r = divmod(off, DATA); n = min(len(data) - p, DATA - r)
            self.f.seek(self.cluster_pos(c) + HDR + r); self.f.write(data[p:p + n])
            off += n; p += n

    def files(self):
        """{경로: (데이터 오프셋, 크기)}  (main.dol 포함)"""
        boot = self.read_data(0, 0x440)
        dol_off, fst_off, fst_size = [v << 2 for v in struct.unpack('>III', boot[0x420:0x42C])]
        fst = self.read_data(fst_off, fst_size)
        n = struct.unpack('>I', fst[8:12])[0]; st = n * 12
        out = {'sys/main.dol': (dol_off, None)}
        dirs = [(n, '')]; path = ''
        ends = []; cur = []
        for i in range(1, n):
            e = fst[i * 12:i * 12 + 12]
            while ends and i >= ends[-1]:
                ends.pop(); cur.pop()
            isdir = e[0]; no = int.from_bytes(e[1:4], 'big'); a, b = struct.unpack('>II', e[4:12])
            nm = fst[st + no:fst.index(b'\0', st + no)].decode()
            if isdir:
                cur.append(nm); ends.append(b)
            else:
                out['files/' + '/'.join(cur + [nm])] = (a << 2, b)
        return out
