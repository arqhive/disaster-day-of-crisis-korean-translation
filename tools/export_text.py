"""번역 검수용 JSON 내보내기: 원문(게임에서 추출)과 번역(translation/ko.json)을 나란히 담는다.
결과: work/디재스터_텍스트.json  [{id, ref, stage, 분류, 화자, 위치, 원문, 영어, 번역}] (영어는 유럽판, work/extract_eu 가 있을 때)
- 같은 원문이 여러 장면에 나오면 장면(ref)마다 한 줄. 고치면 그 장면에만 들어간다
  (데이터 표 위치는 ref "bdat", 모든 맵에 복사된 공통 함수는 ref "공통함수:이름" 한 줄).
- stage(00 프롤로그~23, 인터미션·사격장·공통·미사용) 순, 스테이지 안에서는 맵 순서 → 스크립트 코드 위치 순(tools/data/stages.json)
고친 뒤에는 python tools/ko_import.py work/디재스터_텍스트.json 으로 되돌려 넣는다.
사용법: python tools/export_text.py"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths, extract_text

OUT = os.path.join(paths.WORK, '디재스터_텍스트.json')
STAGES = os.path.join(HERE, 'data', 'stages.json')


def stage_names():
    st = json.load(open(STAGES, encoding='utf-8'))
    names = {e['stage']: (f"STAGE {e['stage']}  {e['이름']}" if e['stage'] != '00' else e['이름']) for e in st['스테이지']}
    names.update(st['구분 이름'])
    return names


def code_positions():
    """스크립트마다 (문자열 번호 -> 처음 쓰이는 코드 위치, 컷신 이름 -> movie.play 코드 위치)"""
    import glob, re, sbfile, sbrefs
    out = {}
    for f in glob.glob(os.path.join(glob.escape(paths.SRC), 'script', 'jp', '*.sb')):
        sb = sbfile.SB(f)
        _, rs = sbrefs.refs(sb)
        first, movie = {}, {}
        for pos, j, _ in rs:
            first.setdefault(j, pos)
            if re.fullmatch(rb'C\d{4}[a-z]?', sb.strs[j]):
                movie.setdefault(sb.strs[j].decode(), pos)
        out[os.path.basename(f)[:-3]] = (first, movie)
    return out


# 모든 맵 스크립트에 똑같이 복사된 공통 함수: 위치마다 나누지 않고 한 줄로 묶는다
COMMON_FUNCS = {'FIRST_TALK_GF', 'FREE_TALK_GF', 'lung', 'JUMPWAIT', 'SP_BONUS', 'GOAL_ON', 'GOAL_OFF', 'BATU', 'IDGroupSetUp',
                'check_life', 'E_MAX', 'stm_comp', 'staminascheck', 'staminascheck0', 'STAMINAScheck', 'STAMINAScomplete'}


def ref_group(ref, locof):
    """검수 줄 하나가 맡는 위치 묶음 이름: 컷신·스크립트 위치는 그 ref 자체, 공통 함수는 "공통함수:이름", 데이터 표는 "bdat" """
    if ref.startswith('cap:'):
        return ref
    if ref.startswith('sb:'):
        func = (locof.get(ref, '').split() + ['', ''])[1]
        if func in COMMON_FUNCS or func.startswith(('STAGE_END_', 'SHINDO_', 'Shake')) or func in ('StopImpact',):
            return '공통함수:' + func
        return ref
    return 'bdat'


def ref_locations():
    """cap/sb ref -> 사람이 읽는 위치 (컷신 프레임, 스크립트 함수·호출)"""
    import glob, capfile, sbfile, sbrefs
    out = {}
    for f in glob.glob(os.path.join(glob.escape(paths.SRC), 'mov', 'jp', '*.cap')):
        n = os.path.basename(f)[:-4]
        for i, (fr, t) in enumerate(capfile.load(f)[1]):
            out[f'cap:{n}:{i}'] = f'{n} {fr}f'
    for f in glob.glob(os.path.join(glob.escape(paths.SRC), 'script', 'jp', '*.sb')):
        n = os.path.basename(f)[:-3]
        for j, u in sbrefs.usage(sbfile.SB(f)).items():
            out[f'sb:{n}:{j}'] = ' '.join(x for x in (n, u['func'], u['call']) if x)
    return out


def stage_keys():
    """ref -> (정렬 순서, stage, 맵 순서, 코드 위치, 컷신 안 번호). 대응표는 tools/data/stages.json.
    스테이지 안에서는 맵 순서(시작 맵부터 mapJump 경로) → 스크립트 코드 위치 순. 컷신 자막은 그 컷신을 트는 코드 위치에 끼운다."""
    st = json.load(open(STAGES, encoding='utf-8'))
    order = {s: i for i, s in enumerate(st['순서'])}
    pos = code_positions()
    sb_at, cap_at = {}, {}
    for e in st['스테이지']:
        for i, n in enumerate(e['sb']):
            sb_at[n] = (e['stage'], i)
        for c in e['cap']:
            play = [(i, pos[n][1][c]) for i, n in enumerate(e['sb']) if c in pos.get(n, ({}, {}))[1]]
            cap_at[c] = (e['stage'],) + (min(play) if play else (len(e['sb']), 0))
    for n, s in st['파일'].items():
        sb_at[n] = (s, 0)
    rest = st['나머지']

    def key(ref, loc):
        kind, body = ref.split(':', 1)
        if kind == 'cap':
            name, idx = body.rsplit(':', 1)
            stage, mi, p = cap_at.get(name, (rest, 0, 0))
            return (order[stage], stage, mi, p, int(idx))
        if kind == 'sb':
            name, idx = body.rsplit(':', 1)
            stage, mi = sb_at.get(name, (rest, 0))
            func = loc.split()[1] if len(loc.split()) > 1 else ''
            if func in st['함수']:
                stage, mi = st['함수'][func], 0
            return (order[stage], stage, mi, pos.get(name, ({}, {}))[0].get(int(idx), 0), 0)
        return (order[rest], rest, 0, 0, 0)
    return key


FIXED = ('id', 'ref', 'stage', '분류', '화자', '위치', '원문', '영어', '번역')


def unimported(built):
    """지금 검수 JSON 에서 새로 만들 줄과 번역·화자·덧붙인 칸이 다른 줄(사용자가 고치고 아직 안 넣은 것)의 id 목록"""
    if not os.path.exists(OUT):
        return []
    try:
        old = [r for r in json.load(open(OUT, encoding='utf-8')) if 'id' in r]
    except ValueError:
        return ['(검수 JSON 문법 오류)']
    new = {(r['id'], r['ref']): r for r in built}
    extra = lambda r: {k: v for k, v in r.items() if k not in FIXED and v not in ('', None)}
    out = []
    for r in old:
        b = new.get((r['id'], r.get('ref')))
        if b and (r['번역'] != b['번역'] or r['화자'] != b['화자'] or extra(r) != extra(b)):
            out.append(r['id'])
    return out


def build_rows(ko, master):
    """ko.json -> 검수 줄 목록(스테이지·시간순, 구분선 없음)"""
    keyof = stage_keys()
    locof = ref_locations()
    import align_en
    english = align_en.english_lookup()
    rows = []
    for u in ko:
        each = u.get('위치별', {})
        refs = master[u['id']]['refs']
        # 같은 원문이 여러 장면에 나오면 장면(ref)마다 한 줄. 고치면 그 장면에만 들어간다(ko_import 가 기본·위치별로 다시 묶음).
        # 데이터 표(bdat) 위치와 모든 맵에 복사된 공통 함수(에릭 대화, 스태미너스 등)는 한 줄로 묶는다.
        groups = collections.OrderedDict()
        for r in refs:
            groups.setdefault(ref_group(r, locof), []).append(r)
        for ref, g in groups.items():
            loc = locof.get(g[0], u['위치']) if ref.startswith(('cap:', 'sb:')) else u['위치']
            key = min(keyof(r, locof.get(r, u['위치'])) for r in g)
            got = next((x for x in map(english, g) if x), None)
            rows.append((key, dict(id=u['id'], ref=ref, stage=key[1], 분류=u['분류'], 화자=u.get('화자별', {}).get(ref, u['화자']),
                                   위치=loc, 원문=master[u['id']]['ja'], 영어=got[0] if got else '', 번역=each.get(g[0], u['ko']),
                                   **u.get('메모', {}).get(ref, {}))))   # 사용자가 덧붙인 칸(대상, 특이사항 등)
    return [r for _, r in sorted(rows, key=lambda x: x[0])]


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if not os.path.exists(paths.MASTER):
        extract_text.main()
    master = {u['id']: u for u in json.load(open(paths.MASTER, encoding='utf-8'))}
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    rows = build_rows(ko, master)
    if '--force' not in sys.argv:
        pending = unimported(rows)
        if pending:
            raise SystemExit(f'검수 JSON 에 ko.json 에 안 넣은 수정이 {len(pending)}줄 있어 덮어쓰지 않음 '
                             f'(예: {", ".join(pending[:5])}). 먼저 ko_import.py 로 넣거나 --force')
    names = stage_names()
    out, cur = [], None
    for r in rows:
        if r['stage'] != cur:                # 스테이지가 바뀌는 곳에 구분선 항목(id 없음, ko_import 가 건너뜀)
            cur = r['stage']
            out.append({'구분': f'======== {names[cur]} ========'})
        out.append(r)
    rows = out
    json.dump(rows, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print(sum('id' in r for r in rows), '개 ->', paths.rel(OUT))


if __name__ == '__main__':
    main()
