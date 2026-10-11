"""요청서.md 쓰기(gpt_prepare.py 가 부른다). 공통 규칙 + 분류별 프롬프트 + 번호별 표."""
import difflib
import json
import os
import re

COMMON = """닌텐도 Wii 게임 「디재스터 데이 오브 크라이시스」의 그림 글씨를 한국어판으로 바꾸는 작업이야.
네가 만든 PNG를 내가 프로그램으로 줄이고 다시 압축해서 게임에 넣을 거라서, 아래 규칙을 반드시 지켜야 해.

[필수 규칙]
1. 결과는 반드시 PNG. JPG 금지.
2. 첨부한 원본과 가로세로 비율을 똑같이 맞춰. 크기는 원본의 2배 이상 크게 만들어.
3. 내가 "투명 배경"이라고 한 그림은 배경을 완전히 투명하게. 흰 배경·체크무늬·단색 배경 금지.
   "검정 바탕 흰 글씨"라고 한 그림은 바탕 전체를 순수한 검정(#000000), 글씨는 순수한 흰색(#FFFFFF)으로만.
   "불투명"이라고 한 그림은 원본의 배경(사진·색·무늬)을 그대로 살리고 글자만 바꿔.
   "그림(가장자리 투명)"은 원본 그림(배경 포함)을 그대로 살리고 글자만 바꿔. 투명한 가장자리는 내가 맞춰 줄게.
4. 그림에 없는 것은 그리지 마. 새 테두리 상자, 받침 판, 배경 장식, 워터마크, 서명 금지.
5. 원본의 디자인을 최대한 따라 해: 서체 종류와 굵기, 글자 색, 외곽선·그림자, 정렬(가운데/왼쪽), 줄 간격, 위아래 여백.
6. 글자를 지운 자리는 주변 배경과 똑같이 자연스럽게 채워. 지운 자국(밝거나 어두운 얼룩, 네모 자국)이 남으면 안 돼.
7. 한국어 맞춤법과 글자 모양을 정확하게. 받침이 빠지거나 획이 붙거나 깨지면 안 돼.
   다 만든 뒤에 글자를 한 자씩 확인하고, 틀렸으면 다시 만들어.
8. 내가 준 한국어 문구를 그대로 써. 띄어쓰기·문장부호·가운뎃점(·)도 바꾸지 마.
9. 원본에 있는 영어·숫자·기호와 버튼 그림(Ⓐ Ⓑ Ⓩ ＋ 등)은 그대로 둬.

이해했으면 "확인"이라고만 답하고, 내가 그림을 보낼 때까지 기다려."""

ONE = """첨부한 첫 번째 그림(원본)을 한국어로 다시 만들어 줘. {bg}, 게임 크기 {w}×{h}(비율 {ratio}).
- 문구: 「{ko}」
- 두 번째 그림은 지금 쓰는 한국어판이야. 문구와 줄 나눔은 이것과 똑같이, 디자인은 원본 수준으로."""

