"""오프닝 영상(mov/opening.sfd)에 박힌 일본어 자막 9줄을 지우고 한글을 넣는다.

translation/opening.json 의 줄마다: 구간 프레임에서 흰 글씨 픽셀을 모아 마스크를 만들고(조금 넓힘),
OpenCV(매끈한 바탕) 또는 LaMa(움직이는 실사)로 지운 뒤, 원본 한자 높이(33px)에 맞춰 한글을 가운데에 그린다.
원본 자막은 페이드 없이 바로 켜지고 꺼져서 한글도 그 구간에만 그린다.
영상은 원본 I 프레임 자리에 맞춰 MPEG-1 로 다시 인코딩하고, sfdvideo 로 원본 SFD 묶음에 끼운다.
몇 분 걸려서 결과를 work/cache/opening/ 에 둔다(설정·도구·글꼴·원본이 같으면 다시 씀).
필요: imageio-ffmpeg, opencv-python, LaMa(%LOCALAPPDATA%\\lama, torch). 글꼴은 tools/fonts/ 또는 Windows 사용자 글꼴 폴더.
사용: python tools/opening_video.py   (build.py 가 부른다)"""
import hashlib
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import paths
import sfdvideo

CONF = os.path.join(paths.ROOT, 'translation', 'opening.json')
SRC = os.path.join(paths.SRC, 'mov', 'opening.sfd')
OUT = os.path.join(paths.OUT_FILES, 'mov', 'opening.sfd')
CACHE = os.path.join(paths.WORK, 'cache', 'opening')
W, H = 640, 448
Y0, Y1 = 350, 405            # 자막 줄 세로 범위
INK_TOP, INK_BOT = 362, 394  # 원본 한자 잉크 위·아래
CX = 320


def font_path(name):
    for d in (os.path.join(HERE, 'fonts'), os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Microsoft', 'Windows', 'Fonts'),
              r'C:\Windows\Fonts'):
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    raise SystemExit(f'글꼴 {name} 이 없음 (tools/fonts/ 에 두기)')


def ffmpeg():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def text_mask(frames, a, b):
    import cv2
    acc = np.zeros((H, W), bool)
    for k in range(a, b):
        f = frames[k].astype(np.int16)
        acc |= (f.min(2) > 170) & ((f.max(2) - f.min(2)) < 45)
    acc[:Y0] = False
    acc[Y1:] = False
    return cv2.dilate(acc.astype(np.uint8) * 255, np.ones((7, 7), np.uint8))


def erase(frame, mask, how):
    if how == 'lama':
        sys.path.insert(0, os.path.join(os.environ['LOCALAPPDATA'], 'lama'))
        from lama_inpaint import inpaint
        return inpaint(frame, mask)
    import cv2
    return cv2.inpaint(frame, mask, 5, cv2.INPAINT_TELEA)


def text_layer(text, font):
    """원본 한자 잉크 높이(362~394)에 맞춰 가운데에 그린 한글 알파(0~1)"""
    from PIL import Image, ImageDraw, ImageFont
    size = 40
    for _ in range(3):
        box = ImageFont.truetype(font, size).getbbox('한')
        size = round(size * (INK_BOT - INK_TOP + 1) / (box[3] - box[1]))
    f = ImageFont.truetype(font, size)
    layer = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(layer)
    bx = d.textbbox((0, 0), text, font=f)
    d.text((CX - (bx[2] - bx[0]) / 2 - bx[0], INK_TOP - f.getbbox('한')[1]), text, font=f, fill=255)
    return np.asarray(layer, np.float32)[..., None] / 255


def cache_key(conf, font):
    h = hashlib.sha1()
    for p in (CONF, os.path.abspath(__file__), sfdvideo.__file__, font):
        h.update(open(p, 'rb').read())
    with open(SRC, 'rb') as f:
        h.update(f.read(1 << 20))
    h.update(str(os.path.getsize(SRC)).encode())
    return h.hexdigest()


def make(conf, font):
    F = ffmpeg()
    src = open(SRC, 'rb').read()
    es = sfdvideo.video_es(src)
    raw = subprocess.run([F, '-v', 'error', '-f', 'mpegvideo', '-i', '-', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         input=es, capture_output=True, check=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    edited = {}
    for x in conf['줄']:
        a, b = x['시작'], x['끝']
        m = text_mask(frames, *(x.get('마스크') or (a, b)))
        alpha = text_layer(x['ko'], font)
        for k in range(a, b):
            e = erase(np.array(frames[k]), m, x['지우기']).astype(np.float32)
            edited[k] = (e * (1 - alpha) + 255 * alpha).round().clip(0, 255).astype(np.uint8)
        print(f"  {x['원문']} → {x['ko']} ({b - a}프레임, {x['지우기']})")
    kf = ','.join(f'{i * 1001 / 30000:.4f}' for i in sfdvideo.keyframes(es))
    enc = subprocess.Popen([F, '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', '30000/1001', '-i', '-',
                            '-c:v', 'mpeg1video', '-b:v', '3600k', '-maxrate', '8000k', '-bufsize', '1441792', '-g', '16', '-bf', '2',
                            '-force_key_frames', kf, '-pix_fmt', 'yuv420p', '-f', 'mpeg1video', '-'],
                           stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    import threading
    chunks = []
    t = threading.Thread(target=lambda: chunks.append(enc.stdout.read()))
    t.start()
    for k in range(len(frames)):
        enc.stdin.write((edited.get(k, frames[k])).tobytes())
    enc.stdin.close()
    t.join()
    if enc.wait():
        raise SystemExit('ffmpeg 인코딩 실패')
    return sfdvideo.replace_video(src, chunks[0])


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    conf = json.load(open(CONF, encoding='utf-8'))
    font = font_path(conf['글꼴'])
    cached = os.path.join(CACHE, cache_key(conf, font) + '.sfd')
    if os.path.exists(cached):
        data = open(cached, 'rb').read()
        print('오프닝 영상: 캐시 사용')
    else:
        print('오프닝 영상: 자막 지우고 한글 넣는 중 (몇 분)')
        data = make(conf, font)
        os.makedirs(CACHE, exist_ok=True)
        open(cached + '.tmp', 'wb').write(data)
        os.replace(cached + '.tmp', cached)
    if len(data) != os.path.getsize(SRC):
        raise SystemExit('오프닝 영상 크기가 원본과 다름')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(data)


if __name__ == '__main__':
    main()
