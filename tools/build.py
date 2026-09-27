"""한글화 빌드: 번역(translation/ko.json) + 폰트 + 이미지(tools/assets) -> work/out/files/ 에 바뀐 파일만 쓴다(파티션 루트 형식).
원본 추출본(work/extract)은 읽기만 한다. ISO 는 inplace.py 가 만든다.
사용법: python tools/build.py"""
import glob, json, os, re, shutil, sys, zlib
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from PIL import Image
import paths
import dfont, bdat, sbfile, capfile, korfont, gxtex, gxenc, extract_text

FMT = {'CMPR': 14, 'RGB5A3': 5, 'I4': 0}
FONTS = ('font.bin', 'CapFont.bin', 'MenuFont.bin')
TAG = re.compile(r'<[^>]*>')


def src(rel):
    return os.path.join(paths.SRC, rel)


def put(rel, data):
    p = os.path.join(paths.OUT_FILES, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'wb').write(data)


def load_translation():
    """ref(게임 안 위치) -> 한국어. 원문 단위 id 로 master 와 잇는다."""
    if not os.path.exists(paths.MASTER):
        extract_text.main()
    master = {u['id']: u for u in json.load(open(paths.MASTER, encoding='utf-8'))}
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    by_ref, errors = {}, []
    for u in ko:
        m = master.get(u['id'])
        if m is None:
            errors.append(f"{u['id']}: 원문 단위가 없음"); continue
        k = u['ko']
        if not k.strip() or k == m['ja']:
            continue
        if sorted(TAG.findall(k)) != sorted(TAG.findall(m['ja'])):
            errors.append(f"{u['id']}: 태그가 원문과 다름")
        if re.search(r'[぀-ヿ]', TAG.sub('', k)):
            errors.append(f"{u['id']}: 가나가 남아 있음")
        for r in m['refs']:
            by_ref[r] = k
    if errors:
        raise SystemExit('번역 검사 실패:\n  ' + '\n  '.join(errors[:30]))
    return by_ref


def sjis_codes(b):
    i = 0
    while i < len(b):
        c = b[i]
        if c < 0x80 or 0xa0 <= c < 0xe0:
            i += 1
        else:
            yield b[i:i + 2]
            i += 2


def build_text(by_ref):
    fonts = {n: dfont.Font(src(n)) for n in FONTS}
    pending, kept = [], []   # (setter, 한국어), 그대로 남는 원문

    head, secs, tail = bdat.load(src('common/jp/bdat.bin'))
    tables = [bdat.Table(s) for s in secs]
    for t in tables:
        for r, row in enumerate(t.rows):
            for ci, col in enumerate(list(row.keys())):
                k = by_ref.get(f'bdat:{t.name}:{r}:{ci}')
                if k is None:
                    kept.append(row[col])
                else:
                    pending.append((lambda v, row=row, col=col: row.__setitem__(col, v), k))

    caps = {}
    for f in sorted(glob.glob(glob.escape(paths.SRC) + '/mov/jp/*.cap')):
        n = os.path.basename(f)[:-4]
        caps[n] = capfile.load(f)
        for i, ev in enumerate(caps[n][1]):
            k = by_ref.get(f'cap:{n}:{i}')
            if k is None:
                kept.append(ev[1])
            else:
                pending.append((lambda v, ev=ev: ev.__setitem__(1, v), k))

    sbs = {}
    for f in sorted(glob.glob(glob.escape(paths.SRC) + '/script/jp/*.sb')):
        n = os.path.basename(f)[:-3]
        sbs[n] = sbfile.SB(f)
        for j, s in enumerate(sbs[n].strs):
            k = by_ref.get(f'sb:{n}:{j}')
            if k is None:
                kept.append(s)
            else:
                pending.append((lambda v, sb=sbs[n], j=j: sb.strs.__setitem__(j, v), k))
    if len(caps) != 65 or len(sbs) != 83:
        raise SystemExit(f'자막 {len(caps)}/65, 스크립트 {len(sbs)}/83 개만 찾음 (경로 확인)')

    # 한글은 이제 쓰이지 않는 한자 자리에 넣는다 (남는 원문에 쓰인 한자는 건드리지 않음)
    used = {c for s in kept for c in sjis_codes(s)}
    free = [c for c, w, p in fonts['font.bin'].ents if len(c) == 2 and c[0] >= 0x88 and c not in used]
    m = korfont.Mapper(fonts['font.bin'], free)
    for setter, k in pending:
        setter(m.encode(k))

    secs = [t.build() for t in tables]
    for d in ('common/jp', 'mov/jp'):
        os.makedirs(os.path.join(paths.OUT_FILES, d), exist_ok=True)
    bdat.save(os.path.join(paths.OUT_FILES, 'common/jp/bdat.bin'), head, secs, tail)
    for n, (h, ev, tl) in caps.items():
        capfile.save(os.path.join(paths.OUT_FILES, f'mov/jp/{n}.cap'), h, ev, tl)
    for n, sb in sbs.items():
        put(f'script/jp/{n}.sb', sb.build())
    m.apply(fonts.values())
    for n, fo in fonts.items():
        put(n, bytes(fo.d))
    print(f'텍스트: 문자열 {len(pending)}곳, 한글 {len(m.map)}자 (남은 한자 자리 {len(m.free)})')


