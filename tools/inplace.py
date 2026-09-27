"""원본 ISO 의 배치를 그대로 두고 바뀐 파일만 교체해 작은 xdelta 가 나오는 ISO 를 만든다.
1) wit 로 원본을 배치 유지 복호화(work/dec.iso)
2) 바뀐 파일(work/out/files)을 원래 자리에 덮어쓰기. 원래 자리보다 커진 파일은
   FST 뒤 빈 공간(원본에서 쓰지 않는 앞쪽 약 300MB)으로 옮기고 FST 의 위치·크기를 고친다
3) 바뀐 2MB 그룹의 H0/H1/H2 해시를 직접 계산해 기록
4) wit 로 암호화(work/R.iso) — 해시는 다시 계산하지 않으므로 3)의 값이 그대로 쓰인다
5) 원본 ISO 복사본에 바뀐 그룹만 R 에서 옮기고, H3 표·TMD 해시 갱신 후 가짜 서명
사용법: python tools/inplace.py [출력.iso]"""
import hashlib, os, shutil, struct, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, wiidisc
from wiidisc import CL, HDR, DATA, GROUP

POFF = 0xF800000
ALIGN = 0x20
sha1 = lambda b: hashlib.sha1(b).digest()


def read_fst(P):
    boot = P.read_data(0, 0x440)
    dol_off, fst_off, fst_size = [v << 2 for v in struct.unpack('>III', boot[0x420:0x42C])]
    dol = P.read_data(dol_off, 0x100)
    offs = struct.unpack('>18I', dol[0:0x48]); sizes = struct.unpack('>18I', dol[0x90:0xD8])
    dol_end = dol_off + max(o + s for o, s in zip(offs, sizes) if s)
    fst = bytearray(P.read_data(fst_off, fst_size))
    n = struct.unpack('>I', fst[8:12])[0]; st = n * 12
    files, ends, cur = {}, [], []
    for i in range(1, n):
        e = fst[i * 12:i * 12 + 12]
        while ends and i >= ends[-1]:
            ends.pop(); cur.pop()
        no = int.from_bytes(e[1:4], 'big'); a, b = struct.unpack('>II', e[4:12])
        nm = fst[st + no:fst.index(b'\0', st + no)].decode()
        if e[0]:
            cur.append(nm); ends.append(b)
        else:
            files['/'.join(cur + [nm])] = [i, a << 2, b]
    return fst_off, fst, dol_end, files


def changed_files():
    out = {}
    for root, _, fs in os.walk(paths.OUT_FILES):
        for f in fs:
            p = os.path.join(root, f)
            out[os.path.relpath(p, paths.OUT_FILES).replace(os.sep, '/')] = p
    return out


def main(out_iso):
    sys.stdout.reconfigure(encoding='utf-8')
    os.chdir(paths.ROOT)
    jp = paths.jp_iso()
    dec, enc = os.path.join(paths.WORK, 'dec.iso'), os.path.join(paths.WORK, 'R.iso')
    print('1) 복호화')
    paths.run_wit('copy', paths.rel(jp), paths.rel(dec), '--psel', 'WHOLE', '--enc', 'DECRYPT', '--overwrite')
    f = open(dec, 'r+b'); P = wiidisc.Part(f, POFF)
    fst_off, fst, dol_end, files = read_fst(P)
    starts = sorted([fst_off] + [o for _, o, _ in files.values()])
    first_file = min(o for _, o, _ in files.values())
    cursor = -(-max(fst_off + len(fst), dol_end) // 0x8000) * 0x8000   # 빈 공간 시작 (32KB 정렬)
    groups = set()

    def touch(off, size):
        for c in range(off // DATA, (off + max(size, 1) - 1) // DATA + 1):
            groups.add(c // GROUP)

    print('2) 파일 교체')
    moved = 0
    for rel, p in sorted(changed_files().items()):
        idx, off, size = files[rel]
        d = open(p, 'rb').read()
        nxt = next(s for s in starts if s > off)
        if len(d) <= nxt - off:
            P.write_data(off, d + b'\0' * max(0, size - len(d)))
            touch(off, max(size, len(d)))
        else:
            off = cursor
            cursor = -(-(cursor + len(d)) // ALIGN) * ALIGN
            if cursor > first_file:
                raise SystemExit('빈 공간이 부족합니다.')
            P.write_data(off, d)
            touch(off, len(d))
            moved += 1
        struct.pack_into('>II', fst, idx * 12 + 4, off >> 2, len(d))
    P.write_data(fst_off, bytes(fst)); touch(fst_off, len(fst))
    print(f'   파일 {len(changed_files())}개 (빈 공간으로 옮김 {moved}개, 사용 {cursor - 0:#x}/{first_file:#x})')

    ncl = P.data_size // CL
    print('3) 해시 재계산:', len(groups), '그룹')
    h3 = {}
    for g in sorted(groups):
        cls = range(g * GROUP, min((g + 1) * GROUP, ncl))
        h0 = {}
        for c in cls:
            f.seek(P.cluster_pos(c) + HDR); d = f.read(DATA)
            h0[c] = b''.join(sha1(d[i * 0x400:(i + 1) * 0x400]) for i in range(31))
        h1 = {}
        for sg in range(8):
            sub = [c for c in cls if (c - g * GROUP) // 8 == sg]
            h1[sg] = b''.join(sha1(h0[c]) for c in sub).ljust(0xA0, b'\0')
        h2 = b''.join(sha1(h1[sg]) for sg in range(8))
        for c in cls:
            sg = (c - g * GROUP) // 8
            hdr = h0[c] + b'\0' * 0x14 + h1[sg] + b'\0' * 0x20 + h2 + b'\0' * 0x20
            f.seek(P.cluster_pos(c)); f.write(hdr)
        h3[g] = sha1(h2)
    f.close()

    print('4) 암호화')
    paths.run_wit('copy', paths.rel(dec), paths.rel(enc), '--psel', 'WHOLE', '--enc', 'ENCRYPT', '--overwrite')
    print('5) 합치기')
    shutil.copyfile(jp, out_iso)
    F = open(out_iso, 'r+b'); R = open(enc, 'rb')
    for g in sorted(groups):
        a = P.cluster_pos(g * GROUP); n = min(GROUP, ncl - g * GROUP) * CL
        R.seek(a); F.seek(a); F.write(R.read(n))
    F.seek(POFF + P.h3_off); H3 = bytearray(F.read(0x18000))
    for g, v in h3.items():
        H3[g * 20:g * 20 + 20] = v
    F.seek(POFF + P.h3_off); F.write(H3)
    # TMD: 콘텐츠 해시 갱신 + 가짜 서명(서명 0, 0x1C8~ 값을 바꿔 SHA1 첫 바이트 00)
    F.seek(POFF + P.tmd_off); tmd = bytearray(F.read(P.tmd_size))
    tmd[0x4:0x104] = b'\0' * 0x100
    tmd[0x1F4:0x208] = sha1(bytes(H3))
    for i in range(1 << 32):
        struct.pack_into('>I', tmd, 0x1C8, i)
        if sha1(bytes(tmd[0x140:]))[0] == 0:
            break
    F.seek(POFF + P.tmd_off); F.write(tmd)
    F.close(); R.close()
    os.remove(enc); os.remove(dec)
    print('완료:', paths.rel(out_iso))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(paths.WORK, 'Disaster_KO.iso'))
