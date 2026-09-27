"""디스크 안 모든 TPL 이미지를 중복 없이 PNG 로 뽑는다 (.tpl/.rec + SZ00 압축 파일).
번역할 이미지를 찾을 때 쓴 조사 도구. 결과: work/tex/<키>.png, work/tex_index.json.
사용법: python tools/dump_textures.py"""
import hashlib, json, os, sys, zlib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gxtex, paths

R = paths.SRC
OUT = os.path.join(paths.WORK, 'tex')
MAGIC = b'\x00\x20\xaf\x30'


def sources():
    for root, _, fs in os.walk(R):
        for f in fs:
            p = os.path.join(root, f)
            rel = os.path.relpath(p, R).replace(os.sep, '/')
            if f.lower().endswith(('.sfd', '.sad', '.spd', '.sb', '.t', '.cap')) or f in ('font.bin', 'CapFont.bin', 'MenuFont.bin'):
                continue
            d = open(p, 'rb').read()
            if d[:4] == b'SZ00':
                d = zlib.decompress(d[0x20:])
            if MAGIC in d:
                yield rel, d


def main():
    os.makedirs(OUT, exist_ok=True)
    index = {}
    total = 0
    for rel, d in sources():
        p = d.find(MAGIC)
        while p >= 0:
            try:
                imgs = list(gxtex.tpl_images(d, p))
            except Exception:
                imgs = []
            for i, w, h, f, off, nb, pal in imgs:
                total += 1
                key = hashlib.sha1(bytes([f]) + w.to_bytes(2, 'big') + h.to_bytes(2, 'big') + d[off:off + nb]).hexdigest()[:16]
                e = index.get(key)
                if e is None:
                    e = index[key] = dict(w=w, h=h, fmt=gxtex.NAME[f], refs=[])
                    try:
                        gxtex.decode(d[off:off + nb], w, h, f, pal).save(f'{OUT}/{key}.png')
                    except Exception as ex:
                        e['err'] = str(ex)
                if len(e['refs']) < 20:
                    e['refs'].append(f'{rel}@{p:x}#{i}')
                e['n'] = e.get('n', 0) + 1
            p = d.find(MAGIC, p + 4)
    json.dump(index, open(os.path.join(paths.WORK, 'tex_index.json'), 'w', encoding='utf-8'), indent=0)
    print('images', total, 'unique', len(index))


if __name__ == '__main__':
    main()
