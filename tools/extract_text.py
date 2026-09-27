"""원문 단위 추출: .sb 대사 / bdat 메뉴·데이터 / .cap 컷신 자막 -> work/master.json.
같은 원문은 한 단위(id)로 묶고, 게임 안 위치(refs)를 모두 기록한다. id 는 추출 순서로 정해지며 translation/ko.json 의 id 와 같다."""
import glob, json, os, re
import paths
import sbfile, sbrefs, bdat, capfile

R = paths.SRC + '/'
STAGE_ORDER = ['agu', 'blu', 'ros', 'air', 'rai', 'por', 'fer', 'ext', 'gameover', 'result', 'presen']
UNUSED = {'-nym_00', 'kns_05_old', 'roo08_00', 'ssk_00_b'}  # .t 없음 = 게임이 안 부름(추정)

CALL_CAT = {
    'menu.caption': '대사', 'menu.playRadio': '무전·방송', 'menu.radio': '무전·방송',
    'menu.tutorialmes': '안내', 'menu.sysmes': '안내', 'menu.sysmesEx': '안내',
    'menu.action': '행동 버튼', 'menu.actionOnce': '행동 버튼', 'eve.setSuccessFailEvent': '행동 버튼',
    'deb.put': '디버그', 'deb.msg': '디버그',
}
VOICE_SPK = {'gray': '레이', 'rsc': '레이', 'eric': '에릭', 'dj': 'DJ', 'radio': '라디오 방송', 'entbtl': '적 병사'}


def jp(b):
    return any(c >= 0x80 for c in b)


def dec(b):
    return b.decode('cp932')


def sb_key(path):
    n = os.path.basename(path)[:-3]
    pre = re.match(r'[a-z]+', n.lstrip('-'))
    pre = pre.group() if pre else n
    return (STAGE_ORDER.index(pre) if pre in STAGE_ORDER else 99, n)


def guess_speaker(text, cat, voice, func):
    if cat == '안내':
        return '(안내)', '안내문'
    if cat == '행동 버튼':
        return '(버튼)', '행동 표시'
    if voice:
        p = voice.split('_')[1].lower()
        if p in VOICE_SPK:
            return VOICE_SPK[p], f'음성 {voice}'
    if 'Mayor' in func:
        return '타운젠드 시장', f'함수 {func}'
    if 'Lisa' in func:
        return '리사(추정)', f'함수 {func}'
    if p_ := (voice.split('_')[1].lower() if voice else ''):
        if p_.startswith('boss') or p_ in ('bradio', 'brdosp', 'brdobu'):
            return 'STORM', f'음성 {voice}'
    if text.startswith('<c=npc>'):
        return 'NPC', '색 태그 npc'
    if cat == '대사' and not voice and re.sub(r'<[^>]*>', '', text)[:1] in '（(':
        return '레이(속마음)', '괄호·무음성'
    return '', (f'음성 {voice}' if voice else '')


def main():
    paths.ensure_extract()
    units = {}   # ja text -> unit
    order = []

    def add(ja, loc, cat, spk='', why='', ctx=''):
        u = units.get(ja)
        if u is None:
            u = units[ja] = dict(ja=ja, ko='', cat=cat, speaker=spk, why=why, ctx=ctx, refs=[])
            order.append(ja)
        else:
            # 더 정보가 많은 쪽을 대표로
            if not u['speaker'] and spk:
                u['speaker'], u['why'] = spk, why
            if u['cat'] == '디버그' and cat != '디버그':
                u['cat'] = cat
        u['refs'].append(loc)

    # 1) bdat (메뉴가 먼저 보이도록)
    head, secs, tail = bdat.load(R + 'common/jp/bdat.bin')
    for si, s in enumerate(secs):
        t = bdat.Table(s)
        for r, row in enumerate(t.rows):
            for ci, (col, v) in enumerate(row.items()):
                if jp(v):
                    add(dec(v), f'bdat:{t.name}:{r}:{ci}', '메뉴·데이터', ctx=t.name)

    # 2) 컷신 자막
    for f in sorted(glob.glob(glob.escape(R) + 'mov/jp/*.cap')):
        n = os.path.basename(f)[:-4]
        for i, (fr, v) in enumerate(capfile.load(f)[1]):
            if jp(v):
                add(dec(v), f'cap:{n}:{i}', '컷신 자막', ctx=f'{n} {fr}f')

    # 3) 스크립트
    for f in sorted(glob.glob(glob.escape(R) + 'script/jp/*.sb'), key=sb_key):
        n = os.path.basename(f)[:-3]
        s = sbfile.SB(f)
        use = sbrefs.usage(s)
        for j, v in enumerate(s.strs):
            if not jp(v):
                continue
            u = use.get(j, {})
            call = u.get('call', '')
            cat = CALL_CAT.get(call, '기타')
            if n in UNUSED:
                cat = '미사용 추정' if cat != '디버그' else cat
            text = dec(v)
            spk, why = guess_speaker(text, cat, u.get('voice', ''), u.get('func', ''))
            add(text, f'sb:{n}:{j}', cat, spk, why, ctx=f"{n} {u.get('func', '')} {call}".strip())

    # 미사용 추정 파일에만 있는 줄은 그대로 '미사용 추정', 다른 곳에도 쓰이면 그쪽 분류 유지
    for ja in order:
        u = units[ja]
        if u['cat'] == '미사용 추정' and any(not r.startswith('sb:') or r.split(':')[1] not in UNUSED for r in u['refs']):
            u['cat'] = '대사'

    master = []
    for k, ja in enumerate(order, 1):
        u = units[ja]
        master.append(dict(id=f'T{k:05d}', **u))
    json.dump(master, open(paths.MASTER, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return master


if __name__ == '__main__':
    import collections, sys
    m = main()
    tag = re.compile(r'<[^>]*>')
    st = collections.defaultdict(lambda: [0, 0])
    for u in m:
        st[u['cat']][0] += 1
        st[u['cat']][1] += len(tag.sub('', u['ja']))
    for k, (a, b) in st.items():
        print(f'{k}\t{a}줄\t{b}자')
    spk = collections.Counter(u['speaker'] for u in m if u['cat'] == '대사')
    print('대사 화자', spk.most_common())
