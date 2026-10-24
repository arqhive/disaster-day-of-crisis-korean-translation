"""번역 검수용 JSON 내보내기: 원문(게임에서 추출)과 번역(translation/ko.json)을 나란히 담는다.
결과: work/디재스터_텍스트.json  [{id, stage, 분류, 화자, 위치, 원문, 번역}] — stage(00 프롤로그~23, 인터미션·사격장·공통·미사용) 순서로 정렬(tools/data/stages.json)
고친 뒤에는 python tools/ko_import.py work/디재스터_텍스트.json 으로 되돌려 넣는다.
사용법: python tools/export_text.py"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, extract_text

OUT = os.path.join(paths.WORK, '디재스터_텍스트.json')
STAGES = os.path.join(HERE, 'data', 'stages.json')


def stage_names():
    st = json.load(open(STAGES, encoding='utf-8'))
    names = {e['stage']: (f"STAGE {e['stage']}  {e['이름']}" if e['stage'] != '00' else e['이름']) for e in st['스테이지']}
    names.update(st['구분 이름'])
    return names


def stage_keys():
    """ref -> (정렬 순서, stage, 스테이지 안 파일 순서, 파일 안 번호). 대응표는 tools/data/stages.json"""
    st = json.load(open(STAGES, encoding='utf-8'))
    order = {s: i for i, s in enumerate(st['순서'])}
    where = {}
    for e in st['스테이지']:
        for i, n in enumerate(e['cap'] + e['sb']):
            where[n] = (e['stage'], i)
    for n, s in st['파일'].items():
        where[n] = (s, 0)

    def key(ref, loc):
        kind, rest = ref.split(':', 1)
        name, idx = (rest.rsplit(':', 1) + ['0'])[:2] if kind in ('cap', 'sb') else ('', '0')
        stage, pos = where.get(name, (st['나머지'], 0))
        func = loc.split()[1] if kind == 'sb' and len(loc.split()) > 1 else ''
        if func in st['함수']:
            stage, pos = st['함수'][func], 0
        return (order[stage], stage, pos, name, int(idx) if idx.isdigit() else 0)
    return key


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if not os.path.exists(paths.MASTER):
        extract_text.main()
    master = {u['id']: u for u in json.load(open(paths.MASTER, encoding='utf-8'))}
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    keyof = stage_keys()
    rows = []
    for u in ko:
        key = min(keyof(r, u['위치']) for r in master[u['id']]['refs'])
        rows.append((key, dict(id=u['id'], stage=key[1], 분류=u['분류'], 화자=u['화자'], 위치=u['위치'], 원문=master[u['id']]['ja'],
                               번역=u['ko'], **({'위치별': u['위치별']} if u.get('위치별') else {}))))
    names = stage_names()
    out, cur = [], None
    for _, r in sorted(rows, key=lambda x: x[0]):
        if r['stage'] != cur:                # 스테이지가 바뀌는 곳에 구분선 항목(id 없음, ko_import 가 건너뜀)
            cur = r['stage']
            out.append({'구분': f'======== {names[cur]} ========'})
        out.append(r)
    rows = out
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(sum('id' in r for r in rows), '개 ->', paths.rel(OUT))


if __name__ == '__main__':
    main()
