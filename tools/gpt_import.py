"""GPT 재작업 결과 반영: work/GPT/결과/<번호>_<이름>.png → tools/assets/<이름>.png (게임 크기·배경 종류에 맞춤).
- 결과/게임크기/ 에 같은 이름의 게임 크기 판이 있으면 그것을 쓴다(고해상도판은 결과/ 에).
- 이미 게임 크기와 같은 그림은 그대로 쓴다(검정 바탕 흰 글씨는 흑백으로만 바꿈).
- 불투명 그림(튜토리얼·로딩 화면·스트랩 경고): 전체를 게임 크기로 줄인다(비율이 다르면 가운데를 잘라 맞춤).
- 투명 배경·검정 바탕 흰 글씨(제목 띠·홈 버튼): GPT 그림의 내용 덩어리를 잘라 지금 한글판 덩어리 높이에 맞추고
  그 가운데에 놓는다. 칸보다 넓으면 칸 안으로 줄인다. 투명이어야 하는데 배경을 채워 보냈으면 테두리 색을 지운다.
- 바꾸기 전 에셋은 work/GPT/이전_assets/ 에 한 번만 남기고, work/GPT/비교/<번호>.png 에 원본 | 이전 | 반영 시트를 만든다.
빌드는 따로 한다(python tools/build.py → python tools/inplace.py, 배포는 make_patcher.py).
사용: python tools/gpt_import.py            (결과 폴더 전부)
      python tools/gpt_import.py T001 B03   (번호 지정)"""
import json
import os
import shutil
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import gpt_prepare
import paths

GPT = os.path.join(paths.WORK, 'GPT')


def content_box(img, mask_like):
    """내용 덩어리 상자: 마스크류는 밝기, 그 외는 알파 기준"""
    a = np.asarray(img.convert('L') if mask_like else img.getchannel('A'))
    ys, xs = np.nonzero(a > 40)
    if not len(xs):
        return (0, 0, img.width, img.height)
    return (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)


def drop_background(img):
    """배경이 채워진 그림 → 테두리 중앙값 색을 투명하게"""
    a = np.asarray(img.convert('RGBA')).astype(float)
    if a[..., 3].min() < 250:
        return img
    edge = np.concatenate([a[0, :, :3], a[-1, :, :3], a[:, 0, :3], a[:, -1, :3]])
    d = np.sqrt(((a[..., :3] - np.median(edge, 0)) ** 2).sum(-1))
    a[..., 3] = np.clip((d - 12) * 8, 0, 255)
    return Image.fromarray(a.astype('uint8'), 'RGBA')


def fit_text(gpt, w, h, box, mask_like):
    """GPT 그림 내용을 (w,h) 캔버스의 box 높이에 맞춰 box 가운데에 놓는다"""
    src = gpt.crop(content_box(gpt, mask_like))
    bx0, by0, bx1, by1 = box
    k = (by1 - by0) / src.height
    if src.width * k > w - 2:
        k = (w - 2) / src.width
    nw, nh = max(1, round(src.width * k)), max(1, round(src.height * k))
    src = src.resize((nw, nh), Image.LANCZOS)
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    x = int(round(min(max(cx - nw / 2, 1), w - nw - 1)))
    y = int(round(min(max(cy - nh / 2, 0), h - nh)))
    canvas = Image.new('RGBA', (w, h), (0, 0, 0, 255) if mask_like else (0, 0, 0, 0))
    if mask_like:
        canvas.paste(src.convert('L').convert('RGBA'), (x, y))
    else:
        canvas.alpha_composite(src, (x, y))
    return canvas


