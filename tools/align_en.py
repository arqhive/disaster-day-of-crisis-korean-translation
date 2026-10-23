"""유럽판 영어 대사를 일본어 원문 단위에 붙인 검수용 대조표를 만든다.
결과: work/디재스터_대조_영어.json  [{id, 분류, 화자, 위치, 원문, 영어, 번역, 맞춘 방법}]
- 스크립트 .sb: 문자열 순서가 판마다 달라서, 음성 ID(sv_…)가 같은 줄끼리 → 없으면 (함수, 호출, 그 안의 순서)로 맞춘다.
- 컷신 자막 .cap: 이벤트 시작 프레임이 가장 가까운 영어 자막(±45프레임).
- 데이터 표 bdat: 같은 표·행·열. 유럽판 menu 표는 끝에 13행이 더 붙어 있을 뿐 앞 610행은 같은 순서(직접 대조함).
필요: 유럽판(RDZP01) DATA 파티션을 work/extract_eu 에 푼 것.
사용: python tools/align_en.py"""
import collections
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import bdat, capfile, paths, sbfile, sbrefs

EU = os.path.join(paths.WORK, 'extract_eu', 'files')
OUT = os.path.join(paths.WORK, '디재스터_대조_영어.json')


def en(b):
    return b.decode('cp1252', 'replace')


def sb_keys(sb):
    """문자열 번호 -> 짝짓기 열쇠 목록(앞쪽이 더 확실)"""
    use = sbrefs.usage(sb)
    order = collections.Counter()
    keys = {}
    for j in sorted(use, key=lambda j: j):
        if sbrefs.VOICE.match(sb.strs[j]) or re.fullmatch(rb'[A-Za-z0-9_.]*', sb.strs[j]):
            continue                       # 음성 ID·내부 이름은 대사가 아님
        u = use[j]
        k = []
        if u['voice']:
            k.append(('voice', u['voice']))
        base = (u['func'], u['call'])
        order[base] += 1
        k.append(('seq', base, order[base]))
        keys[j] = k
    return keys


def sb_map(name):
    jp, eu = os.path.join(paths.SRC, 'script', 'jp', name + '.sb'), os.path.join(EU, 'script', 'en', name + '.sb')
    if not os.path.exists(eu):
        return {}
    a, b = sbfile.SB(jp), sbfile.SB(eu)
    ka, kb = sb_keys(a), sb_keys(b)
    index = {}
    for j, ks in kb.items():
        for k in ks:
            index.setdefault(k, j)
    out = {}
    for j, ks in ka.items():
        for k in ks:
            if k in index:
                out[j] = (en(b.strs[index[k]]), k[0])
                break
    return out


def cap_map(name):
    jp, eu = os.path.join(paths.SRC, 'mov', 'jp', name + '.cap'), os.path.join(EU, 'mov', 'en', name + '.cap')
    if not os.path.exists(eu):
        return {}
    a, b = capfile.load(jp)[1], [e for e in capfile.load(eu)[1] if e[1]]
    out = {}
    for i, (fr, t) in enumerate(a):
        if not t or not b:
            continue
        near = min(b, key=lambda e: abs(e[0] - fr))
        if abs(near[0] - fr) <= 45:
            out[i] = (en(near[1]), f'frame{near[0] - fr:+d}')
    return out


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    master = {u['id']: u for u in json.load(open(paths.MASTER, encoding='utf-8'))}
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    h1, s1, _ = bdat.load(os.path.join(paths.SRC, 'common', 'jp', 'bdat.bin'))
    h2, s2, _ = bdat.load(os.path.join(EU, 'common', 'en', 'bdat.bin'))
    t_en = {t.name: t for t in (bdat.Table(s) for s in s2)}
    t_jp = {t.name: t for t in (bdat.Table(s) for s in s1)}
    sbs, caps = {}, {}
    rows, stat = [], collections.Counter()
    for u in ko:
        m = master[u['id']]
        got = None
        for r in m['refs']:
            kind, rest = r.split(':', 1)
            if kind == 'sb':
                n, j = rest.rsplit(':', 1)
                if n not in sbs:
                    sbs[n] = sb_map(n)
                got = sbs[n].get(int(j))
            elif kind == 'cap':
                n, i = rest.rsplit(':', 1)
                if n not in caps:
                    caps[n] = cap_map(n)
                got = caps[n].get(int(i))
            elif kind == 'bdat':
                tn, row, col = rest.split(':')
                a, b = t_jp.get(tn), t_en.get(tn)
                if a and b and len(b.rows) >= len(a.rows):
                    v = list(b.rows[int(row)].values())[int(col)]
                    got = (en(v) if isinstance(v, bytes) else str(v), 'bdat')
            if got:
                break
        stat[got[1].split('+')[0].split('-')[0] if got else '없음'] += 1
        rows.append(dict(id=u['id'], 분류=u['분류'], 화자=u['화자'], 위치=u['위치'], 원문=m['ja'], 영어=got[0] if got else '',
                         번역=u['ko'], 맞춘방법=got[1] if got else ''))
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(len(rows), '개 ->', paths.rel(OUT), dict(stat))


if __name__ == '__main__':
    main()
