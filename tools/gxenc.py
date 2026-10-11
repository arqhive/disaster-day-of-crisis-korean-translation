"""GX texture encoders: CMPR (via Pillow BC1), RGB5A3, I4."""
import io
import numpy as np
from PIL import Image


def _bc1_blocks(img):
    """Pillow DXT1 -> array (h/4, w/4, 8) of BC1 blocks."""
    w, h = img.size
    buf = io.BytesIO()
    img.convert('RGBA').save(buf, format='DDS', pixel_format='DXT1')
    raw = np.frombuffer(buf.getvalue()[128:], dtype=np.uint8)
    return raw[:(h // 4) * (w // 4) * 8].reshape(h // 4, w // 4, 8)


def _expand(c):
    """565 정수 (N,...) -> 디코더와 같은 0~255 RGB 실수"""
    r = ((c >> 11) & 31) * 255 // 31
    g = ((c >> 5) & 63) * 255 // 63
    b = (c & 31) * 255 // 31
    return np.stack([r, g, b], -1).astype(np.float32)


def _pack565(rgb):
    q = np.clip(np.rint(rgb * [31 / 255, 63 / 255, 31 / 255]), 0, [31, 63, 31]).astype(np.int64)
    return (q[..., 0] << 11) | (q[..., 1] << 5) | q[..., 2]


def _palette4(c0, c1):
    a, b = _expand(c0), _expand(c1)
    return np.stack([a, b, np.floor((2 * a + b) / 3), np.floor((a + 2 * b) / 3)], -2)   # (...,4,3)


def _best_idx(px, pal, opaque_mask=None):
    """px (N,16,3), pal (N,K,4,3) → 오차 (N,K), 인덱스 (N,K,16)"""
    d = ((px[:, None, :, None, :] - pal[:, :, None, :, :]) ** 2).sum(-1)   # (N,K,16,4)
    idx = d.argmin(-1)
    err = np.take_along_axis(d, idx[..., None], -1)[..., 0].sum(-1)
    return err, idx


def _encode_blocks(px):
    """불투명 4x4 블록들 px (N,16,3) → c0, c1, idx (N,16). 블록 안 색 쌍을 전부 시도하고 끝점을 다듬어 오차 최소."""
    N = len(px)
    q = _pack565(px)                                             # 후보 색 = 블록 픽셀 16개
    ii, jj = np.triu_indices(16)
    out_c0 = np.zeros(N, np.int64); out_c1 = np.zeros(N, np.int64); out_idx = np.zeros((N, 16), np.int64)
    best_err = np.full(N, np.inf)
    CH = 256
    for s in range(0, N, CH):
        p = px[s:s + CH]
        a, b = q[s:s + CH][:, ii], q[s:s + CH][:, jj]            # (n,136)
        c0, c1 = np.maximum(a, b), np.minimum(a, b)
        err, idx = _best_idx(p, _palette4(c0, c1))
        k = err.argmin(1); r = np.arange(len(p))
        c0, c1, idx, err = c0[r, k], c1[r, k], idx[r, k], err[r, k]
        # 다듬기: 끝점 각 채널 ±1 (565 단위)을 반복해서 시도
        steps = []
        for e in (0, 1):
            for sh, m in ((11, 31), (5, 63), (0, 31)):
                for dv in (-1, 1):
                    steps.append((e, sh, m, dv))
        for _ in range(4):
            improved = False
            for e, sh, m, dv in steps:
                t = (c0, c1)[e]
                ch = (t >> sh) & m
                nch = np.clip(ch + dv, 0, m)
                nt = (t & ~(m << sh)) | (nch << sh)
                n0, n1 = (nt, c1) if e == 0 else (c0, nt)
                hi, lo = np.maximum(n0, n1), np.minimum(n0, n1)
                e2, i2 = _best_idx(p, _palette4(hi, lo)[:, None])
                e2, i2 = e2[:, 0], i2[:, 0]
                better = e2 < err - 1e-6
                if better.any():
                    improved = True
                    c0 = np.where(better, hi, c0); c1 = np.where(better, lo, c1)
                    err = np.where(better, e2, err); idx = np.where(better[:, None], i2, idx)
            if not improved:
                break
        out_c0[s:s + CH], out_c1[s:s + CH], out_idx[s:s + CH], best_err[s:s + CH] = c0, c1, idx, err
    # c0 == c1 이면 디코더가 3색 모드로 읽음: 인덱스 0·1 만 쓰면 같은 색이라 문제없음
    same = out_c0 == out_c1
    out_idx[same] = 0
    return out_c0, out_c1, out_idx


def cmpr(img):
    """고품질 CMPR: 블록마다 색 쌍 전부 + 끝점 다듬기(불투명 블록). 투명 픽셀이 있는 블록은 Pillow 결과를 쓴다."""
    w, h = img.size
    assert w % 8 == 0 and h % 8 == 0
    rgba = np.asarray(img.convert('RGBA'), np.float32)
    blk = rgba.reshape(h // 4, 4, w // 4, 4, 4).transpose(0, 2, 1, 3, 4).reshape(-1, 16, 4)
    fast = np.frombuffer(cmpr_fast(img), np.uint8).reshape(h // 8, w // 8, 2, 2, 8)
    fast = fast.transpose(0, 2, 1, 3, 4).reshape(-1, 8).copy()   # 블록 행 순서로 되돌림
    opaque = (blk[..., 3] >= 128).all(1)
    if opaque.any():
        c0, c1, idx = _encode_blocks(blk[opaque][..., :3])
        bits = np.zeros(len(c0), np.int64)
        for i in range(16):
            bits |= idx[:, i] << (30 - 2 * i)
        o = np.zeros((len(c0), 8), np.uint8)
        o[:, 0], o[:, 1], o[:, 2], o[:, 3] = c0 >> 8, c0 & 255, c1 >> 8, c1 & 255
        for k in range(4):
            o[:, 4 + k] = (bits >> (24 - 8 * k)) & 255
        fast[opaque] = o
    b = fast.reshape(h // 8, 2, w // 8, 2, 8).transpose(0, 2, 1, 3, 4)
    return b.tobytes()


def cmpr_fast(img):
    w, h = img.size
    assert w % 8 == 0 and h % 8 == 0
    b = _bc1_blocks(img).copy()
    # colors LE -> BE
    b[..., [0, 1, 2, 3]] = b[..., [1, 0, 3, 2]]
    # index bytes: reverse 2-bit order (pixel0 to high bits)
    idx = b[..., 4:8]
    idx = ((idx & 0x03) << 6) | ((idx & 0x0c) << 2) | ((idx & 0x30) >> 2) | ((idx & 0xc0) >> 6)
    b[..., 4:8] = idx
    # tile: 8x8 macro block = 2x2 sub-blocks (TL, TR, BL, BR)
    b = b.reshape(h // 8, 2, w // 8, 2, 8).transpose(0, 2, 1, 3, 4)
    return b.tobytes()


def rgb5a3(img):
    a = np.asarray(img.convert('RGBA'), dtype=np.uint16)
    h, w = a.shape[:2]
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    opaque = al >= 0xF8
    v_op = 0x8000 | ((r >> 3) << 10) | ((g >> 3) << 5) | (b >> 3)
    v_tr = ((al >> 5) << 12) | ((r >> 4) << 8) | ((g >> 4) << 4) | (b >> 4)
    v = np.where(opaque, v_op, v_tr).astype('>u2')
    v = v.reshape(h // 4, 4, w // 4, 4).transpose(0, 2, 1, 3)
    return v.tobytes()


def i4(img):
    # intensity from luminance of the visible image (composited on black)
    im = img.convert('RGBA')
    bg = Image.new('RGBA', im.size, (0, 0, 0, 255))
    bg.alpha_composite(im)
    g = np.asarray(bg.convert('L'), dtype=np.uint16)
    h, w = g.shape
    v = ((g + 8) // 17).clip(0, 15).astype(np.uint8)
    v = v.reshape(h // 8, 8, w // 8, 8).transpose(0, 2, 1, 3).reshape(-1, 2)
    return (v[:, 0] << 4 | v[:, 1]).astype(np.uint8).tobytes()


BLOCK = {'CMPR': (8, 8), 'RGB5A3': (4, 4), 'I4': (8, 8)}


def _pad(img, bw, bh):
    """Pad to block multiple by repeating the last row/column."""
    w, h = img.size
    W, H = -(-w // bw) * bw, -(-h // bh) * bh
    if (W, H) == (w, h):
        return img
    a = np.asarray(img.convert('RGBA'))
    a = np.pad(a, ((0, H - h), (0, W - w), (0, 0)), mode='edge')
    return Image.fromarray(a, 'RGBA')


def encode(img, fmt):
    return {'CMPR': cmpr, 'RGB5A3': rgb5a3, 'I4': i4}[fmt](_pad(img, *BLOCK[fmt]))


ENC = {k: (lambda im, k=k: encode(im, k)) for k in BLOCK}
