"""GPT 그림 재작업 준비: work/GPT/ 에 요청 묶음을 만든다(돌격 패미컴 워즈 VS·어나더 코드 R 방식).
  원본/  GPT에 첨부할 원본(일본판). 작은 그림은 픽셀 그대로 키운 _N배 판으로 둔다.
  참고/  지금 패치에 들어간 한글판(_현재한글판, tools/assets)
  결과/  GPT가 만든 PNG를 「저장할 이름」으로 저장하는 곳
  비교/  gpt_import.py 가 원본 | 이전 | 반영 비교 시트를 만드는 곳
  목록.json  번호 → 에셋 이름·게임 크기·형식·배경 종류·들어가는 곳
  요청서.md  GPT 프롬프트와 번호별 표 (현재 문구는 OCR 초안)
대상은 tools/data/textures.json 의 그림 전부(209장). 필요한 것만 골라 맡기면 된다.
사용: python tools/gpt_prepare.py            (OCR 포함)
      python tools/gpt_prepare.py --no-ocr   (OCR 없이, 이전 _ocr.json 이 있으면 그것을 씀)"""
import json
import math
import os
import shutil
import subprocess
import sys
import zlib

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gpt_request
import gxtex
import paths

GPT = os.path.join(paths.WORK, 'GPT')
# textures.json 분류 → (번호 머리글자, 요청서 분류 이름)
GROUPS = {
    '튜토리얼': ('T', '튜토리얼'),
    '로딩힌트_ST00': ('L', '로딩 힌트'),
    '인물장소소개_ST10': ('P', '인물·장소 소개'),
    '스트랩경고_logo': ('S', '스트랩 경고'),
    '스테이지제목_경고띠': ('B', '스테이지 제목·경고 띠'),
    '홈버튼메뉴': ('M', '홈 버튼 메뉴'),
}
GRAY = {'I4', 'I8', 'IA4', 'IA8'}   # 흰 글씨 마스크 형식


def original(ref):
    """원본 일본판 텍스처(work/extract)를 RGBA 그림으로"""
    path, rest = ref.split('@')
    base, idx = rest.split('#')
    d = open(os.path.join(paths.SRC, path), 'rb').read()
    if d[:4] == b'SZ00':
        d = zlib.decompress(d[0x20:])
    for i, w, h, f, off, nb, pal in gxtex.tpl_images(d, int(base, 16)):
        if i == int(idx):
            return gxtex.decode(d[off:off + nb], w, h, f, pal)
    raise SystemExit(f'원본 텍스처를 못 찾음: {ref}')


def bg_kind(img, fmt):
    if fmt in GRAY:
        return '검정 바탕 흰 글씨'
    a = np.asarray(img)[..., 3]
    if a.min() >= 250:
        return '불투명'
    return '투명' if (a < 250).mean() >= 0.5 else '그림(가장자리 투명)'


def scale_for(w, h):
    """작은 그림은 GPT가 알아보기 쉽게 픽셀 그대로 키운 판을 첨부한다(긴 변 512px 이상, 최대 4배)"""
    return min(4, max(1, math.ceil(512 / max(w, h))))


def save_pair(it, orig, cur):
    base = f"{it['id']}_{it['name']}"
    w, h = orig.size
    n = scale_for(w, h)
    if n > 1:
        it['attach'] = f'원본/{base}_원본_{n}배_{w * n}x{h * n}.png'
        orig.resize((w * n, h * n), Image.NEAREST).save(os.path.join(GPT, it['attach']))
        it['ref'] = f'참고/{base}_현재한글판_{n}배.png'
        cur.resize((w * n, h * n), Image.NEAREST).save(os.path.join(GPT, it['ref']))
    else:
        it['attach'] = f'원본/{base}_원본_{w}x{h}.png'
        orig.save(os.path.join(GPT, it['attach']))
        it['ref'] = f'참고/{base}_현재한글판.png'
        cur.save(os.path.join(GPT, it['ref']))
    it['save_as'] = f'{base}.png'


def run_ocr(items):
    """현재 한글판을 2배로 키워 Windows 한국어 OCR로 읽는다 → work/GPT/_ocr.json"""
    tmp = os.path.join(GPT, '_ocr_in')
    if os.path.isdir(tmp):
        shutil.rmtree(tmp)
    os.makedirs(tmp)
    for it in items:
        im = Image.open(os.path.join(paths.ASSETS, it['asset'])).convert('RGBA')
        bg = Image.new('RGBA', im.size, (0, 0, 0, 255) if it['bg'] in ('투명', '검정 바탕 흰 글씨') else (255, 255, 255, 255))
        bg.alpha_composite(im)
        k = max(2, scale_for(*im.size))
        bg.convert('RGB').resize((im.width * k, im.height * k), Image.LANCZOS).save(os.path.join(tmp, it['id'] + '.png'))
    subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'ocr_ko.ps1'),
                    tmp, os.path.join(GPT, '_ocr.json')], check=True)
    shutil.rmtree(tmp)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    paths.ensure_extract()
    for d in ('원본', '참고'):
        if os.path.isdir(os.path.join(GPT, d)):
            shutil.rmtree(os.path.join(GPT, d))
    for d in ('원본', '참고', '결과', '비교'):
        os.makedirs(os.path.join(GPT, d), exist_ok=True)
    targets = json.load(open(os.path.join(paths.DATA, 'textures.json'), encoding='utf-8'))
    count = {}
    items = []
    for e in targets:
        pre, gname = GROUPS[e['group']]
        count[pre] = count.get(pre, 0) + 1
        it = {'id': f'{pre}{count[pre]:02d}' if pre != 'T' else f'T{count[pre]:03d}', 'name': e['name'],
              'group': gname, 'asset': e['name'] + '.png', 'size': [e['w'], e['h']], 'fmt': e['fmt'], 'refs': e['refs']}
        orig = original(e['refs'][0])
        cur = Image.open(os.path.join(paths.ASSETS, it['asset'])).convert('RGBA')
        if orig.size != cur.size:
            raise SystemExit(f"{it['name']}: 원본 {orig.size} / 현재 {cur.size} 크기가 다름")
        it['bg'] = bg_kind(orig, e['fmt'])
        save_pair(it, orig, cur)
        items.append(it)
    if '--no-ocr' not in sys.argv:
        run_ocr(items)
    gpt_request.write(items, os.path.join(GPT, '요청서.md'))   # 현재 문구 초안(ko_hint)도 채운다
    json.dump({'items': items}, open(os.path.join(GPT, '목록.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    kinds = {}
    for it in items:
        kinds[it['bg']] = kinds.get(it['bg'], 0) + 1
    print('항목', len(items), {g: n for g, n in count.items()}, kinds)


if __name__ == '__main__':
    main()
