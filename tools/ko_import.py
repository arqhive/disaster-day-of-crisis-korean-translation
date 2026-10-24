"""검수한 JSON(export_text.py 형식)의 번역·화자를 translation/ko.json 에 되돌려 넣는다. 원문은 저장하지 않는다.
- 한 원문이 여러 장면에 나오면 검수 JSON 에는 장면(ref)마다 한 줄이 있다. 같은 id 의 줄들을 모아
  가장 많이 쓰인 번역을 기본(ko)으로, 나머지를 위치별(ref -> 한국어)로 저장한다. 그래서 한 장면만 고쳐도 다른 장면은 그대로다.
- ref 가 "bdat" 인 줄은 데이터 표 위치 전부, "공통함수:이름" 은 모든 맵의 그 함수 위치를 뜻한다. 구분선(id 없음)은 건너뛴다.
- 화자도 장면마다 다르면 화자별(ref 묶음 이름 -> 화자)로 저장한다.
- 사용자가 덧붙인 칸(대상, 특이사항 등)은 메모(ref 묶음 이름 -> {칸: 값})로 저장해 다음 내보내기에 다시 붙는다.
- ref 가 없는 예전 형식(한 id 한 줄, 위치별 칸)도 읽는다.
사용: python tools/ko_import.py work/디재스터_텍스트.json"""
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import export_text
import paths


def merge(u, rows, refs, locof):
    """한 id 의 검수 줄들 -> (ko, 위치별). 줄의 ref 는 export_text.ref_group 이 만든 묶음 이름"""
    per = {}
    for r in rows:
        for x in refs:
            if export_text.ref_group(x, locof) == r['ref']:
                per[x] = r['번역']
    for x in refs:                      # 검수 JSON 에 없는 위치는 지금 값 유지
        per.setdefault(x, u.get('위치별', {}).get(x, u['ko']))
    count = collections.Counter(per[x] for x in refs)
    best = max(count.values())
    tops = [t for t, n in count.items() if n == best]
    base = u['ko'] if u['ko'] in tops else per[refs[0]] if per[refs[0]] in tops else tops[0]
    return base, {x: t for x, t in per.items() if t != base}


def speakers(u, rows):
    """한 id 의 검수 줄들 -> (화자, 화자별). 장면마다 화자가 다르면 줄의 ref(묶음 이름) -> 화자 로 저장"""
    per = {r['ref']: r.get('화자', '') for r in rows}
    count = collections.Counter(per.values())
    best = max(count.values())
    tops = [t for t, n in count.items() if n == best]
    base = u['화자'] if u['화자'] in tops else tops[0]
    return base, {k: v for k, v in per.items() if v != base}


BASE_FIELDS = {'id', 'ref', 'stage', '분류', '화자', '위치', '원문', '영어', '번역', '위치별'}


def notes(u, rows):
    """검수 줄에 사용자가 덧붙인 칸(대상, 특이사항 등) -> 메모 {ref 묶음 이름: {칸: 값}}. 빈 값은 지운다"""
    memo = dict(u.get('메모', {}))
    for r in rows:
        extra = {k: v for k, v in r.items() if k not in BASE_FIELDS and v not in ('', None)}
        key = r.get('ref', '')
        if extra:
            memo[key] = extra
        else:
            memo.pop(key, None)
    return memo


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    if len(sys.argv) < 2:
        raise SystemExit('사용법: python tools/ko_import.py <검수 JSON>')
    rows = collections.defaultdict(list)
    for r in json.load(open(sys.argv[1], encoding='utf-8')):
        if 'id' in r:                   # 구분선 항목은 건너뜀
            rows[r['id']].append(r)
    master = {u['id']: u for u in json.load(open(paths.MASTER, encoding='utf-8'))}
    locof = export_text.ref_locations()
    ko = json.load(open(paths.KO_JSON, encoding='utf-8'))
    changed = 0
    for u in ko:
        rs = rows.get(u['id'])
        if not rs:
            continue
        new = dict(u)
        if 'ref' in rs[0]:
            new['ko'], each = merge(u, rs, master[u['id']]['refs'], locof)
            new['화자'], who = speakers(u, rs)
        else:
            new['ko'], each = rs[0]['번역'], rs[0].get('위치별') or {}
            new['화자'], who = rs[0].get('화자', u['화자']), u.get('화자별', {})
        memo = notes(u, rs)
        for k, v in (('위치별', each), ('화자별', who), ('메모', memo)):
            new.pop(k, None)
            if v:
                new[k] = v
        changed += new != u
        u.clear()
        u.update(new)
    json.dump(ko, open(paths.KO_JSON, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)
    print(f'{changed}개 바뀜 -> {paths.rel(paths.KO_JSON)}')


if __name__ == '__main__':
    main()