def build_images():
    targets = json.load(open(os.path.join(paths.DATA, 'textures.json'), encoding='utf-8'))
    patches = {}   # 파일 -> [(TPL 위치, 이미지 번호, 인코딩 결과, 항목)]
    for e in targets:
        im = Image.open(os.path.join(paths.ASSETS, e['name'] + '.png')).convert('RGBA')
        if im.size != (e['w'], e['h']):
            raise SystemExit(f"{e['name']}.png: 크기가 {e['w']}x{e['h']}가 아님 ({im.size[0]}x{im.size[1]})")
        data = gxenc.ENC[e['fmt']](im)
        for r in e['refs']:
            path, rest = r.split('@')
            base, idx = rest.split('#')
            patches.setdefault(path, []).append((int(base, 16), int(idx), data, e))
    for path, ps in sorted(patches.items()):
        outp = os.path.join(paths.OUT_FILES, path)
        raw = open(outp if os.path.exists(outp) else src(path), 'rb').read()
        comp = raw[:4] == b'SZ00'          # SZ00 = 헤더 0x20 + zlib
        d = bytearray(zlib.decompress(raw[0x20:]) if comp else raw)
        for base, idx, data, e in ps:
            info = {i: (w, h, f, off, nb) for i, w, h, f, off, nb, pal in gxtex.tpl_images(bytes(d), base)}
            w, h, f, off, nb = info[idx]
            assert (w, h, f) == (e['w'], e['h'], FMT[e['fmt']]) and nb == len(data), (path, base, idx)
            d[off:off + nb] = data
        if comp:
            d = b'SZ00' + len(d).to_bytes(4, 'little') + raw[8:0x20] + zlib.compress(bytes(d), 9)
        put(path, bytes(d))
    print(f'이미지: {len(targets)}장, 파일 {len(patches)}개')


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    paths.ensure_extract()
    if os.path.isdir(paths.OUT):
        shutil.rmtree(paths.OUT)
    os.makedirs(paths.OUT)
    build_text(load_translation())
    build_images()
    # 원본과 같은 파일은 지운다 (바뀐 파일만 남김)
    n = 0
    for root, _, fs in os.walk(paths.OUT_FILES):
        for f in fs:
            p = os.path.join(root, f)
            if open(p, 'rb').read() == open(src(os.path.relpath(p, paths.OUT_FILES)), 'rb').read():
                os.remove(p)
            else:
                n += 1
    print(f'바뀐 파일 {n}개 -> {paths.rel(paths.OUT)}')


if __name__ == '__main__':
    main()