def fit_full(gpt, w, h):
    r, rr = gpt.width / gpt.height, w / h
    if abs(r - rr) / rr > 0.02:   # 비율이 다르면 가운데를 잘라 맞춤
        if r > rr:
            nw = round(gpt.height * rr)
            gpt = gpt.crop(((gpt.width - nw) // 2, 0, (gpt.width - nw) // 2 + nw, gpt.height))
        else:
            nh = round(gpt.width / rr)
            gpt = gpt.crop((0, (gpt.height - nh) // 2, gpt.width, (gpt.height - nh) // 2 + nh))
    return gpt.resize((w, h), Image.LANCZOS)


def as_mask(img):
    g = img.convert('L')
    return Image.merge('RGBA', [g, g, g, Image.new('L', g.size, 255)])


def sheet(it, orig, prev, new, out):
    F = ImageFont.truetype('C:/Windows/Fonts/malgun.ttf', 13)
    n = gpt_prepare.scale_for(*new.size)
    ims = [(lab, im.resize((im.width * n, im.height * n), Image.NEAREST)) for lab, im in
           (('원본', orig), ('이전', prev), ('반영', new)) if im is not None]
    W = max(im.width for _, im in ims) + 20
    H = sum(im.height + 26 for _, im in ims) + 24
    s = Image.new('RGB', (W, H), (70, 70, 85))
    d = ImageDraw.Draw(s)
    d.text((6, 4), f"{it['id']} {it['name']} ({it['size'][0]}×{it['size'][1]}, {it['bg']})", font=F, fill=(255, 255, 255))
    y = 24
    for lab, im in ims:
        d.text((6, y), lab, font=F, fill=(220, 220, 230))
        y += 18
        chk = Image.new('RGBA', im.size, (110, 110, 125, 255))
        cd = ImageDraw.Draw(chk)
        for yy in range(0, im.height, 16):
            for xx in range((yy // 16) % 2 * 16, im.width, 32):
                cd.rectangle([xx, yy, xx + 15, yy + 15], fill=(140, 140, 155, 255))
        chk.alpha_composite(im)
        s.paste(chk.convert('RGB'), (10, y))
        y += im.height + 8
    s.save(out)


def main(ids):
    sys.stdout.reconfigure(encoding='utf-8')
    items = {it['id']: it for it in json.load(open(os.path.join(GPT, '목록.json'), encoding='utf-8'))['items']}
    done = []
    for f in sorted(x for x in os.listdir(os.path.join(GPT, '결과')) if x.lower().endswith('.png')):
        iid = f.split('_')[0]
        if ids and iid not in ids:
            continue
        it = items.get(iid)
        if it is None:
            print('  모르는 번호:', f)
            continue
        w, h = it['size']
        mask_like = it['bg'] == '검정 바탕 흰 글씨'
        sized = os.path.join(GPT, '결과', '게임크기', f)   # 게임 크기로 맞춘 판이 있으면 그것을 쓴다
        gpt = Image.open(sized if os.path.exists(sized) else os.path.join(GPT, '결과', f)).convert('RGBA')
        asset = os.path.join(paths.ASSETS, it['asset'])
        prev = Image.open(asset).convert('RGBA')
        orig = Image.open(os.path.join(GPT, it['attach'])).convert('RGBA')
        if orig.size != (w, h):
            orig = orig.resize((w, h), Image.NEAREST)   # _N배 첨부본 → 게임 크기
        if gpt.size == (w, h):
            new = as_mask(gpt) if mask_like else gpt
        elif it['bg'] == '불투명':
            new = fit_full(gpt, w, h).convert('RGBA')
            new.putalpha(255)
        elif it['bg'] == '그림(가장자리 투명)':   # 그림째 맞추고 투명 모양은 이전 것
            new = fit_full(gpt, w, h).convert('RGBA')
            new.putalpha(prev.getchannel('A'))
        else:
            if not mask_like:
                gpt = drop_background(gpt)
                if (np.asarray(gpt.getchannel('A')) > 40).mean() < 0.005:
                    print(f'  {f}: 배경을 지우니 글자가 거의 안 남음(흰 글씨에 흰 배경?) → 건너뜀. 투명 배경으로 다시 받아 주세요.')
                    continue
            ref = prev
            if content_box(prev, mask_like) == (0, 0, w, h) or not (np.asarray(prev.getchannel('A')) > 40).any():
                ref = orig   # 이전 그림이 비었거나 칸 전체면 원본 덩어리 자리를 기준으로
            new = fit_text(gpt, w, h, content_box(ref, mask_like), mask_like)
            if mask_like:
                new = as_mask(new)
        bk = os.path.join(GPT, '이전_assets', it['asset'])
        if not os.path.exists(bk):
            os.makedirs(os.path.dirname(bk), exist_ok=True)
            shutil.copy2(asset, bk)
        new.save(asset)
        sheet(it, orig, prev, new, os.path.join(GPT, '비교', iid + '.png'))
        done.append(iid)
    print(f'반영 {len(done)}장:', ' '.join(done))
    if done:
        print('비교 시트: work/GPT/비교/  · 빌드: python tools/build.py')


if __name__ == '__main__':
    main(set(sys.argv[1:]))