GROUPS = {
    '튜토리얼': '튜토리얼 설명 화면이야. 위쪽 베이지색 띠에 작은 분류 글씨와 큰 제목, 그 아래 검정 바탕에 큰 소제목, '
               '흰 테두리 상자 안에 설명 글이 있어. 빨간 주의 표시 줄과 전구 힌트 줄도 있어. 그림·아이콘·버튼 그림·화면 사진·'
               '테두리는 그대로 두고 글자만 바꿔. 원본은 가는 고딕이니 비슷한 굵기로.',
    '로딩 힌트': '로딩 중에 나오는 힌트 화면이야. 왼쪽 위 전구 아이콘 옆에 흰 글씨 힌트가 한두 줄(·로 시작), 가운데 게임 장면 사진 액자, '
              '배경은 어두운 갈색 질감이야. 전구·HINTS 영어 글씨·사진·배경은 그대로 두고 힌트 글자만 바꿔.',
    '인물·장소 소개': '스테이지 시작 전 로딩 화면이야. 인물·장소 사진 위 밝게 번진 영역에 굵은 이름 한 줄, 그 아래 밑줄, '
                 '설명 몇 줄(검정 고딕)이 있어. DISASTER 로고와 사진은 그대로 두고 글자만 바꿔.',
    '스트랩 경고': 'Wii 리모컨 스트랩·눈차크 사용 안내 화면이야(흰 바탕). 손·리모컨·아이콘 그림과 Nintendo 표시는 그대로, '
               '파란 글씨·빨간 강조 글씨는 원본 색 그대로. 일본어 위의 작은 읽는 법 글씨(후리가나)는 한국어에서는 빼.',
    '스테이지 제목·경고 띠': '스테이지 시작 때 화면에 겹쳐 나오는 제목 띠(작은 지명 + 큰 재해 이름)와 경고 띠(흰 테두리 상자 안 글자)야. '
                      '실제 크기가 높이 32픽셀 안팎으로 아주 작아지니 획이 너무 가늘지 않게 해. 원본처럼 흰 글씨.',
    '홈 버튼 메뉴': 'Wii HOME 버튼 메뉴의 버튼 글씨야(검정 바탕 흰 글씨). Wii 본체 메뉴처럼 깔끔하고 둥근 고딕, 가운데 정렬.',
}


def _known():
    """번역 JSON의 한 줄짜리 문구 — OCR 오독을 고치는 사전"""
    import paths
    out = set()
    for u in json.load(open(paths.KO_JSON, encoding='utf-8')):
        for line in re.sub(r'<(?!n>)[^>]*>', '', u['ko']).split('<n>'):
            line = line.strip()
            if 1 < len(line) <= 40:
                out.add(line)
    return sorted(out)


def fix_line(t, known, joined):
    """OCR 한 줄을 가장 비슷한 번역문 줄로 바꾼다(비슷한 게 없으면 그대로) → (문구, 고쳤는지)"""
    norm = lambda s: re.sub(r'[^0-9A-Za-z가-힣]', '', s)
    if not norm(t) or t in known or any(norm(t) in k for k in joined):
        return t, False
    digits = lambda s: re.sub(r'\D', '', s)
    cand = [k for k in known if len(norm(k)) == len(norm(t)) and digits(k) == digits(t)]
    if not cand:
        return t, False
    best = max(cand, key=lambda k: difflib.SequenceMatcher(None, norm(t), norm(k)).ratio())
    if norm(best) == norm(t) or difflib.SequenceMatcher(None, norm(t), norm(best)).ratio() < 0.75:
        return t, False
    rep = iter(norm(best))
    return ''.join(next(rep) if re.match(r'[0-9A-Za-z가-힣]', c) else c for c in t), True


def _rel(p):
    return '`' + p.replace('/', '\\') + '`' if p else ''


