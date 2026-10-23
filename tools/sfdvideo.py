"""Sofdec SFD(MPEG-1 프로그램 스트림, 2048바이트 묶음)의 영상만 새 MPEG-1 ES 로 바꿔 끼우기.

- 음성(ADX)·채움·CRI 헤더(SofdecStream, CRITAGS) 묶음은 바이트 그대로 둔다. 파일 크기도 원본과 같다.
- 새 ES 의 그림 k 는 원본 ES 에서 그림 k 가 있던 위치보다 앞에 오지 않게 0 채움을 넣는다
  (시작 코드 앞 0 은 MPEG 에서 허용). 그래서 그림이 들어오는 시점이 원본과 같다. 새 ES 는 원본보다 작아야 한다.
- 영상 PES 헤더는 원본과 같은 길이로 만들고, 그 묶음에서 시작하는 첫 그림의 PTS(·DTS)를 넣는다.
  원본 규칙: 한 프레임 3006(90kHz), I·P 는 PTS+DTS, B 는 PTS 만.
"""
import struct

SC = b'\x00\x00\x01'
PACK = SC + b'\xba'
T = 3006


def packs(d):
    """2048바이트 묶음마다 (오프셋, 묶음 헤더 또는 None, [(스트림 ID, PES 전체)])"""
    out = []
    for o in range(0, len(d), 2048):
        if d[o:o + 4] != PACK:                 # 끝 묶음: 000001b9 + FF 채움
            out.append((o, None, [(0xB9, d[o:o + 2048])]))
            continue
        items = []
        p = o + 12
        while p < o + 2048 and d[p:p + 3] == SC:
            sid = d[p + 3]
            if sid == 0xB9:
                items.append((sid, d[p:p + 4]))
                p += 4
                continue
            n = struct.unpack('>H', d[p + 4:p + 6])[0]
            items.append((sid, d[p:p + 6 + n]))
            p += 6 + n
        out.append((o, d[o:o + 12], items))
    return out


def _ts_read(b):
    return ((b[0] >> 1) & 7) << 30 | b[1] << 22 | (b[2] >> 1) << 15 | b[3] << 7 | b[4] >> 1


def _ts(prefix, t):
    return bytes([(prefix << 4) | ((t >> 30) & 7) << 1 | 1, (t >> 22) & 0xFF, ((t >> 15) & 0x7F) << 1 | 1,
                  (t >> 7) & 0xFF, (t & 0x7F) << 1 | 1])


def pes_payload(pes):
    """MPEG-1 PES 헤더(채움·STD 버퍼·PTS/DTS)를 건너뛴 내용, PTS, DTS"""
    p = 6
    while pes[p] == 0xFF:
        p += 1
    if (pes[p] >> 6) == 1:
        p += 2
    pts = dts = None
    if (pes[p] >> 4) == 2:
        pts = _ts_read(pes[p:p + 5])
        p += 5
    elif (pes[p] >> 4) == 3:
        pts, dts = _ts_read(pes[p:p + 5]), _ts_read(pes[p + 5:p + 10])
        p += 10
    else:
        p += 1
    return pes[p:], pts, dts


def video_es(d):
    """SFD 바이트에서 영상 ES 만 이어 붙인 것"""
    es = bytearray()
    for _, _, items in packs(d):
        for sid, pes in items:
            if sid == 0xE0:
                es += pes_payload(pes)[0]
    return bytes(es)


def units(es):
    """그림마다 [단위 시작(앞의 시퀀스·GOP 헤더 포함), 그림 헤더 위치, 종류(1=I,2=P,3=B), temporal_reference, GOP 시작]"""
    out = []
    p = 0
    pend = None
    gop = False
    while True:
        p = es.find(SC, p)
        if p < 0:
            break
        c = es[p + 3]
        if c == 0x00:
            out.append([pend if pend is not None else p, p, (es[p + 5] >> 3) & 7, es[p + 4] << 2 | es[p + 5] >> 6, gop])
            pend = None
            gop = False
        elif 0x01 <= c <= 0xAF:
            pend = None
        else:
            if pend is None:
                pend = p
            if c == 0xB8:
                gop = True
        p += 3
    return out


def keyframes(es):
    """원본 ES 의 I 프레임 표시 번호들 (새 인코딩에서 같은 자리에 I 프레임을 두려고)"""
    base = size = 0
    out = []
    for s, ph, typ, tref, gop in units(es):
        if gop:
            base += size
            size = 0
        size += 1
        if typ == 1:
            out.append(base + tref)
    return out


def replace_video(d, ne):
    """원본 SFD 바이트 d 의 영상을 새 ES ne 로 바꾼 SFD 바이트"""
    pk = packs(d)
    old = bytearray()
    slots = []
    for pi, (o, h, items) in enumerate(pk):
        for ii, (sid, pes) in enumerate(items):
            if sid == 0xE0:
                pl = pes_payload(pes)[0]
                slots.append((pi, ii, len(pes) - 6 - len(pl), len(pl)))
                old += pl
    cap = len(old)
    ou, nu = units(old), units(ne)
    if len(ou) != len(nu):
        raise SystemExit(f'그림 수가 다름: 원본 {len(ou)}, 새 {len(nu)}')
    es = bytearray()
    pics = []                                  # (새 ES 안 그림 헤더 위치, 종류, 표시 번호, 디코드 번호)
    base = size = 0
    for k, (s, ph, typ, tref, gop) in enumerate(nu):
        if gop:
            base += size
            size = 0
        size += 1
        end = nu[k + 1][0] if k + 1 < len(nu) else len(ne)
        target = min(ou[k][0], cap - 4 - (len(ne) - s))   # 남은 그림이 끝까지 들어갈 만큼만 늦춘다
        if len(es) < target:
            es += bytes(target - len(es))
        pics.append((len(es) + ph - s, typ, base + tref, k))
        es += ne[s:end]
    if len(es) > cap:
        raise SystemExit(f'새 영상이 원본 자리보다 큼: {len(es)} > {cap}')
    if es.endswith(SC + b'\xb7'):
        es = es[:-4] + bytes(cap - len(es)) + SC + b'\xb7'
    else:
        es += bytes(cap - len(es))
    out = bytearray(d)
    pos = q = 0
    for pi, ii, hl, n in slots:
        while q < len(pics) and pics[q][0] < pos:
            q += 1
        stamp = b'\x0f'
        if q < len(pics) and pics[q][0] < pos + n:
            _, typ, disp, dec = pics[q]
            stamp = _ts(2, disp * T) if typ == 3 else _ts(3, disp * T) + _ts(1, dec * T)
        head = b'\xff' * (hl - 2 - len(stamp)) + b'\x60\x2e' + stamp
        p = pk[pi][0] + 12 + sum(len(x[1]) for x in pk[pi][2][:ii])
        pes = SC + b'\xe0' + struct.pack('>H', hl + n) + head + es[pos:pos + n]
        out[p:p + len(pes)] = pes
        pos += n
    return bytes(out)