def write(items, path):
    gpt_dir = os.path.dirname(path)
    ocr = {}
    if os.path.exists(os.path.join(gpt_dir, '_ocr.json')):
        ocr = json.load(open(os.path.join(gpt_dir, '_ocr.json'), encoding='utf-8'))
    known = _known()
    joined = [re.sub(r'[^0-9A-Za-z가-힣]', '', k) for k in known]
    o = ['# GPT 그림 재작업 요청서 (디재스터 데이 오브 크라이시스 한글 패치)\n',
         'GPT(ChatGPT 이미지 생성)에게 그림을 다시 그려 달라고 할 때 쓰는 프롬프트와 번호별 표입니다.',
         f'지금 패치에 들어간 그림 글씨 **{len(items)}장**을 모두 준비했습니다. **필요한 것만 골라서 맡기면 됩니다.**\n',
         '## 폴더\n', '| 폴더 | 내용 |', '|---|---|',
         '| `work\\GPT\\원본\\` | GPT에 첨부할 원본(일본판). 작은 그림은 픽셀 그대로 키운 `_N배` 판입니다. |',
         '| `work\\GPT\\참고\\` | 지금 패치에 들어간 한글판(`_현재한글판`). 문구를 GPT에게 보여 줄 때 같이 첨부합니다. |',
         '| `work\\GPT\\결과\\` | **GPT가 만든 PNG를 여기에 저장합니다.** 표의 「저장할 이름」을 그대로 써 주세요. |',
         '| `work\\GPT\\비교\\` | 반영하면 원본 \\| 이전 \\| 반영 비교 시트가 생깁니다. |',
         '| `work\\GPT\\목록.json` | 번호 → 에셋 이름·게임 크기·형식·배경 종류(도구용) |\n',
         '결과를 저장한 뒤 `python tools/gpt_import.py`(또는 `python tools/gpt_import.py T001 B03`처럼 번호 지정)를 실행하면 '
         '게임 크기에 맞춰 `tools/assets`에 넣고 비교 시트를 만듭니다. 바꾸기 전 그림은 `work\\GPT\\이전_assets\\`에 남습니다. 빌드는 따로 합니다.',
         '- 불투명 그림(튜토리얼·로딩 화면 등)은 전체를 게임 크기로 줄입니다. 비율이 조금 다르면 가운데를 잘라 맞춥니다.',
         '- 투명 배경 그림(제목 띠)은 GPT 그림의 내용 덩어리를 지금 한글판 덩어리 자리에 비율 유지로 맞춥니다. 배경이 채워져 와도 귀퉁이 색을 지워 받습니다.',
         '- 검정 바탕 흰 글씨 그림(홈 버튼)은 밝기만 씁니다(색이 섞여 와도 흑백으로 바꿈).',
         '- GPT 결과가 이미 게임 크기와 같으면 그대로 씁니다.',
         '- 「현재 문구」는 지금 한글판을 OCR로 읽은 **초안**입니다. 번역문에 있는 비슷한 줄로 고친 곳은 ✎ 표시가 있습니다. '
         '틀린 글자가 남아 있을 수 있으니 보내기 전에 참고 그림과 맞는지 확인해 주세요. 줄은 ` / `로 나눴습니다.\n',
         '---\n', '## 1. 맨 처음 한 번만 붙여 넣을 공통 규칙\n', '```', COMMON, '```\n', '---\n',
         '## 2. 그림 한 장 요청 틀\n',
         '첨부: 표의 「첨부(원본)」과 「참고(현재)」 두 장. 표의 값으로 `{ }` 칸을 채워 보냅니다.\n',
         '```', ONE, '```\n',
         '같은 분류를 여러 장 맡길 때는 "앞에서 만든 그림과 같은 서체·굵기로"라고 덧붙이면 모양이 통일됩니다.\n',
         '---\n', '## 3. 분류별 표\n']
    groups = {}
    for it in items:
        groups.setdefault(it['group'], []).append(it)
    for g in [g for g in GROUPS if g in groups]:
        its = groups[g]
        pre = re.match(r'[A-Z]+', its[0]['id']).group()
        o.append(f'### {pre} {g} ({len(its)}장)\n')
        o.append(f'추가로 붙일 말: "{GROUPS[g]}"\n')
        o.append('| 번호 | 그림 | 게임 크기 | 배경 | 현재 문구(OCR 초안) | 첨부(원본) | 참고(현재) | 저장할 이름 |')
        o.append('|---|---|---|---|---|---|---|---|')
        for i in its:
            lines, fixed = [], False
            for x in ocr.get(i['id'] + '.png', '').split('\n'):
                x = re.sub(r"[\[\]\\|]", '', x).strip()
                if not re.search('[가-힣]', x):
                    continue
                y, f = fix_line(x, known, joined)
                lines.append(y)
                fixed |= f
            i['ko_hint'] = ' / '.join(lines)
            t = (i['ko_hint'].replace('|', '｜') + (' ✎' if fixed else '')) if lines else '(읽지 못함)'
            o.append(f"| {i['id']} | {i['name']} | {i['size'][0]}×{i['size'][1]} | {i['bg']} | {t} | {_rel(i['attach'])} | "
                     f"{_rel(i.get('ref'))} | `{i['save_as']}` |")
        o.append('')
    open(path, 'w', encoding='utf-8').write('\n'.join(o) + '\n')
